"""Agentic ingestion for messy alternative-splicing tables.

The strict loader only accepts rMATS / SUPPA2 / MAJIQ / LeafCutter or a
fully standardized ``AS_event_master`` table. Real vendor exports rarely
match any of those: headers are renamed, separators differ, PSI is written
as percentages, p-values carry ``<`` prefixes, sample groups live in a
second file, and event types use long English labels.

This module closes that gap with the same pattern the rest of SpliceGAIP
uses for model assistance:

1. **profile** every delimited file deterministically (encoding, delimiter,
   header row, columns, sample rows);
2. **propose a mapping** from headers to the standard schema. A configured
   model may suggest the mapping (it sees headers plus three sample rows,
   never the full table), but a synonym-based heuristic always provides a
   baseline and a fallback;
3. **sanitize** the proposal — file names, headers and event types must
   exist in the profiled data, so a hallucinated mapping cannot be applied;
4. **convert** deterministically into :class:`StandardEvent` objects and a
   sample metadata table, dropping unusable rows and recording every
   transformation as a reviewable issue;
5. **preview** the result through the same validator the pipeline uses, so
   the UI can show what will happen before the analysis starts.

Nothing here writes to disk during preview. :func:`apply_ingestion` writes
a self-contained directory that the existing :func:`load_dataset` accepts.
"""

from __future__ import annotations

import csv
import io
import json
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from splicegaip.data.loader import Dataset, load_dataset
from splicegaip.data.validator import validate_dataset
from splicegaip.splicing.schema import (
    AS_EVENT_TYPES,
    CORE_EVENT_FIELDS,
    QUALITY_EVENT_FIELDS,
    PSI_COLUMN_PREFIX,
    SampleMetadata,
    StandardEvent,
)

#: Size of the head window used for encoding/delimiter/header detection.
HEAD_BYTES = 256 * 1024
#: Rows inspected when picking the header line.
HEADER_SCAN_ROWS = 15
#: Sample rows kept in a profile (sent to the model and shown in the UI).
SAMPLE_ROWS = 3
#: Rows scanned when collecting distinct values (event types, groups).
VALUE_SCAN_ROWS = 20000
#: Upper bound for row counting; keeps profiling fast on huge exports.
MAX_COUNT_ROWS = 500000
#: Values longer than this are truncated before being sent to a model.
MAX_CELL_CHARS = 64
SUPPORTED_SUFFIXES = {".csv", ".tsv", ".txt", ".tab"}

#: Standard fields the mapping UI exposes, with bilingual labels.
MAPPING_FIELDS: tuple[tuple[str, str, str, bool], ...] = (
    ("gene_symbol", "基因符号", "Gene symbol", True),
    ("gene_id", "基因 ID", "Gene ID", False),
    ("event_type", "剪接类型", "Event type", False),
    ("delta_PSI", "ΔPSI", "Delta PSI", True),
    ("mean_PSI_group1", "组1平均 PSI", "Group 1 mean PSI", False),
    ("mean_PSI_group2", "组2平均 PSI", "Group 2 mean PSI", False),
    ("FDR", "FDR / q 值", "FDR / q value", False),
    ("p_value", "p 值", "p value", False),
    ("chromosome", "染色体", "Chromosome", False),
    ("strand", "链方向", "Strand", False),
    ("start", "起始坐标", "Start", False),
    ("end", "终止坐标", "End", False),
    ("genomic_coordinates", "基因组坐标", "Coordinates", False),
)

#: Header synonyms. Values are matched after :func:`_norm`, so punctuation
#: and case never matter. Greek letters are spelled out first.
COLUMN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "event_id": (
        "eventid", "event", "asid", "aseventid", "splicingid", "spliceeventid",
        "eventname", "事件id", "事件编号", "事件",
    ),
    "gene_id": (
        "geneid", "ensembl", "ensemblgeneid", "ensemblid", "gene", "基因id",
        "基因编号",
    ),
    "gene_symbol": (
        "genesymbol", "symbol", "genename", "genesym", "gene", "hgnc",
        "基因名", "基因符号",
    ),
    "event_type": (
        "eventtype", "astype", "splicingtype", "splicetype", "type", "类型",
        "剪接类型",
    ),
    "chromosome": ("chromosome", "chrom", "chr", "seqname", "seqid", "染色体"),
    "strand": ("strand", "方向", "链"),
    "genomic_coordinates": (
        "genomiccoordinates", "coordinates", "coordinate", "coord", "region",
        "genomicregion", "坐标", "基因组坐标",
    ),
    "coordinate_system": ("coordinatesystem", "坐标系统", "坐标系"),
    "start": (
        "start", "begin", "startposition", "chromstart", "exonstart",
        "exonstart0base", "upstreames", "upstreames", "longexonstart0base",
        "riexonstart0base", "起点", "起始",
    ),
    "end": (
        "end", "stop", "endposition", "chromend", "exonend", "exonend0base",
        "downstreames", "downstreames", "longexonend0base", "riexonend0base",
        "终点", "终止",
    ),
    "mean_PSI_group1": (
        "meanpsigroup1", "meangroup1psi", "psigroup1", "group1psi", "psi1",
        "meanpsi1", "avgpsi1", "avgpsigroup1", "controlpsi", "ctrlpsi",
        "psictrl", "psicontrol", "psicontrolgroup", "inclevel1", "inclvl1",
        "组1psi", "对照组psi", "对照psi",
    ),
    "mean_PSI_group2": (
        "meanpsigroup2", "meangroup2psi", "psigroup2", "group2psi", "psi2",
        "meanpsi2", "avgpsi2", "avgpsigroup2", "treatpsi", "casepsi",
        "psitreat", "psitreatment", "psitreated", "inclevel2", "inclvl2",
        "组2psi", "实验组psi", "处理组psi",
    ),
    "delta_PSI": (
        "deltapsi", "deltaps", "dpsi", "dpsidelta", "psidifference", "psidelta",
        "psidiff", "delta", "差异psi", "psidelta值",
    ),
    "p_value": ("pvalue", "pval", "pvalues", "p", "p值", "显著性"),
    "FDR": (
        "fdr", "qvalue", "qval", "q", "padj", "adjp", "adjustedp",
        "adjustedpvalue", "fdrbh", "bh", "校正p值", "fdr值",
    ),
    "inclusion_reads": (
        "inclusionreads", "inclusionreadcount", "inclusioncount", "ijc",
        "inclusion", "包含reads", "包含读数",
    ),
    "exclusion_reads": (
        "exclusionreads", "exclusionreadcount", "exclusioncount", "sjc",
        "exclusion", "排除reads", "排除读数",
    ),
    "total_support_reads": (
        "totalsupportreads", "totalreads", "supportreads", "totalcount",
        "总reads", "支持reads",
    ),
    "valid_sample_count": (
        "validsamplecount", "validsamples", "nvalid", "有效样本数",
    ),
    "psi_missing_rate": ("psimissingrate", "missingrate", "missrate", "缺失率"),
    "single_sample_driven": ("singlesampledriven", "单样本驱动"),
    "mapping_ambiguity": ("mappingambiguity", "multimapping", "比对歧义"),
    "confidence_level": ("confidencelevel", "confidence", "置信度"),
}

METADATA_SYNONYMS: dict[str, tuple[str, ...]] = {
    "sample_id": (
        "sampleid", "sample", "samplename", "id", "runsampleid", "样本id",
        "样本编号", "样本",
    ),
    "group": (
        "group", "condition", "treatment", "groupname", "class", "status",
        "分组", "组别", "条件",
    ),
    "condition": ("condition", "disease", "phenotype", "条件", "疾病"),
    "tissue": ("tissue", "organ", "组织"),
    "batch": ("batch", "plate", "run", "批次"),
}

EVENT_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "SE": (
        "se", "skippedexon", "exonskipping", "skippingexon", "skippedexons",
        "cassetteexon", "cassette", "es", "外显子跳跃", "外显子跳过",
    ),
    "MXE": (
        "mxe", "mutuallyexclusiveexons", "mutuallyexclusive", "exclusiveexons",
        "mutualexclusion", "互斥外显子",
    ),
    "A5SS": (
        "a5ss", "alt5", "alternative5", "alternative5splicesite", "5ss",
        "donor", "alternativedonor", "可变5剪接位点",
    ),
    "A3SS": (
        "a3ss", "alt3", "alternative3", "alternative3splicesite", "3ss",
        "acceptor", "alternativeacceptor", "可变3剪接位点",
    ),
    "RI": (
        "ri", "retainedintron", "intronretention", "retention", "intron",
        "内含子保留",
    ),
}

CONTROL_HINTS = (
    "ctrl", "control", "untreated", "vehicle", "wildtype", "wt", "normal",
    "mock", "igg", "group1", "grp1", "对照", "正常", "未处理", "野生", "组1",
)
TREAT_HINTS = (
    "treat", "trt", "treatment", "case", "ko", "knockout", "kd", "knockdown",
    "overexpr", "overexpression", "oe", "drug", "disease", "tumor", "cancer",
    "patient", "mutant", "group2", "grp2", "处理", "实验", "疾病", "肿瘤",
    "过表达", "敲除", "组2",
)

_NA_VALUES = {
    "", "na", "n/a", "nan", "none", "null", "nil", "-", "--", ".", "inf",
    "+inf", "-inf", "notavailable", "missing",
}

VALIDATION_ZH: dict[str, str] = {
    "no_events": "数据集中没有任何剪接事件。",
    "missing_event_id": "{n} 个事件缺少 event_id。",
    "duplicate_event_id": "{n} 个 event_id 重复。",
    "missing_gene": "{n} 个事件缺少基因标识。",
    "unknown_event_type": "存在标准之外的剪接类型（SE/MXE/A5SS/A3SS/RI）。",
    "no_fdr": "未检测到 FDR/q 值；显著性筛选将选不出事件。",
    "partial_fdr": "{n} 个事件缺少 FDR。",
    "missing_delta_psi": "{n} 个事件缺少 ΔPSI。",
    "psi_out_of_range": "{n} 个 PSI 值超出 [0,1]。",
    "single_group": "样本元数据少于两组，差异分析无法进行。",
    "psi_sample_mismatch": "每样本 PSI 列与元数据样本 ID 不匹配。",
}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def _norm(value: Any) -> str:
    """Lowercase, spell out Greek letters, drop punctuation and spaces."""
    text = str(value or "").strip().lower()
    for source, target in (
        ("δ", "delta"),
        ("Δ", "delta"),
        ("ψ", "psi"),
        ("Ψ", "psi"),
        ("σ", "sigma"),
        ("α", "alpha"),
        ("β", "beta"),
    ):
        text = text.replace(source, target)
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def _truncate(value: Any, limit: int = MAX_CELL_CHARS) -> str:
    text = str(value if value is not None else "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _scrub(text: str) -> str:
    """Remove anything that looks like a credential from surfaced errors."""
    cleaned = re.sub(r"(sk-[A-Za-z0-9_\-]{8,})", "sk-****", str(text or ""))
    cleaned = re.sub(r"(?i)(api[_\-]?key\s*[=:]\s*)\S+", r"\1****", cleaned)
    return cleaned[:300]


def _issue(severity: str, code: str, message_zh: str, message_en: str) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "message": message_zh,
        "message_en": message_en,
    }


def _unique_headers(headers: Sequence[str]) -> list[str]:
    seen: Counter[str] = Counter()
    result: list[str] = []
    for index, raw in enumerate(headers):
        name = str(raw or "").strip() or f"column_{index + 1}"
        seen[name] += 1
        result.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    return result


# ---------------------------------------------------------------------------
# profiling
# ---------------------------------------------------------------------------


@dataclass
class FileProfile:
    """Deterministic description of one delimited input file."""

    path: Path
    name: str
    supported: bool = True
    encoding: str = ""
    delimiter: str = ","
    header_row: int = 0
    headers: list[str] = field(default_factory=list)
    sample_rows: list[list[str]] = field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    notes: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def suffix(self) -> str:
        return self.path.suffix.lower()

    @property
    def width(self) -> int:
        return len(self.headers)

    def column_values(self, header: str, limit: int = 40) -> list[str]:
        """Distinct non-empty values for ``header`` (capped scan)."""
        try:
            index = self.headers.index(header)
        except ValueError:
            return []
        values: list[str] = []
        seen: set[str] = set()
        for count, row in enumerate(self.iter_rows()):
            if count >= VALUE_SCAN_ROWS:
                break
            value = row[index].strip() if index < len(row) else ""
            if not value or value in seen or _norm(value) in _NA_VALUES:
                continue
            seen.add(value)
            values.append(value)
            if len(values) >= limit:
                break
        return values

    def iter_rows(self) -> Iterator[list[str]]:
        """Yield data rows after the detected header, aligned to its width."""
        with self.path.open("r", encoding=self.encoding or "utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter=self.delimiter)
            for index, row in enumerate(reader):
                if index <= self.header_row:
                    continue
                if not any(str(cell).strip() for cell in row):
                    continue
                if len(row) < self.width:
                    row = list(row) + [""] * (self.width - len(row))
                elif len(row) > self.width:
                    row = row[: self.width]
                yield row

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "supported": self.supported,
            "encoding": self.encoding,
            "delimiter": self.delimiter,
            "header_row": self.header_row,
            "headers": self.headers,
            "column_count": self.width,
            "row_count": self.row_count,
            "truncated": self.truncated,
            "notes": self.notes,
            "error": self.error,
        }


def _decode_head(raw: bytes) -> tuple[str, str]:
    """Return ``(encoding, text)`` for a byte sample, tolerating Excel exports."""
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        try:
            return "utf-16", raw.decode("utf-16")
        except UnicodeDecodeError:
            pass
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if text.count("\ufffd") <= max(1, len(text) // 2000):
            return encoding, text
    return "latin-1", raw.decode("latin-1", errors="replace")


def _head_text(path: Path) -> tuple[bytes, str, str]:
    with path.open("rb") as handle:
        raw = handle.read(HEAD_BYTES)
    encoding, text = _decode_head(raw)
    if len(raw) >= HEAD_BYTES and "\n" in text:
        text = text.rsplit("\n", 1)[0]
    return raw, encoding, text


def _detect_delimiter(text: str, suffix: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()][:20]
    if not lines:
        return "\t" if suffix in {".tsv", ".tab"} else ","
    default = "\t" if suffix in {".tsv", ".tab"} else ","
    best = default
    best_score = -1.0
    for delimiter in (",", "\t", ";", "|"):
        counts: list[int] = []
        for line in lines:
            try:
                counts.append(len(next(csv.reader([line], delimiter=delimiter))))
            except csv.Error:
                counts.append(1)
        mode, frequency = Counter(counts).most_common(1)[0]
        if mode < 2:
            continue
        consistency = frequency / len(counts)
        score = consistency * 12 + min(mode, 24) + (1.5 if delimiter == default else 0)
        if score > best_score:
            best_score = score
            best = delimiter
    return best


def _looks_numeric(value: str) -> bool:
    text = str(value or "").strip().replace("%", "").lstrip("<>≤≥")
    if not text:
        return False
    try:
        float(text.replace(",", ""))
        return True
    except ValueError:
        return False


def _header_hit_count(cells: Sequence[str]) -> int:
    hits = 0
    for cell in cells:
        normalized = _norm(cell)
        if not normalized:
            continue
        for synonyms in (*COLUMN_SYNONYMS.values(), *METADATA_SYNONYMS.values()):
            if normalized in {_norm(alias) for alias in synonyms}:
                hits += 1
                break
    return hits


def _detect_header_row(rows: Sequence[Sequence[str]]) -> int:
    best_index = 0
    best_score = float("-inf")
    for index, row in enumerate(rows[:HEADER_SCAN_ROWS]):
        cells = [str(cell).strip() for cell in row]
        nonempty = sum(1 for cell in cells if cell)
        if nonempty < 2:
            continue
        unique = len({cell.lower() for cell in cells if cell}) / max(nonempty, 1)
        numeric = sum(1 for cell in cells if _looks_numeric(cell)) / max(nonempty, 1)
        textual = sum(
            1
            for cell in cells
            if cell and not _looks_numeric(cell) and len(cell) <= 80
        ) / max(nonempty, 1)
        width_match = 0.0
        following = [
            len([c for c in candidate if str(c).strip()])
            for candidate in rows[index + 1 : index + 4]
        ]
        if following:
            width_match = sum(1 for width in following if width == nonempty) / len(following)
        score = (
            min(nonempty, 12) * 0.6
            + unique * 2.0
            + (1.0 - numeric) * 2.5
            + textual * 1.5
            + width_match * 2.0
            + _header_hit_count(cells) * 1.2
            - index * 0.08
        )
        if score > best_score:
            best_score = score
            best_index = index
    return best_index


def profile_file(path: Path, *, count_rows: bool = True) -> FileProfile:
    """Profile one file; never raises for unreadable/unsupported inputs."""
    profile = FileProfile(path=path, name=path.name)
    if not path.is_file():
        profile.supported = False
        profile.error = "not a file"
        return profile
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        profile.supported = False
        profile.notes.append(
            f"unsupported extension {path.suffix or '(none)'}; only CSV/TSV/TXT are profiled"
        )
        return profile
    try:
        if path.stat().st_size == 0:
            profile.supported = False
            profile.error = "empty file"
            return profile
        raw, encoding, text = _head_text(path)
        profile.encoding = encoding
        profile.delimiter = _detect_delimiter(text, path.suffix.lower())
        try:
            rows = list(csv.reader(io.StringIO(text), delimiter=profile.delimiter))
        except csv.Error as error:
            profile.supported = False
            profile.error = f"cannot parse table: {error}"
            return profile
        if not rows:
            profile.supported = False
            profile.error = "no rows"
            return profile
        header_row = _detect_header_row(rows)
        while header_row < len(rows) and not any(str(cell).strip() for cell in rows[header_row]):
            header_row += 1
        if header_row >= len(rows):
            profile.supported = False
            profile.error = "no header row detected"
            return profile
        profile.header_row = header_row
        profile.headers = _unique_headers(rows[header_row])
        for row in rows[header_row + 1 :]:
            if not any(str(cell).strip() for cell in row):
                continue
            padded = list(row) + [""] * max(0, profile.width - len(row))
            profile.sample_rows.append([_truncate(cell) for cell in padded[: profile.width]])
            if len(profile.sample_rows) >= SAMPLE_ROWS:
                break
        if not profile.sample_rows and profile.width:
            profile.notes.append("no data rows found below the header")
        if count_rows:
            profile.row_count, profile.truncated = _count_rows(path, profile)
        return profile
    except OSError as error:
        profile.supported = False
        profile.error = f"cannot read file: {error}"
        return profile


def _count_rows(path: Path, profile: FileProfile) -> tuple[int, bool]:
    count = 0
    try:
        with path.open("r", encoding=profile.encoding, newline="") as handle:
            for index, row in enumerate(csv.reader(handle, delimiter=profile.delimiter)):
                if index <= profile.header_row:
                    continue
                if not any(str(cell).strip() for cell in row):
                    continue
                count += 1
                if count >= MAX_COUNT_ROWS:
                    return count, True
    except (OSError, UnicodeError, csv.Error):
        return count, False
    return count, False


def _profile_directory(directory: Path) -> list[FileProfile]:
    profiles: list[FileProfile] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() in {".json", ".png", ".pdf", ".log"}:
            continue
        profiles.append(profile_file(path))
    return profiles


# ---------------------------------------------------------------------------
# heuristic mapping
# ---------------------------------------------------------------------------


def _synonym_score(header: str, synonyms: Sequence[str]) -> float:
    normalized = _norm(header)
    if not normalized:
        return 0.0
    normalized_synonyms = {_norm(alias) for alias in synonyms if _norm(alias)}
    if normalized in normalized_synonyms:
        return 1.0
    for alias in normalized_synonyms:
        if len(alias) < 4:
            continue
        if normalized.startswith(alias) or (
            alias.startswith(normalized) and len(normalized) >= 4
        ):
            return 0.88
        if alias in normalized:
            return 0.8
    return 0.0


_FIELD_PRIORITY = {"gene_symbol": 3, "gene_id": 2, "event_type": 2}


def _map_columns(
    headers: Sequence[str],
    synonyms: Mapping[str, Sequence[str]],
    *,
    threshold: float = 0.72,
    strict_fields: Iterable[str] = (),
) -> dict[str, str]:
    """Assign at most one header per field, best score first."""
    strict = set(strict_fields)
    candidates: list[tuple[float, str, int, str]] = []
    for field_name, field_synonyms in synonyms.items():
        for index, header in enumerate(headers):
            score = _synonym_score(header, field_synonyms)
            if field_name in strict and score < 1.0:
                continue
            if score >= threshold:
                candidates.append((score, field_name, index, header))
    candidates.sort(key=lambda item: (-item[0], item[2], -_FIELD_PRIORITY.get(item[1], 0), item[1]))
    mapping: dict[str, str] = {}
    used_indices: set[int] = set()
    for _score, field_name, index, header in candidates:
        if field_name in mapping or index in used_indices:
            continue
        mapping[field_name] = header
        used_indices.add(index)
    return mapping


def _detect_sample_columns(profile: FileProfile, mapped_headers: set[str]) -> dict[str, str]:
    """Find per-sample PSI columns and derive a sample id from each header."""
    sample_columns: dict[str, str] = {}
    used_ids: set[str] = set()
    for header in profile.headers:
        if header in mapped_headers:
            continue
        raw = header.strip()
        lowered = raw.lower()
        prefix = ""
        for candidate in ("psi_", "psi.", "psi-", "psi ", "psi:"):
            if lowered.startswith(candidate):
                prefix = raw[: len(candidate)]
                break
        if not prefix:
            continue
        sample_id = raw[len(prefix) :].strip(" _-.:")
        if not sample_id or sample_id in used_ids:
            continue
        used_ids.add(sample_id)
        sample_columns[header] = sample_id
    return sample_columns


def _normalize_event_type(value: Any) -> str | None:
    normalized = _norm(value)
    if not normalized:
        return None
    if normalized.upper() in AS_EVENT_TYPES:
        return normalized.upper()
    for canonical, aliases in EVENT_TYPE_ALIASES.items():
        for alias in aliases:
            normalized_alias = _norm(alias)
            if not normalized_alias:
                continue
            if normalized == normalized_alias:
                return canonical
            if len(normalized_alias) >= 4 and (
                normalized_alias in normalized or normalized in normalized_alias
            ):
                return canonical
    return None


def _event_type_map(profile: FileProfile, header: str | None) -> dict[str, str]:
    if not header or header not in profile.headers:
        return {}
    result: dict[str, str] = {}
    for value in profile.column_values(header):
        canonical = _normalize_event_type(value)
        if canonical:
            result[value] = canonical
    return result


def _infer_group(sample_id: str) -> str | None:
    normalized = _norm(sample_id)
    if any(_norm(hint) in normalized for hint in CONTROL_HINTS):
        return "Control"
    if any(_norm(hint) in normalized for hint in TREAT_HINTS):
        return "Treatment"
    return None

def _pick_groups(values: Sequence[str]) -> dict[str, str]:
    clean = [str(value).strip() for value in values if str(value).strip()]
    if len(clean) < 2:
        return {}
    control = next(
        (value for value in clean if any(_norm(hint) in _norm(value) for hint in CONTROL_HINTS)),
        clean[0],
    )
    treatment = next(
        (
            value
            for value in clean
            if value != control
            and any(_norm(hint) in _norm(value) for hint in TREAT_HINTS)
        ),
        next((value for value in clean if value != control), clean[-1]),
    )
    return {"group1": control, "group2": treatment}


def _metadata_profile(profiles: Sequence[FileProfile]) -> FileProfile | None:
    best: FileProfile | None = None
    best_score = 0.0
    for profile in profiles:
        if not profile.supported or not profile.headers:
            continue
        columns = _map_columns(profile.headers, METADATA_SYNONYMS)
        score = 0.0
        if "sample_id" in columns:
            score += 2.0
        if "group" in columns:
            score += 3.0
        lowered = profile.name.lower()
        if any(token in lowered for token in ("metadata", "sample", "design", "group")):
            score += 1.0
        if any(token in lowered for token in ("event", "psi", "mats", "splice")):
            score -= 1.5
        if score > best_score:
            best_score = score
            best = profile
    return best if best_score >= 3.0 else None


@dataclass
class _Candidate:
    profile: FileProfile
    columns: dict[str, str]
    sample_columns: dict[str, str]
    score: float


def _candidate_for(profile: FileProfile) -> _Candidate | None:
    if not profile.supported or not profile.headers:
        return None
    # Group means must match an exact synonym: PSI_control_1 is one sample, not
    # the control-group mean, even though it starts with "PSI_control".
    columns = _map_columns(
        profile.headers,
        COLUMN_SYNONYMS,
        strict_fields={"mean_PSI_group1", "mean_PSI_group2"},
    )
    mapped_headers = set(columns.values())
    sample_columns = _detect_sample_columns(profile, mapped_headers)
    if not ("gene_symbol" in columns or "gene_id" in columns):
        return None
    quantitative = (
        "delta_PSI" in columns
        or ("mean_PSI_group1" in columns and "mean_PSI_group2" in columns)
        or bool(sample_columns)
    )
    significance = "FDR" in columns or "p_value" in columns
    if not quantitative and not significance:
        return None
    score = 0.0
    score += 4.0
    score += 3.0 if "delta_PSI" in columns else 0.0
    score += 2.0 if {"mean_PSI_group1", "mean_PSI_group2"} <= set(columns) else 0.0
    score += 0.8 if sample_columns else 0.0
    score += 3.0 if "FDR" in columns else (1.5 if "p_value" in columns else 0.0)
    score += 1.0 if "event_type" in columns else 0.0
    score += 1.0 if (
        "genomic_coordinates" in columns
        or {"chromosome", "start", "end"} <= set(columns)
    ) else 0.0
    if profile.row_count:
        score += 0.5
    lowered = profile.name.lower()
    if any(token in lowered for token in ("metadata", "sample", "design")):
        score -= 2.0
    if any(token in lowered for token in ("event", "psi", "mats", "splice", "as_")):
        score += 0.4
    return _Candidate(profile=profile, columns=columns, sample_columns=sample_columns, score=score)


def _heuristic_mapping(profiles: Sequence[FileProfile]) -> tuple[dict[str, Any], FileProfile | None, _Candidate | None]:
    candidates = [candidate for profile in profiles if (candidate := _candidate_for(profile))]
    candidates.sort(key=lambda item: item.score, reverse=True)
    candidate = candidates[0] if candidates else None
    metadata = _metadata_profile(profiles)
    if candidate is not None and metadata is not None and metadata.name == candidate.profile.name:
        metadata = None
    if candidate is None:
        return {}, metadata, None
    profile = candidate.profile
    mapping: dict[str, Any] = {
        "event_file": profile.name,
        "metadata_file": metadata.name if metadata else None,
        "delimiter": profile.delimiter,
        "encoding": profile.encoding,
        "header_row": profile.header_row,
        "columns": dict(candidate.columns),
        "sample_columns": dict(candidate.sample_columns),
        "event_type_map": _event_type_map(profile, candidate.columns.get("event_type")),
        "delta_direction": "group2-group1",
        "fdr_from_p": "auto",
        "coordinate_system": "unknown",
        "source_tool": profile.path.stem,
    }
    if metadata:
        metadata_columns = _map_columns(metadata.headers, METADATA_SYNONYMS)
        mapping["metadata_columns"] = metadata_columns
        group_header = metadata_columns.get("group")
        if group_header:
            mapping["groups"] = _pick_groups(metadata.column_values(group_header))
    if not mapping.get("groups"):
        inferred = {_infer_group(sample_id) for sample_id in candidate.sample_columns.values()}
        if {"Control", "Treatment"} <= inferred:
            mapping["groups"] = {"group1": "Control", "group2": "Treatment"}
    if candidate.sample_columns:
        mapping["sample_groups"] = {
            sample_id: _infer_group(sample_id) or ""
            for sample_id in candidate.sample_columns.values()
        }
    return mapping, metadata, candidate


# ---------------------------------------------------------------------------
# model-assisted mapping
# ---------------------------------------------------------------------------

_INGEST_SYSTEM = """You are the data-ingestion agent of SpliceGAIP, an alternative-splicing analysis platform.
Your job is to map a messy tabular export onto a fixed event schema. You may only use the file names and
column headers that are supplied; never invent them. Return a single JSON object and nothing else.
If a field cannot be mapped, omit it or use null. Prefer the heuristic guess when it is already correct."""


def _mapping_prompt(profiles: Sequence[FileProfile], heuristic: Mapping[str, Any]) -> str:
    files: list[dict[str, Any]] = []
    for profile in profiles:
        if not profile.supported or not profile.headers:
            continue
        files.append(
            {
                "name": profile.name,
                "row_count": profile.row_count,
                "headers": [profile.headers[index] for index in range(min(len(profile.headers), 120))],
                "sample_rows": [
                    [_truncate(cell) for cell in row[:120]]
                    for row in profile.sample_rows[:SAMPLE_ROWS]
                ],
            }
        )
        if len(files) >= 8:
            break
    schema: dict[str, str] = {}
    descriptions = {
        "event_id": "stable event identifier",
        "gene_id": "gene identifier (Ensembl / NCBI)",
        "gene_symbol": "gene symbol",
        "event_type": "one of SE, MXE, A5SS, A3SS, RI",
        "chromosome": "chromosome name",
        "strand": "+ or -",
        "genomic_coordinates": "coordinates such as chr1:100-200",
        "mean_PSI_group1": "mean PSI of the control/group1 samples",
        "mean_PSI_group2": "mean PSI of the treatment/group2 samples",
        "delta_PSI": "delta PSI, group2 minus group1 unless stated otherwise",
        "p_value": "raw p-value",
        "FDR": "multiple-testing adjusted p-value (FDR/q/BH/padj)",
        "inclusion_reads": "reads supporting inclusion",
        "exclusion_reads": "reads supporting exclusion",
        "total_support_reads": "total supporting reads",
    }
    for key, description in descriptions.items():
        schema[key] = description
    payload = {
        "task": "map an alternative-splicing table to the SpliceGAIP standard schema",
        "standard_schema": schema,
        "event_types": list(AS_EVENT_TYPES),
        "per_sample_psi_format": "PSI_<sample_id>",
        "files": files,
        "heuristic_guess": {
            "event_file": heuristic.get("event_file"),
            "metadata_file": heuristic.get("metadata_file"),
            "columns": heuristic.get("columns", {}),
            "sample_columns": heuristic.get("sample_columns", {}),
            "sample_groups": heuristic.get("sample_groups", {}),
            "event_type_map": heuristic.get("event_type_map", {}),
        },
        "rules": [
            "Use exact header strings from the file; do not translate or rename headers.",
            "Choose event_file from the supplied file names; metadata_file is optional.",
            "Per-sample PSI columns are those that hold one PSI value per sample; return them in sample_columns as {header: sample_id}.",
            "Assign each listed sample ID to a biological group in sample_groups as {sample_id: group_label}. Use only the supplied sample IDs. Infer labels from sample names and metadata; leave uncertain samples empty for human review.",
            "Map event-type labels to SE/MXE/A5SS/A3SS/RI in event_type_map.",
            "delta_direction is 'group2-group1' or 'group1-group2'.",
            "Set fdr_from_p to true only when FDR must be approximated from the p-value column.",
            "Add short notes for anything a human should review.",
        ],
        "response_format": {
            "event_file": "string",
            "metadata_file": "string or null",
            "columns": {"gene_symbol": "header", "delta_PSI": "header"},
            "sample_columns": {"PSI_S1": "S1"},
            "sample_groups": {"S1": "Control"},
            "event_type_map": {"label": "SE"},
            "groups": {"group1": "label", "group2": "label"},
            "delta_direction": "group2-group1",
            "coordinate_system": "unknown",
            "fdr_from_p": False,
            "confidence": 0.0,
            "notes": ["..."],
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _sanitize_mapping(
    raw: Mapping[str, Any] | Any,
    profiles: Sequence[FileProfile],
    heuristic: Mapping[str, Any],
    metadata_profile: FileProfile | None,
    *,
    allow_clear: bool = False,
) -> tuple[dict[str, Any], list[str], int]:
    """Merge a model proposal into the heuristic mapping, rejecting hallucinations.

    Returns ``(mapping, notes, accepted)`` where ``accepted`` counts proposals
    that survived header/file validation. Zero means the model produced
    nothing usable and the caller should report heuristic provenance.
    """
    notes: list[str] = []
    accepted = 0
    mapping: dict[str, Any] = dict(heuristic)
    by_name = {profile.name: profile for profile in profiles}
    if not isinstance(raw, Mapping):
        if raw is not None:
            notes.append("model returned a non-object mapping; heuristic mapping used")
        return mapping, notes, accepted

    candidate_name = str(raw.get("event_file") or "").strip()
    if candidate_name and candidate_name in by_name and by_name[candidate_name].supported:
        mapping["event_file"] = candidate_name
        accepted += 1
    elif candidate_name:
        notes.append(f"model selected unknown event file {candidate_name!r}; ignored")

    metadata_name = raw.get("metadata_file")
    if metadata_name in (None, ""):
        if "metadata_file" not in mapping:
            mapping["metadata_file"] = None
    elif str(metadata_name) in by_name and by_name[str(metadata_name)].supported:
        mapping["metadata_file"] = str(metadata_name)
        accepted += 1
    else:
        notes.append(f"model selected unknown metadata file {metadata_name!r}; ignored")

    event_profile = by_name.get(str(mapping.get("event_file") or ""))
    if event_profile is None:
        return mapping, notes, accepted

    columns = dict(heuristic.get("columns") or {})
    proposed_columns = raw.get("columns")
    if isinstance(proposed_columns, Mapping):
        lowered = {header.lower(): header for header in event_profile.headers}
        for field_name, header in proposed_columns.items():
            if field_name not in COLUMN_SYNONYMS and field_name not in {"start", "end", "coordinate_system"}:
                continue
            if header in (None, ""):
                if allow_clear:
                    columns.pop(field_name, None)
                continue
            resolved = lowered.get(str(header).strip().lower())
            if resolved is None:
                notes.append(f"model mapped {field_name} to unknown header {header!r}; ignored")
                continue
            columns[field_name] = resolved
            accepted += 1
    mapping["columns"] = columns

    if not ({"gene_symbol", "gene_id"} & set(columns)):
        fallback = by_name.get(str(heuristic.get("event_file") or ""))
        if fallback is not None and fallback is not event_profile:
            event_profile = fallback
            mapping["event_file"] = fallback.name
            mapping["columns"] = dict(heuristic.get("columns") or {})
            notes.append("mapping left no gene column; reverted to the heuristic event file")
            accepted = 0

    sample_columns = dict(heuristic.get("sample_columns") or {})
    proposed_samples = raw.get("sample_columns")
    if isinstance(proposed_samples, Mapping):
        valid_headers = set(event_profile.headers)
        for header, sample_id in proposed_samples.items():
            header = str(header or "").strip()
            sample_id = str(sample_id or "").strip()
            if header in valid_headers and sample_id:
                if sample_id in sample_columns.values() and sample_columns.get(header) != sample_id:
                    continue
                sample_columns[header] = sample_id
                accepted += 1
            elif header:
                notes.append(f"model proposed unknown sample column {header!r}; ignored")
    if sample_columns:
        mapping["sample_columns"] = sample_columns
    else:
        mapping.pop("sample_columns", None)
    sample_ids = set(sample_columns.values())
    sample_groups = {sample_id: str(group or "").strip() for sample_id, group in
                     (heuristic.get("sample_groups") or {}).items() if sample_id in sample_ids}
    if isinstance(raw.get("sample_groups"), Mapping):
        for sample_id, group in raw["sample_groups"].items():
            if sample_id not in sample_ids:
                notes.append(f"unknown sample ID {sample_id!r}; ignored")
                continue
            label = str(group or "").strip()[:80]
            if label:
                sample_groups[sample_id] = label
                accepted += 1
            elif allow_clear:
                sample_groups[sample_id] = ""
    mapping["sample_groups"] = sample_groups
    if raw.get("sample_groups_confirmed") is True:
        mapping["sample_groups_confirmed"] = True

    proposed_types = raw.get("event_type_map")
    if isinstance(proposed_types, Mapping) and "event_type" in columns:
        observed = set(event_profile.column_values(columns["event_type"]))
        type_map = dict(heuristic.get("event_type_map") or {})
        for value, canonical in proposed_types.items():
            value = str(value or "").strip()
            normalized = _normalize_event_type(canonical)
            if value in observed and normalized:
                type_map[value] = normalized
                accepted += 1
        mapping["event_type_map"] = type_map

    if raw.get("delta_direction") in {"group1-group2", "group2-group1"}:
        mapping["delta_direction"] = raw["delta_direction"]
        accepted += 1
    if isinstance(raw.get("fdr_from_p"), bool):
        mapping["fdr_from_p"] = "always" if raw["fdr_from_p"] else "never"
        accepted += 1
    coordinate_system = str(raw.get("coordinate_system") or "").strip()
    if coordinate_system:
        mapping["coordinate_system"] = coordinate_system
        accepted += 1
    groups = raw.get("groups")
    if isinstance(groups, Mapping):
        group1 = str(groups.get("group1") or "").strip()
        group2 = str(groups.get("group2") or "").strip()
        if group1 and group2 and group1 != group2:
            mapping["groups"] = {"group1": group1, "group2": group2}
            accepted += 1
    if metadata_profile is not None and "metadata_columns" not in mapping:
        columns_meta = _map_columns(metadata_profile.headers, METADATA_SYNONYMS)
        if columns_meta:
            mapping["metadata_columns"] = columns_meta
    if raw.get("confidence") is not None:
        try:
            mapping["llm_confidence"] = max(0.0, min(float(raw["confidence"]), 1.0))
        except (TypeError, ValueError):
            pass
    notes.extend(_truncate(note, 160) for note in (raw.get("notes") or [])[:5] if str(note).strip())
    return mapping, notes, accepted


# ---------------------------------------------------------------------------
# conversion
# ---------------------------------------------------------------------------


def _parse_float(value: Any, *, decimal_comma: bool | None = None) -> tuple[float | None, bool]:
    """Parse vendor numbers; returns ``(value, was_percent)``.

    ``decimal_comma`` disambiguates a lone comma: PSI/p-values use decimal
    commas in European exports, while read counts use thousands separators.
    """
    text = str(value if value is not None else "").strip()
    if not text:
        return None, False
    text = (
        text.replace("\u2212", "-")
        .replace("−", "-")
        .replace("–", "-")
        .replace("\u00a0", " ")
    )
    percent = text.endswith("%") or text.startswith("%")
    text = text.strip("%").strip()
    text = text.lstrip("<>≤≥~≈").strip()
    normalized = _norm(text)
    if not text or normalized in _NA_VALUES:
        return None, percent
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            # European style: 1.234,56 -> 1234.56
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        if decimal_comma is True:
            text = text.replace(",", ".")
        elif decimal_comma is False:
            text = text.replace(",", "")
        else:
            pieces = text.split(",")
            if len(pieces) == 2 and 1 <= len(pieces[1]) <= 2:
                text = ".".join(pieces)
            else:
                text = "".join(pieces)
    try:
        number = float(text)
    except ValueError:
        return None, percent
    if percent:
        number /= 100.0
    return number, percent


def _parse_int(value: Any) -> int | None:
    number, _ = _parse_float(value)
    return None if number is None else int(round(number))


def _normalize_strand(value: Any) -> str:
    text = str(value or "").strip()
    lowered = text.lower()
    if lowered in {"+", "plus", "forward", "f", "1", "正", "正向"}:
        return "+"
    if lowered in {"-", "minus", "reverse", "r", "-1", "负", "反向"}:
        return "-"
    return text


def _build_coordinates(
    chromosome: str,
    start: str,
    end: str,
    explicit: str,
) -> str:
    if explicit.strip():
        return explicit.strip()
    if start.strip() or end.strip():
        span = f"{start.strip() or '?'}-{end.strip() or '?'}"
        return f"{chromosome.strip()}:{span}" if chromosome.strip() else span
    return ""


def _metadata_rows(
    profile: FileProfile,
    mapping: Mapping[str, Any],
    issues: list[dict[str, str]],
) -> list[SampleMetadata]:
    columns = mapping.get("metadata_columns")
    if not isinstance(columns, Mapping):
        columns = _map_columns(profile.headers, METADATA_SYNONYMS)
    if "sample_id" not in columns:
        issues.append(
            _issue(
                "warning",
                "metadata_without_sample_id",
                "样本元数据文件未识别出样本 ID 列，已跳过该文件。",
                "No sample-id column was found in the metadata file; it was skipped.",
            )
        )
        return []
    sample_header = str(columns["sample_id"])
    indices = {str(header): index for index, header in enumerate(profile.headers)}
    if sample_header not in indices:
        return []
    rows: list[SampleMetadata] = []
    seen: set[str] = set()
    for row in profile.iter_rows():
        def value(field_name: str) -> str:
            header = columns.get(field_name)
            if not header or header not in indices:
                return ""
            index = indices[header]
            return row[index].strip() if index < len(row) else ""

        sample_id = value("sample_id")
        if not sample_id or sample_id in seen:
            continue
        seen.add(sample_id)
        rows.append(
            SampleMetadata(
                sample_id=sample_id,
                group=value("group"),
                condition=value("condition") or value("group"),
                tissue=value("tissue"),
                batch=value("batch"),
            )
        )
    groups = {sample.group for sample in rows if sample.group}
    if len(groups) < 2:
        issues.append(
            _issue(
                "warning",
                "single_group_metadata",
                "样本元数据少于两组；已跳过元数据，分析仍可使用文件中的组均值。",
                "Metadata defines fewer than two groups; it was skipped so differential analysis can proceed.",
            )
        )
        return []
    return rows


def _synthesized_metadata(
    sample_columns: Mapping[str, str],
    issues: list[dict[str, str]],
    sample_groups: Mapping[str, str] | None = None,
) -> list[SampleMetadata]:
    if not sample_columns:
        return []
    supplied = sample_groups or {}
    inferred = {sample_id: str(supplied.get(sample_id) or _infer_group(sample_id) or "").strip()
                for sample_id in sample_columns.values()}
    labels = {label for label in inferred.values() if label}
    if len(labels) < 2 or any(not label for label in inferred.values()):
        issues.append(
            _issue(
                "info",
                "no_sample_groups",
                "检测到每样本 PSI 列，但样本名中没有可识别的对照/处理标签；未生成样本元数据。",
                "Per-sample PSI columns were found without recognizable control/treatment labels; no metadata was generated.",
            )
        )
        return []
    return [
        SampleMetadata(
            sample_id=sample_id,
            group=inferred[sample_id],
            condition=inferred[sample_id],
        )
        for sample_id in sample_columns.values()
    ]


@dataclass
class Conversion:
    events: list[StandardEvent]
    samples: list[SampleMetadata]
    issues: list[dict[str, str]]
    total_rows: int = 0
    dropped: int = 0
    drop_reasons: Counter[str] = field(default_factory=Counter)
    sample_columns: dict[str, str] = field(default_factory=dict)
    normalized_types: Counter[str] = field(default_factory=Counter)

    def stats(self, validation: Mapping[str, Any] | None = None) -> dict[str, Any]:
        events = self.events
        fdr = sum(1 for event in events if event.fdr is not None)
        delta = sum(1 for event in events if event.delta_psi is not None)
        types = Counter(event.event_type or "UNKNOWN" for event in events)
        groups = Counter(sample.group for sample in self.samples)
        return {
            "total_rows": self.total_rows,
            "valid_events": len(events),
            "dropped": self.dropped,
            "drop_reasons": dict(self.drop_reasons),
            "fdr_coverage": round(fdr / len(events), 3) if events else 0.0,
            "delta_coverage": round(delta / len(events), 3) if events else 0.0,
            "event_types": dict(types),
            "groups": dict(groups),
            "sample_count": len(self.samples),
            "sample_psi_columns": len(self.sample_columns),
            "validation": dict(validation or {}),
        }

    def preview_rows(self, limit: int = 5) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for event in self.events[:limit]:
            rows.append(
                {
                    "event_id": event.event_id,
                    "gene": event.gene_symbol or event.gene_id,
                    "event_type": event.event_type,
                    "delta_psi": event.delta_psi,
                    "fdr": event.fdr,
                    "p_value": event.p_value,
                    "coordinates": event.genomic_coordinates,
                }
            )
        return rows


def _convert(
    profile: FileProfile,
    mapping: Mapping[str, Any],
    issues: list[dict[str, str]],
) -> Conversion:
    columns = {str(key): str(value) for key, value in (mapping.get("columns") or {}).items()}
    headers = {header: index for index, header in enumerate(profile.headers)}
    sample_columns = {
        str(header): str(sample_id)
        for header, sample_id in (mapping.get("sample_columns") or {}).items()
        if header in headers and sample_id
    }
    event_type_map = {
        str(value): str(canonical)
        for value, canonical in (mapping.get("event_type_map") or {}).items()
    }
    direction = mapping.get("delta_direction") or "group2-group1"
    sign = 1.0 if direction == "group2-group1" else -1.0

    conversion = Conversion(
        events=[],
        samples=[],
        issues=issues,
        sample_columns=dict(sample_columns),
    )

    def header_for(field_name: str) -> str | None:
        header = columns.get(field_name)
        return header if header in headers else None

    def cell(row: Sequence[str], field_name: str) -> str:
        header = header_for(field_name)
        if header is None:
            return ""
        index = headers[header]
        return row[index].strip() if index < len(row) else ""

    def numeric(row: Sequence[str], field_name: str) -> tuple[float | None, bool]:
        return _parse_float(cell(row, field_name), decimal_comma=True)

    used_ids: set[str] = set()
    tool = str(mapping.get("source_tool") or profile.path.stem)
    coordinate_system = str(mapping.get("coordinate_system") or "unknown")
    dropped_types = Counter()
    scaled_psi = False

    def as_psi(value: float | None, *, signed: bool = False) -> float | None:
        """Interpret 0-100 values as percentages; real PSI/ΔPSI is within [-1, 1]."""
        nonlocal scaled_psi
        if value is None:
            return None
        magnitude = abs(value) if signed else value
        if 1.0 < magnitude <= 100.0:
            scaled_psi = True
            return value / 100.0
        return value

    for index, row in enumerate(profile.iter_rows(), start=1):
        conversion.total_rows += 1
        gene_id = cell(row, "gene_id")
        gene_symbol = cell(row, "gene_symbol")
        if not gene_id and not gene_symbol:
            conversion.dropped += 1
            conversion.drop_reasons["missing_gene"] += 1
            continue
        gene_id = gene_id or gene_symbol
        gene_symbol = gene_symbol or gene_id

        raw_type = cell(row, "event_type")
        event_type = event_type_map.get(raw_type)
        if event_type is None:
            event_type = _normalize_event_type(raw_type)
        if event_type is None:
            event_type = (raw_type or "UNKNOWN").upper()
            dropped_types[event_type] += 1
        else:
            conversion.normalized_types[event_type] += 1

        mean1, _ = numeric(row, "mean_PSI_group1")
        mean2, _ = numeric(row, "mean_PSI_group2")
        delta, _ = numeric(row, "delta_PSI")
        mean1 = as_psi(mean1)
        mean2 = as_psi(mean2)
        delta = as_psi(delta, signed=True)

        p_value, _ = numeric(row, "p_value")
        fdr, _ = numeric(row, "FDR")
        if delta is not None:
            delta *= sign

        psi_by_sample: dict[str, float] = {}
        for header, sample_id in sample_columns.items():
            value, _ = _parse_float(
                row[headers[header]] if headers[header] < len(row) else "",
                decimal_comma=True,
            )
            value = as_psi(value)
            if value is not None:
                psi_by_sample[sample_id] = value

        if delta is None and mean1 is not None and mean2 is not None:
            delta = sign * (mean2 - mean1)

        event_id = cell(row, "event_id")
        if not event_id:
            event_id = f"ING_{index:06d}"
        if event_id in used_ids:
            suffix = 2
            while f"{event_id}_{suffix}" in used_ids:
                suffix += 1
            event_id = f"{event_id}_{suffix}"
        used_ids.add(event_id)

        chromosome = cell(row, "chromosome")
        start = cell(row, "start")
        end = cell(row, "end")
        coordinates = _build_coordinates(
            chromosome, start, end, cell(row, "genomic_coordinates")
        )
        conversion.events.append(
            StandardEvent(
                event_id=event_id,
                gene_id=gene_id,
                gene_symbol=gene_symbol,
                event_type=event_type,
                chromosome=chromosome,
                strand=_normalize_strand(cell(row, "strand")),
                genomic_coordinates=coordinates,
                coordinate_system=coordinate_system,
                source_tool=tool,
                mean_psi_group1=mean1,
                mean_psi_group2=mean2,
                delta_psi=delta,
                p_value=p_value,
                fdr=fdr,
                psi_by_sample=psi_by_sample,
                inclusion_reads=_parse_int(cell(row, "inclusion_reads")),
                exclusion_reads=_parse_int(cell(row, "exclusion_reads")),
                total_support_reads=_parse_int(cell(row, "total_support_reads")),
                valid_sample_count=_parse_int(cell(row, "valid_sample_count")),
                single_sample_driven=_parse_bool(cell(row, "single_sample_driven")),
                mapping_ambiguity=_parse_bool(cell(row, "mapping_ambiguity")),
                confidence_level=cell(row, "confidence_level"),
            )
        )

    if scaled_psi:
        issues.append(
            _issue(
                "info",
                "psi_percent_scaled",
                "部分 PSI / ΔPSI 值大于 1，已按百分比（0–100）除以 100。",
                "Some PSI / delta-PSI values exceeded 1 and were interpreted as percentages (divided by 100).",
            )
        )

    # FDR fallback: only with an explicit, visible warning.
    fdr_mode = str(mapping.get("fdr_from_p") or "auto")
    if fdr_mode != "never":
        missing_fdr = [event for event in conversion.events if event.fdr is None]
        usable_p = [event for event in missing_fdr if event.p_value is not None]
        if missing_fdr and len(usable_p) == len(missing_fdr):
            for event in missing_fdr:
                event.fdr = event.p_value
            if "FDR" in columns:
                zh = f"{len(missing_fdr)} 个事件缺少 FDR/q 值，已用原始 p 值填充；结果可能偏宽松。"
                en = (
                    f"{len(missing_fdr)} events had no FDR/q value and were filled with raw p-values. "
                    "This is anti-conservative."
                )
            else:
                zh = "输入没有 FDR/q 值，已将原始 p 值作为 FDR 使用；结果可能偏宽松，建议补充校正后的 q 值。"
                en = (
                    "No FDR/q column was available; raw p-values were used as FDR. "
                    "This is anti-conservative — supply adjusted q-values when possible."
                )
            issues.append(_issue("warning", "fdr_from_p", zh, en))
        elif missing_fdr:
            issues.append(
                _issue(
                    "warning",
                    "missing_fdr",
                    f"{len(missing_fdr)} 个事件缺少 FDR，且没有可用的 p 值可替代；显著性筛选会跳过这些事件。",
                    f"{len(missing_fdr)} events have no FDR and no p-value fallback; significance filtering will skip them.",
                )
            )

    if conversion.dropped:
        reasons = ", ".join(f"{key}={value}" for key, value in conversion.drop_reasons.items())
        issues.append(
            _issue(
                "warning",
                "rows_dropped",
                f"共跳过 {conversion.dropped} 行无法标准化的事件（{reasons}）。",
                f"{conversion.dropped} rows could not be standardized and were dropped ({reasons}).",
            )
        )
    if dropped_types:
        detail = ", ".join(f"{key}={value}" for key, value in dropped_types.most_common(5))
        issues.append(
            _issue(
                "warning",
                "unknown_event_type",
                f"部分剪接类型无法映射到 SE/MXE/A5SS/A3SS/RI：{detail}。已保留原始标签。",
                f"Some event-type labels could not be mapped to SE/MXE/A5SS/A3SS/RI: {detail}. Raw labels were kept.",
            )
        )
    if not header_for("event_type"):
        issues.append(
            _issue(
                "info",
                "no_event_type",
                "输入没有剪接类型列；事件将标记为 UNKNOWN。",
                "No event-type column was found; events are labelled UNKNOWN.",
            )
        )
    if not header_for("genomic_coordinates") and not (
        header_for("chromosome") or header_for("start") or header_for("end")
    ):
        issues.append(
            _issue(
                "info",
                "no_coordinates",
                "输入没有坐标列；事件仍可分析，但无法在基因组上定位。",
                "No coordinate columns were found; events remain analyzable but cannot be placed on the genome.",
            )
        )

    # Metadata: an explicit file is authoritative; only synthesize from sample
    # names when the input supplied no metadata file at all.
    metadata_file = mapping.get("metadata_file")
    metadata_profile = next(
        (profile for profile in (mapping.get("_profiles") or []) if profile.name == metadata_file),
        None,
    )
    if metadata_profile is not None:
        conversion.samples = _metadata_rows(metadata_profile, mapping, issues)
    if sample_columns and (not conversion.samples or mapping.get("sample_groups_confirmed")):
        confirmed = _synthesized_metadata(sample_columns, issues, mapping.get("sample_groups"))
        if confirmed:
            previous = {sample.sample_id: sample for sample in conversion.samples}
            conversion.samples = [
                SampleMetadata(
                    sample_id=sample.sample_id,
                    group=sample.group,
                    condition=sample.group,
                    tissue=previous[sample.sample_id].tissue if sample.sample_id in previous else "",
                    batch=previous[sample.sample_id].batch if sample.sample_id in previous else "",
                )
                for sample in confirmed
            ]

    # Derive per-group means from per-sample PSI when the table only has samples.
    if conversion.samples and sample_columns and any(
        event.mean_psi_group1 is None or event.mean_psi_group2 is None
        for event in conversion.events
    ):
        groups: dict[str, list[str]] = {}
        for sample in conversion.samples:
            groups.setdefault(sample.group, []).append(sample.sample_id)
        labels = sorted(groups)
        if len(labels) >= 2:
            group1, group2 = labels[0], labels[-1]
            for event in conversion.events:
                values1 = [event.psi_by_sample[sid] for sid in groups[group1] if sid in event.psi_by_sample]
                values2 = [event.psi_by_sample[sid] for sid in groups[group2] if sid in event.psi_by_sample]
                if event.mean_psi_group1 is None and values1:
                    event.mean_psi_group1 = sum(values1) / len(values1)
                if event.mean_psi_group2 is None and values2:
                    event.mean_psi_group2 = sum(values2) / len(values2)
                if event.delta_psi is None and event.mean_psi_group1 is not None and event.mean_psi_group2 is not None:
                    event.delta_psi = sign * (event.mean_psi_group2 - event.mean_psi_group1)
            issues.append(
                _issue(
                    "info",
                    "means_from_samples",
                    "组均值由每样本 PSI 计算得到。",
                    "Group means were computed from per-sample PSI values.",
                )
            )

    return conversion


def _parse_bool(value: Any) -> bool | None:
    text = str(value or "").strip().lower()
    if text in {"true", "1", "yes", "y", "是"}:
        return True
    if text in {"false", "0", "no", "n", "否"}:
        return False
    return None


# ---------------------------------------------------------------------------
# confidence, validation, public API
# ---------------------------------------------------------------------------


def _confidence(
    mapping: Mapping[str, Any],
    conversion: Conversion,
    llm_used: bool,
) -> dict[str, Any]:
    columns = mapping.get("columns") or {}
    reasons: list[str] = []
    score = 0.15
    if "gene_symbol" in columns or "gene_id" in columns:
        score += 0.15
    else:
        reasons.append("基因列未确定")
    if "delta_PSI" in columns:
        score += 0.18
        reasons.append("ΔPSI 列已识别")
    elif {"mean_PSI_group1", "mean_PSI_group2"} <= set(columns):
        score += 0.13
        reasons.append("由两组均值计算 ΔPSI")
    elif mapping.get("sample_columns"):
        score += 0.1
        reasons.append("由每样本 PSI 计算组均值")
    if "FDR" in columns:
        score += 0.18
        reasons.append("FDR 列已识别")
    elif "p_value" in columns:
        score += 0.08
        reasons.append("仅有 p 值（用作 FDR 近似）")
    if "event_type" in columns:
        score += 0.08
        reasons.append("剪接类型列已识别")
    if "genomic_coordinates" in columns or {"chromosome", "start", "end"} <= set(columns):
        score += 0.05
    if conversion.samples and len({sample.group for sample in conversion.samples}) >= 2:
        score += 0.07
        reasons.append("样本分组已识别")
    if conversion.sample_columns:
        score += 0.03
    if conversion.total_rows:
        valid_ratio = len(conversion.events) / conversion.total_rows
        score *= 0.55 + 0.45 * valid_ratio
        if valid_ratio < 0.9:
            reasons.append(f"有效率 {valid_ratio:.0%}")
    if llm_used:
        llm_confidence = mapping.get("llm_confidence")
        if isinstance(llm_confidence, (int, float)):
            score = score * 0.75 + float(llm_confidence) * 0.25
            reasons.append(f"模型自评 {float(llm_confidence):.0%}")
        else:
            score += 0.04
    else:
        score += 0.03
    score = max(0.05, min(score, 0.99))
    level = "high" if score >= 0.8 else ("medium" if score >= 0.55 else "low")
    return {"score": round(score, 2), "level": level, "reasons": reasons}


def _validation_payload(events: Sequence[StandardEvent], samples: Sequence[SampleMetadata]) -> dict[str, Any]:
    dataset = Dataset(
        name="ingestion_preview",
        source_dir=Path("."),
        source_format="ingested",
        events=list(events),
        samples=list(samples),
    )
    return validate_dataset(dataset).as_dict()


def _validation_issues(validation: Mapping[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for raw in validation.get("issues") or []:
        if not isinstance(raw, Mapping):
            continue
        severity = str(raw.get("severity") or "warning")
        code = str(raw.get("code") or "")
        message = str(raw.get("message") or "")
        template = VALIDATION_ZH.get(code)
        if template:
            match = re.match(r"(\d+)", message)
            translated = template.format(n=match.group(1)) if "{n}" in template and match else template
        else:
            translated = message
        issues.append(_issue(severity, f"validation_{code}", translated, message))
    return issues


def _native_preview(directory: Path) -> dict[str, Any] | None:
    try:
        dataset = load_dataset(directory)
    except Exception:  # noqa: BLE001 - native detection must never break preview
        return None
    validation = validate_dataset(dataset)
    sample_ids = sorted({sample_id for event in dataset.events for sample_id in event.psi_by_sample})
    known = {sample.sample_id: sample.group for sample in dataset.samples}
    proposed = {sample_id: known.get(sample_id) or _infer_group(sample_id) or "" for sample_id in sample_ids}
    return {
        "status": "native",
        "native": True,
        "native_format": dataset.source_format,
        "summary": dataset.summary(),
        "validation": validation.as_dict(),
        "issues": _validation_issues(validation.as_dict()),
        "agent_trace": [
            {
                "step": "profile",
                "status": "ok",
                "detail": f"已识别原生格式 {dataset.source_format}，无需字段映射。",
                "detail_en": f"Native {dataset.source_format} input recognized; no mapping needed.",
            }
        ],
        "event_file": None,
        "mapping": {"sample_groups": proposed} if sample_ids else {},
        "sample_ids": sample_ids,
        "preview": {
            "total_rows": len(dataset.events),
            "valid_events": len(dataset.events),
            "dropped": 0,
            "fdr_coverage": round(
                sum(1 for event in dataset.events if event.fdr is not None) / max(len(dataset.events), 1), 3
            ),
            "delta_coverage": round(
                sum(1 for event in dataset.events if event.delta_psi is not None) / max(len(dataset.events), 1), 3
            ),
            "event_types": dataset.summary().get("event_types", {}),
            "groups": dataset.summary().get("groups", {}),
            "sample_count": len(dataset.samples),
            "sample_psi_columns": len(
                {sample_id for event in dataset.events for sample_id in event.psi_by_sample}
            ),
            "validation": validation.as_dict(),
        },
    }


def preview_ingestion(
    input_dir: str | Path,
    *,
    settings: Any = None,
    use_llm: bool = True,
    enhancer: Any = None,
) -> dict[str, Any]:
    """Profile ``input_dir``, propose a mapping and preview standardized events."""
    started = time.perf_counter()
    directory = Path(input_dir)
    trace: list[dict[str, Any]] = []

    def step(name: str, status: str, detail_zh: str, detail_en: str) -> None:
        trace.append(
            {
                "step": name,
                "status": status,
                "detail": detail_zh,
                "detail_en": detail_en,
            }
        )

    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Input directory not found: {directory}")

    native = _native_preview(directory)
    if native is not None:
        sample_ids = native.get("sample_ids") or []
        if sample_ids and use_llm and not all(native["mapping"]["sample_groups"].values()):
            try:
                if enhancer is None:
                    from splicegaip.llm.enrich import LLMEnhancer
                    if settings is None:
                        from splicegaip.config import load_settings
                        settings = load_settings()
                    enhancer = LLMEnhancer(settings, features=("ingest",))
                if getattr(enhancer, "has", lambda _feature: False)("ingest"):
                    proposal = enhancer.json(
                        system=_INGEST_SYSTEM,
                        user=json.dumps({"task": "Suggest biological group for each sample ID; leave uncertain groups empty. Return sample_groups only.", "sample_ids": sample_ids, "known_groups": native["mapping"]["sample_groups"]}, ensure_ascii=False),
                        feature="ingest", max_tokens=1200, temperature=0.0, timeout=60,
                    )
                    if isinstance(proposal, Mapping) and isinstance(proposal.get("sample_groups"), Mapping):
                        for sample_id, label in proposal["sample_groups"].items():
                            if sample_id in sample_ids and str(label or "").strip():
                                native["mapping"]["sample_groups"][sample_id] = str(label).strip()[:80]
                        native["mapping_source"] = "llm+heuristic"
            except Exception:  # noqa: BLE001 - group review remains available
                pass
        native["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
        return native

    step(
        "profile",
        "running",
        "严格加载器未识别数据，开始逐文件画像。",
        "Strict loader did not recognize the input; profiling files individually.",
    )
    profiles = _profile_directory(directory)
    supported = [profile for profile in profiles if profile.supported and profile.headers]
    step(
        "profile",
        "ok" if supported else "error",
        f"已画像 {len(profiles)} 个文件，其中 {len(supported)} 个可解析为表格。",
        f"Profiled {len(profiles)} files; {len(supported)} are parseable tables.",
    )

    if not supported:
        result = {
            "status": "unmappable",
            "native": False,
            "files": [profile.to_dict() for profile in profiles],
            "issues": [
                _issue(
                    "error",
                    "no_tables",
                    "没有找到可解析的 CSV/TSV/TXT 表格。请上传文本表格（Excel 请先另存为 CSV）。",
                    "No parseable CSV/TSV/TXT table was found. Export spreadsheets as CSV first.",
                )
            ],
            "agent_trace": trace,
            "mapping": {},
            "preview": {},
            "confidence": {"score": 0.0, "level": "low", "reasons": []},
            "llm": {"attempted": False, "used": False, "errors": []},
            "privacy": "只向模型发送列名与最多 3 行样例，不发送完整文件。",
            "privacy_en": "Only headers and up to 3 sample rows are sent to the model; the full file stays local.",
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }
        return result

    heuristic, metadata_profile, candidate = _heuristic_mapping(supported)
    step(
        "heuristic",
        "ok" if candidate else "warn",
        (
            f"同义词规则命中 {len(heuristic.get('columns') or {})} 个字段。"
            if candidate
            else "同义词规则未能确定事件表。"
        ),
        (
            f"Synonym rules matched {len(heuristic.get('columns') or {})} fields."
            if candidate
            else "Synonym rules could not identify an event table."
        ),
    )

    llm_used = False
    llm_attempted = False
    llm_errors: list[dict[str, str]] = []
    llm_notes: list[str] = []
    mapping = heuristic
    if candidate is not None and use_llm:
        llm_attempted = True
        try:
            if enhancer is None:
                from splicegaip.llm.enrich import LLMEnhancer

                if settings is None:
                    from splicegaip.config import load_settings

                    settings = load_settings()
                enhancer = LLMEnhancer(settings, features=("ingest",))
                enhancer.max_retries = min(getattr(enhancer, "max_retries", 2), 2)
            if getattr(enhancer, "has", lambda _feature: False)("ingest"):
                step(
                    "llm",
                    "running",
                    "模型正在阅读列名与样例行，提出字段映射建议…",
                    "The model is reading headers and sample rows to propose a mapping…",
                )
                proposal = enhancer.json(
                    system=_INGEST_SYSTEM,
                    user=_mapping_prompt(supported, heuristic),
                    feature="ingest",
                    max_tokens=1600,
                    temperature=0.0,
                    timeout=60,
                )
                if proposal is not None:
                    mapping, llm_notes, accepted = _sanitize_mapping(
                        proposal, supported, heuristic, metadata_profile
                    )
                    llm_used = accepted > 0
                    step(
                        "llm",
                        "ok" if llm_used else "warn",
                        (
                            "模型映射建议已通过列名校验。"
                            if llm_used
                            else "模型建议未通过列名校验，保留确定性映射。"
                        ),
                        (
                            "The model's mapping was validated against the real headers."
                            if llm_used
                            else "The model's proposal failed header validation; the deterministic mapping is kept."
                        ),
                    )
                else:
                    step(
                        "llm",
                        "warn",
                        "模型未返回可用映射，保留确定性同义词映射。",
                        "The model returned no usable mapping; the deterministic mapping is kept.",
                    )
            else:
                step(
                    "llm",
                    "skip",
                    "未配置模型，使用确定性同义词映射。",
                    "No model configured; using the deterministic synonym mapping.",
                )
            llm_errors = [
                {"feature": str(item.get("feature") or ""), "error": _scrub(str(item.get("error") or ""))}
                for item in (getattr(enhancer, "errors", None) or [])[-3:]
            ]
        except Exception as error:  # noqa: BLE001 - mapping must never block
            llm_errors = [{"feature": "ingest", "error": _scrub(str(error))}]
            step(
                "llm",
                "warn",
                "模型映射失败，已回退到确定性映射。",
                "Model mapping failed; fell back to the deterministic mapping.",
            )

    if candidate is None:
        result = {
            "status": "unmappable",
            "native": False,
            "files": [profile.to_dict() for profile in profiles],
            "issues": [
                _issue(
                    "error",
                    "no_event_table",
                    "没有找到同时包含基因列与定量/显著性列的表格。请检查文件，或手动指定列映射。",
                    "No table with both a gene column and quantitative/significance columns was found.",
                )
            ],
            "agent_trace": trace,
            "mapping": {},
            "preview": {},
            "confidence": {"score": 0.0, "level": "low", "reasons": []},
            "llm": {"attempted": llm_attempted, "used": llm_used, "errors": llm_errors},
        }
        return result

    event_profile = next(
        (profile for profile in supported if profile.name == mapping.get("event_file")),
        candidate.profile,
    )
    mapping["_profiles"] = supported  # internal only; removed before returning
    issues: list[dict[str, str]] = []
    conversion = _convert(event_profile, mapping, issues)
    mapping.pop("_profiles", None)
    issues.extend(_validation_issues(_validation_payload(conversion.events, conversion.samples)))

    validation = _validation_payload(conversion.events, conversion.samples)
    confidence = _confidence(mapping, conversion, llm_used)
    stats = conversion.stats(validation)
    essential_missing: list[str] = []
    if not conversion.events:
        essential_missing.append("没有可用事件行")
    if not ({"gene_symbol", "gene_id"} & set(mapping.get("columns") or {})):
        essential_missing.append("基因列")
    if "delta_PSI" not in (mapping.get("columns") or {}) and not (
        {"mean_PSI_group1", "mean_PSI_group2"} <= set(mapping.get("columns") or {})
    ) and not conversion.sample_columns:
        essential_missing.append("ΔPSI/组均值")
    if "FDR" not in (mapping.get("columns") or {}) and "p_value" not in (mapping.get("columns") or {}):
        essential_missing.append("FDR/p 值")
    if essential_missing:
        issues.append(
            _issue(
                "error",
                "essential_fields_missing",
                "缺少关键字段：" + "、".join(essential_missing) + "。",
                "Missing essential fields: " + ", ".join(essential_missing) + ".",
            )
        )
    status = "unmappable" if not conversion.events else (
        "needs_review" if essential_missing or confidence["level"] == "low" else "mapped"
    )
    step(
        "validate",
        "ok" if not essential_missing else "warn",
        f"标准化完成：{len(conversion.events)}/{conversion.total_rows} 行可分析，"
        f"FDR 覆盖 {stats['fdr_coverage']:.0%}，ΔPSI 覆盖 {stats['delta_coverage']:.0%}。",
        f"Standardized {len(conversion.events)}/{conversion.total_rows} rows; "
        f"FDR coverage {stats['fdr_coverage']:.0%}, delta-PSI coverage {stats['delta_coverage']:.0%}.",
    )
    step(
        "preview",
        "ok",
        f"置信度 {confidence['level']}（{confidence['score']:.0%}），请确认映射后开始分析。",
        f"Confidence {confidence['level']} ({confidence['score']:.0%}); confirm the mapping to analyze.",
    )

    event_file = event_profile.to_dict()
    metadata_dict = metadata_profile.to_dict() if metadata_profile else None
    mapping_fields = [
        {
            "field": field_name,
            "label_zh": label_zh,
            "label_en": label_en,
            "required": required,
            "value": (mapping.get("columns") or {}).get(field_name, ""),
        }
        for field_name, label_zh, label_en, required in MAPPING_FIELDS
    ]
    result = {
        "status": status,
        "native": False,
        "files": [profile.to_dict() for profile in profiles],
        "event_file": event_file,
        "metadata_file": metadata_dict,
        "mapping": mapping,
        "sample_ids": sorted(set(mapping.get("sample_columns", {}).values())),
        "mapping_fields": mapping_fields,
        "mapping_source": ("llm+heuristic" if llm_used else "heuristic"),
        "confidence": confidence,
        "preview": {**stats, "events": conversion.preview_rows()},
        "issues": issues,
        "agent_trace": trace,
        "llm": {
            "attempted": llm_attempted,
            "used": llm_used,
            "errors": llm_errors,
            "notes": llm_notes[:5],
        },
        "privacy": "只向模型发送列名与最多 3 行样例，不发送完整文件。",
        "privacy_en": "Only headers and up to 3 sample rows are sent to the model; the full file stays local.",
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
    }
    return result


def _standard_row(event: StandardEvent, sample_ids: Sequence[str]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "event_id": event.event_id,
        "gene_id": event.gene_id,
        "gene_symbol": event.gene_symbol,
        "event_type": event.event_type,
        "chromosome": event.chromosome,
        "strand": event.strand,
        "genomic_coordinates": event.genomic_coordinates,
        "coordinate_system": event.coordinate_system,
        "source_tool": event.source_tool,
        "mean_PSI_group1": event.mean_psi_group1,
        "mean_PSI_group2": event.mean_psi_group2,
        "delta_PSI": event.delta_psi,
        "p_value": event.p_value,
        "FDR": event.fdr,
        "inclusion_reads": event.inclusion_reads,
        "exclusion_reads": event.exclusion_reads,
        "total_support_reads": event.total_support_reads,
        "valid_sample_count": event.valid_sample_count,
        "psi_missing_rate": (
            None
            if not sample_ids
            else round(1 - len(event.psi_by_sample) / len(sample_ids), 4)
        ),
        "single_sample_driven": event.single_sample_driven,
        "mapping_ambiguity": event.mapping_ambiguity,
        "confidence_level": event.confidence_level,
    }
    for sample_id in sample_ids:
        row[f"{PSI_COLUMN_PREFIX}{sample_id}"] = event.psi_by_sample.get(sample_id, "")
    return row


def _write_standardized(
    output_dir: Path,
    conversion: Conversion,
    mapping: Mapping[str, Any],
    preview: Mapping[str, Any],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_ids = list(conversion.sample_columns.values())
    for sample in conversion.samples:
        if sample.sample_id not in sample_ids:
            sample_ids.append(sample.sample_id)
    fieldnames = (
        list(CORE_EVENT_FIELDS)
        + list(QUALITY_EVENT_FIELDS)
        + [f"{PSI_COLUMN_PREFIX}{sample_id}" for sample_id in sample_ids]
    )
    with (output_dir / "AS_event_master.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for event in conversion.events:
            writer.writerow(_standard_row(event, sample_ids))

    metadata_fields = ["sample_id", "group", "condition", "tissue", "batch"]
    extra_fields: list[str] = []
    for sample in conversion.samples:
        for key in sample.extra:
            if key not in extra_fields:
                extra_fields.append(key)
    with (output_dir / "sample_metadata.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=metadata_fields + extra_fields, extrasaction="ignore")
        writer.writeheader()
        for sample in conversion.samples:
            row = {
                "sample_id": sample.sample_id,
                "group": sample.group,
                "condition": sample.condition,
                "tissue": sample.tissue,
                "batch": sample.batch,
            }
            row.update({key: value for key, value in sample.extra.items() if key not in row})
            writer.writerow(row)

    serializable_mapping = {
        key: value for key, value in mapping.items() if not str(key).startswith("_")
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "SpliceGAIP ingestion agent",
        "mapping": serializable_mapping,
        "preview": {
            key: value
            for key, value in preview.items()
            if key not in {"events", "validation"}
        },
        "source_files": [mapping.get("event_file"), mapping.get("metadata_file")],
    }
    (output_dir / "ingestion_mapping.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_dir


def apply_ingestion(
    input_dir: str | Path,
    mapping: Mapping[str, Any],
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Convert using a confirmed mapping and write a standardized directory."""
    started = time.perf_counter()
    directory = Path(input_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"Input directory not found: {directory}")
    profiles = _profile_directory(directory)
    supported = [profile for profile in profiles if profile.supported and profile.headers]
    if not supported:
        raise ValueError("No parseable table was found; nothing to convert")

    heuristic, metadata_profile, candidate = _heuristic_mapping(supported)
    if candidate is None:
        raise ValueError("No event table could be identified")
    # Merge the user-confirmed mapping on top of the deterministic baseline.
    combined: dict[str, Any] = {
        **_sanitize_mapping(mapping, supported, heuristic, metadata_profile, allow_clear=True)[0]
    }
    combined["event_file"] = str(mapping.get("event_file") or heuristic.get("event_file") or candidate.profile.name)
    event_profile = next(
        (profile for profile in supported if profile.name == combined["event_file"]),
        candidate.profile,
    )
    combined["_profiles"] = supported
    issues: list[dict[str, str]] = []
    conversion = _convert(event_profile, combined, issues)
    combined.pop("_profiles", None)
    if not conversion.events:
        detail = "; ".join(issue["message"] for issue in issues if issue["severity"] == "error")
        raise ValueError(detail or "No usable events remained after standardization")
    validation = _validation_payload(conversion.events, conversion.samples)
    if not validation.get("ok", True):
        errors = "; ".join(
            str(issue.get("message") or "")
            for issue in validation.get("issues") or []
            if issue.get("severity") == "error"
        )
        raise ValueError(f"Ingested dataset failed validation: {errors}")
    if validation.get("issues"):
        issues.extend(_validation_issues(validation))
    preview = {
        "total_rows": conversion.total_rows,
        "valid_events": len(conversion.events),
        "dropped": conversion.dropped,
        "drop_reasons": dict(conversion.drop_reasons),
        "fdr_coverage": round(
            sum(1 for event in conversion.events if event.fdr is not None) / len(conversion.events), 3
        ),
        "delta_coverage": round(
            sum(1 for event in conversion.events if event.delta_psi is not None) / len(conversion.events), 3
        ),
        "event_types": dict(Counter(event.event_type or "UNKNOWN" for event in conversion.events)),
        "groups": dict(Counter(sample.group for sample in conversion.samples)),
        "sample_count": len(conversion.samples),
        "sample_psi_columns": len(conversion.sample_columns),
        "events": conversion.preview_rows(),
        "validation": validation,
    }
    target = Path(output_dir) if output_dir else directory / "standardized"
    _write_standardized(target, conversion, combined, preview)
    return {
        "path": str(target),
        "mapping": {key: value for key, value in combined.items() if not str(key).startswith("_")},
        "preview": preview,
        "issues": issues,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
    }


def apply_native_groups(input_dir: str | Path, sample_groups: Mapping[str, str]) -> dict[str, Any]:
    """Save a reviewed assignment for a recognized input in its upload directory."""
    directory = Path(input_dir)
    dataset = load_dataset(directory)
    sample_ids = {sample_id for event in dataset.events for sample_id in event.psi_by_sample}
    if not sample_ids:
        raise ValueError("No per-sample PSI values are available for group assignment")
    if set(sample_groups) != sample_ids:
        raise ValueError("Group assignment must include exactly the observed sample IDs")
    labels = {sample_id: str(sample_groups[sample_id]).strip() for sample_id in sample_ids}
    if any(not label or len(label) > 80 for label in labels.values()) or len(set(labels.values())) != 2:
        raise ValueError("Assign every sample to exactly one of two non-empty groups")
    target = directory / "sample_metadata.csv"
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample_id", "group", "condition"])
        for sample_id in sorted(sample_ids):
            writer.writerow([sample_id, labels[sample_id], labels[sample_id]])
    validation = validate_dataset(load_dataset(directory))
    if not validation.ok:
        target.unlink(missing_ok=True)
        raise ValueError("Group assignment produced an invalid dataset")
    return {"path": str(directory), "sample_count": len(sample_ids), "groups": dict(Counter(labels.values()))}
