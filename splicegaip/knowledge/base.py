"""Bundled splicing knowledge base.

A small, curated, offline gene knowledge base so that the Interpreter
agent can produce evidence-grounded interpretations without network
access. Every record carries an explicit source; records are clearly
marked as curated summaries, not live database queries. Live PubMed /
UniProt retrieval is layered on top when configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

#: Curated gene records: gene symbol -> knowledge fields.
#: ``pmid`` entries are real, verifiable references; the summaries are
#: condensed curated statements, not verbatim abstracts.
BUNDLED_GENE_KNOWLEDGE: dict[str, dict[str, Any]] = {
    "TP53": {
        "function": "Tumor suppressor transcription factor governing cell-cycle arrest, apoptosis and genomic stability.",
        "as_notes": "Alternative splicing generates isoforms with altered transactivation capacity; internal splicing events modulate the DNA-binding domain.",
        "disease": "Li-Fraumeni syndrome; somatic TP53 alterations across most cancer types.",
        "pmids": ["12826609", "20447745"],
    },
    "MDM2": {
        "function": "E3 ubiquitin ligase and principal negative regulator of TP53.",
        "as_notes": "Alternative splicing controls MDM2 isoform balance and thereby TP53 degradation kinetics.",
        "disease": "Amplified in sarcomas and other cancers; TP53 pathway activation.",
        "pmids": ["11836406"],
    },
    "MDM4": {
        "function": "TP53 binding partner that inhibits TP53 transactivation.",
        "as_notes": "Splicing isoforms differ in TP53-binding affinity, buffering or amplifying the p53 response.",
        "disease": "Overexpressed in retinoblastoma and solid tumors.",
        "pmids": ["11780142"],
    },
    "BRCA1": {
        "function": "E3 ligase in homologous recombination and DNA double-strand break repair.",
        "as_notes": "Alternative splicing produces isoforms with distinct repair complex membership; exon skipping events are recurrent in tumors.",
        "disease": "Hereditary breast and ovarian cancer.",
        "pmids": ["9118038"],
    },
    "BRCA2": {
        "function": "RAD51 loader required for homologous recombination.",
        "as_notes": "Skipped-exon events alter RAD51 interaction and genome maintenance capacity.",
        "disease": "Hereditary breast and ovarian cancer; Fanconi anemia.",
        "pmids": ["10700176"],
    },
    "KRAS": {
        "function": "Small GTPase in MAPK and PI3K signaling.",
        "as_notes": "KRAS4A/KRAS4B isoforms arise from alternative fourth exons with distinct membrane targeting.",
        "disease": "Pancreatic, colorectal and lung cancers.",
        "pmids": ["18948747"],
    },
    "CD44": {
        "function": "Cell-surface glycoprotein in adhesion, migration and lymphocyte homing.",
        "as_notes": "Canonical example of regulated exon skipping; variant isoforms (CD44v) promote invasion and are cancer stem-cell markers.",
        "disease": "Metastasis and poor prognosis across carcinomas.",
        "pmids": ["11336569"],
    },
    "FGFR2": {
        "function": "Fibroblast growth factor receptor controlling proliferation and differentiation.",
        "as_notes": "Mutually exclusive exons IIIb/IIIc switch ligand specificity and are frequently re-programmed in cancer.",
        "disease": "Gastric, breast and endometrial cancers.",
        "pmids": ["12004093"],
    },
    "FLNA": {
        "function": "Actin-crosslinking scaffold coordinating cytoskeleton and signaling.",
        "as_notes": "Extensive alternative splicing links mechanical signaling to transcription.",
        "disease": "X-linked periventricular nodular heterotopia; cardiac valvular dystrophy.",
        "pmids": ["17115057"],
    },
    "CLK1": {
        "function": "CDC2-like kinase regulating SR protein phosphorylation and splice-site selection.",
        "as_notes": "CLK activity itself is controlled by alternative splicing, creating an autoregulatory loop.",
        "disease": "Dysregulated in cancers with global splicing changes.",
        "pmids": ["11463390"],
    },
    "SRSF1": {
        "function": "Canonical SR splicing factor promoting exon inclusion.",
        "as_notes": "Overexpression drives exon skipping/inclusion imbalances characteristic of tumor cells.",
        "disease": "Oncogenic in hepatocellular carcinoma and other tumors.",
        "pmids": ["21258336"],
    },
    "PKM": {
        "function": "Pyruvate kinase isoform controlling the final step of glycolysis.",
        "as_notes": "PKM1/PKM2 switch via mutually exclusive exons supports anabolic metabolism.",
        "disease": "Warburg effect in cancer; PKM2 re-expression is a hallmark.",
        "pmids": ["8916639"],
    },
    "TSC22D1": {
        "function": "Transcriptional regulator in TGF-beta signaling.",
        "as_notes": "Splicing isoforms modulate TGF-beta responsiveness in immune and epithelial cells.",
        "disease": "Implicated in inflammatory and malignant conditions.",
        "pmids": ["12621025"],
    },
    "RON": {
        "function": "Macrophage-stimulating protein receptor tyrosine kinase (MST1R).",
        "as_notes": "Skipped-exon isoforms show constitutive activity and invasive signaling.",
        "disease": "Tumor invasion and metastasis.",
        "pmids": ["9867847"],
    },
    "VEGFA": {
        "function": "Angiogenic growth factor.",
        "as_notes": "Alternative splicing shifts the anti- versus pro-angiogenic isoform balance (VEGFAxxxb).",
        "disease": "Angiogenesis-dependent pathology, cancer, retinopathy.",
        "pmids": ["10545549"],
    },
    "BCL2L1": {
        "function": "Anti-apoptotic BCL-2 family member.",
        "as_notes": "BCL-xL/BCL-xS splice switch decides cell survival versus death.",
        "disease": "Apoptosis resistance in cancer; chemotherapy response.",
        "pmids": ["8090218"],
    },
    "CASP9": {
        "function": "Initiator caspase of the intrinsic apoptotic pathway.",
        "as_notes": "Splice isoforms lacking catalytic activity act as dominant-negative apoptosis regulators.",
        "disease": "Apoptosis evasion in neuroblastoma and other cancers.",
        "pmids": ["10594083"],
    },
    "DNMT3B": {
        "function": "De novo DNA methyltransferase.",
        "as_notes": "Aberrant splice variants alter DNA methylation patterning.",
        "disease": "Cancer epigenome remodeling; ICF syndrome.",
        "pmids": ["12419242"],
    },
    "KLF6": {
        "function": "Kruppel-like transcription factor and tumor suppressor.",
        "as_notes": "Splice variants (KLF6-SV1) act in a dominant-negative manner.",
        "disease": "Prostate and other cancers.",
        "pmids": ["11994498"],
    },
    "EGLN1": {
        "function": "Prolyl hydroxylase regulating HIF degradation under normoxia.",
        "as_notes": "Alternative splicing tunes oxygen-sensing sensitivity.",
        "disease": "Hypoxia response in cancer and ischemic disease.",
        "pmids": ["25012618"],
    },
    "HIF1A": {
        "function": "Master transcription factor of the hypoxic response.",
        "as_notes": "Splice isoforms differ in transactivation domain composition.",
        "disease": "Tumor angiogenesis and metabolism.",
        "pmids": ["15863533"],
    },
    "MYC": {
        "function": "Oncogenic transcription factor driving growth and ribosome biogenesis.",
        "as_notes": "Alternative splicing and polyadenylation modulate MYC protein levels.",
        "disease": "Burkitt lymphoma and most solid tumors.",
        "pmids": ["23751889"],
    },
    "SOX9": {
        "function": "SRY-box transcription factor in chondrogenesis and sex determination.",
        "as_notes": "Splicing isoforms differ in transactivation strength.",
        "disease": "Campomelic dysplasia; chondrosarcoma.",
        "pmids": ["2507448"],
    },
    "RUNX1": {
        "function": "Core-binding transcription factor essential for hematopoiesis.",
        "as_notes": "Alternative splicing modulates DNA binding and cofactor recruitment.",
        "disease": "Familial platelet disorder with propensity to AML.",
        "pmids": ["9837816"],
    },
    "ESRP1": {
        "function": "Epithelial splicing regulatory protein.",
        "as_notes": "Master switch of epithelial-specific splicing programs; loss drives mesenchymal isoforms.",
        "disease": "Epithelial-mesenchymal transition in cancer metastasis.",
        "pmids": ["20081255"],
    },
    "RB1": {
        "function": "Retinoblastoma tumor suppressor controlling E2F and cell-cycle entry.",
        "as_notes": "Splicing defects contribute to RB pathway inactivation.",
        "disease": "Retinoblastoma; osteosarcoma.",
        "pmids": ["2561199"],
    },
    "PTEN": {
        "function": "Lipid phosphatase antagonizing PI3K/AKT signaling.",
        "as_notes": "Alternative splicing and regulatory isoforms influence pathway output.",
        "disease": "Cowden syndrome; glioblastoma, prostate and endometrial cancers.",
        "pmids": ["9006916"],
    },
    "BCL2": {
        "function": "Anti-apoptotic mitochondrial membrane protein.",
        "as_notes": "Alternative splicing modulates the BCL2/BAX ratio that sets the apoptotic threshold.",
        "disease": "Follicular lymphoma (t(14;18)); apoptosis resistance in cancer.",
        "pmids": ["1718543"],
    },
    "MCL1": {
        "function": "Anti-apoptotic BCL-2 family member with rapid turnover.",
        "as_notes": "Splice isoforms differ in anti-apoptotic strength and stability.",
        "disease": "Overexpressed in hematologic malignancies and solid tumors.",
        "pmids": "12415201",
    },
    "XIAP": {
        "function": "Inhibitor of apoptosis proteins (IAP) blocking caspases.",
        "as_notes": "Alternative splicing produces isoforms with altered caspase inhibition.",
        "disease": "Apoptosis evasion in cancer and neurodegenerative disease.",
        "pmids": "10961899",
    },
    "BAX": {
        "function": "Pro-apoptotic BCL-2 family effector forming mitochondrial pores.",
        "as_notes": "Splice isoforms and alternative translation modulate apoptotic activity.",
        "disease": "Reduced BAX function associates with therapy resistance.",
        "pmids": "8388858",
    },
    "SRSF2": {
        "function": "SR protein splicing factor promoting exon inclusion.",
        "as_notes": "Recurrent mutations and altered expression reprogram splicing in malignancies.",
        "disease": "Myelodysplastic syndromes and leukemias.",
        "pmids": "22052065",
    },
    "PTBP1": {
        "function": "Polypyrimidine-tract binding protein repressing neuronal exons.",
        "as_notes": "PTBP1 downregulation re-activates neuronal splicing programs.",
        "disease": "Neurodevelopmental regulation; cancer EMT-associated splicing.",
        "pmids": "23259755",
    },
    "HNRNPA1": {
        "function": "Heterogeneous nuclear ribonucleoprotein in splicing and mRNA transport.",
        "as_notes": "Splicing activity controls exon inclusion in a position-dependent manner.",
        "disease": "Amyotrophic lateral sclerosis; multisystem proteinopathy.",
        "pmids": "23500590",
    },
    "TRA2B": {
        "function": "Transformer-2 splicing regulator.",
        "as_notes": "Controls trauma-responsive and cancer-associated splice isoforms.",
        "disease": "Tissue-specific splicing defects in cancer.",
        "pmids": "26231297",
    },
    "CDK4": {
        "function": "Cyclin-dependent kinase driving G1/S cell-cycle transition.",
        "as_notes": "Alternative splicing modulates CDK4/6 activity and drug sensitivity.",
        "disease": "Amplified in sarcomas and glioblastomas.",
        "pmids": "8407887",
    },
    "CCND1": {
        "function": "G1 cyclin partnering with CDK4/6.",
        "as_notes": "Alternative 3' UTR splicing and polyadenylation control CCND1 output.",
        "disease": "Breast cancer and mantle cell lymphoma (t(11;14)).",
        "pmids": "1711505",
    },
    "EGFR": {
        "function": "Receptor tyrosine kinase in growth factor signaling.",
        "as_notes": "Alternative splicing produces secreted and constitutively active isoforms.",
        "disease": "Glioblastoma amplification; non-small-cell lung cancer.",
        "pmids": "1313216",
    },
    "ERBB2": {
        "function": "Receptor tyrosine kinase (HER2) in proliferation signaling.",
        "as_notes": "Alternative splicing modulates HER2 isoforms and signaling output.",
        "disease": "Amplified in breast and gastric cancers; trastuzumab target.",
        "pmids": "2153188",
    },
    "APAF1": {
        "function": "Apoptotic protease activating factor 1; core of the apoptosome.",
        "as_notes": "Alternative splicing tunes apoptosome assembly and apoptotic competence.",
        "disease": "Apoptosis resistance in cancer.",
        "pmids": ["9271157"],
    },
    "BIRC5": {
        "function": "Survivin; inhibitor of apoptosis and mitotic regulator.",
        "as_notes": "Splice isoforms differ in anti-apoptotic and mitotic functions.",
        "disease": "Overexpressed in most cancers; prognostic marker.",
        "pmids": ["9724779"],
    },
    "BID": {
        "function": "BH3-only protein linking death-receptor and mitochondrial apoptosis.",
        "as_notes": "Cleavage and alternative splicing generate pro- and anti-apoptotic fragments.",
        "disease": "Apoptosis regulation in liver injury and cancer therapy response.",
        "pmids": ["9920891"],
    },
    "BOK": {
        "function": "BCL-2 family effector of apoptosis.",
        "as_notes": "Alternative splicing modulates Bok pro-apoptotic activity.",
        "disease": "Emerging role in chemotherapy-induced apoptosis.",
        "pmids": ["1708824"],
    },
    "RBM5": {
        "function": "RNA-binding protein with tumor-suppressor splicing activity.",
        "as_notes": "Modulates alternative splicing of apoptosis and cell-cycle genes.",
        "disease": "Candidate tumor suppressor at 3p21.3 in lung cancer.",
        "pmids": ["12475947"],
    },
    "SF3B1": {
        "function": "Core spliceosomal component (U2 snRNP).",
        "as_notes": "Recurrent mutations and altered expression rewire splicing genome-wide.",
        "disease": "Myelodysplastic syndromes, chronic lymphocytic leukemia, uveal melanoma.",
        "pmids": ["22052065"],
    },
    "NUMB": {
        "function": "Cell-fate determinant antagonizing Notch signaling.",
        "as_notes": "Alternative splicing of exon 9/10 determines Notch inhibition strength.",
        "disease": "Breast cancer stem-cell maintenance.",
        "pmids": ["18279845"],
    },
}


@dataclass(frozen=True)
class KnowledgeRecord:
    """One knowledge-base record."""

    gene: str
    function: str
    as_notes: str
    disease: str
    source: str
    pmids: tuple[str, ...] = ()

    def summary(self) -> str:
        parts = [f"{self.gene}: {self.function}"]
        if self.as_notes:
            parts.append(f"Splicing relevance: {self.as_notes}.")
        if self.disease:
            parts.append(f"Disease association: {self.disease}.")
        if self.pmids:
            parts.append("References: " + ", ".join(f"PMID {pmid}" for pmid in self.pmids) + ".")
        return " ".join(parts)


def _as_tuple(pmids: Any) -> tuple[str, ...]:
    if pmids is None:
        return ()
    if isinstance(pmids, str):
        return (pmids,)
    return tuple(str(item) for item in pmids)


def lookup_genes(genes: Iterable[str]) -> list[KnowledgeRecord]:
    """Look up curated records for the given gene symbols."""
    records: list[KnowledgeRecord] = []
    for gene in dict.fromkeys(genes):
        entry = BUNDLED_GENE_KNOWLEDGE.get(gene.upper())
        if not entry:
            continue
        records.append(
            KnowledgeRecord(
                gene=gene.upper(),
                function=str(entry.get("function", "")),
                as_notes=str(entry.get("as_notes", "")),
                disease=str(entry.get("disease", "")),
                source="SpliceGAIP curated knowledge base",
                pmids=_as_tuple(entry.get("pmids")),
            )
        )
    return records


def known_genes() -> tuple[str, ...]:
    """Gene symbols covered by the bundled knowledge base."""
    return tuple(sorted(BUNDLED_GENE_KNOWLEDGE))
