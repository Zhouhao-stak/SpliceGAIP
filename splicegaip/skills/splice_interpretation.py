"""Splice event interpretation skill.

Provides clinical and functional interpretation of alternative splicing events:
- Splice site strength prediction (MaxEntScan)
- Pathogenicity assessment (SpliceAI scores)
- Protein domain impact analysis
- Disease mechanism hypotheses
- Therapeutic targeting opportunities (antisense oligonucleotides, small molecules)

Integrates computational predictions with clinical databases.
"""

from __future__ import annotations

from typing import Any

import httpx

from splicegaip.skills.base import BaseSkill, SkillResult


class SpliceInterpretationSkill(BaseSkill):
    """Interpret the biological and clinical significance of splicing events."""

    @property
    def name(self) -> str:
        return "splice_interpretation"

    @property
    def description(self) -> str:
        return "解读可变剪接事件的生物学和临床意义，包括剪接位点强度预测、致病性评估、蛋白结构域影响和治疗靶点分析"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol (e.g., BRCA1)",
                },
                "event_type": {
                    "type": "string",
                    "enum": ["SE", "MXE", "A5SS", "A3SS", "RI"],
                    "description": "Alternative splicing event type",
                },
                "chromosome": {
                    "type": "string",
                    "description": "Chromosome (e.g., chr17)",
                },
                "start": {
                    "type": "integer",
                    "description": "Genomic start position (GRCh38)",
                },
                "end": {
                    "type": "integer",
                    "description": "Genomic end position (GRCh38)",
                },
                "strand": {
                    "type": "string",
                    "enum": ["+", "-"],
                    "description": "DNA strand orientation",
                },
                "delta_psi": {
                    "type": "number",
                    "description": "Change in percent spliced in (PSI)",
                },
                "fdr": {
                    "type": "number",
                    "description": "False discovery rate",
                },
                "include_therapeutics": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include therapeutic targeting information",
                },
            },
            "required": ["gene_symbol", "event_type"],
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        gene_symbol = kwargs.get("gene_symbol")
        event_type = kwargs.get("event_type")
        chromosome = kwargs.get("chromosome")
        start = kwargs.get("start")
        end = kwargs.get("end")
        strand = kwargs.get("strand")
        delta_psi = kwargs.get("delta_psi")
        fdr = kwargs.get("fdr")
        include_therapeutics = kwargs.get("include_therapeutics", True)

        if not gene_symbol or not event_type:
            return SkillResult(
                skill_name=self.name,
                success=False,
                error="必须提供基因符号和事件类型",
            )

        try:
            interpretation = {}

            # 1. Predict splice site strength
            if chromosome and start and end:
                splice_strength = await self._predict_splice_strength(
                    chromosome, start, end, strand
                )
                if splice_strength:
                    interpretation["splice_site_prediction"] = splice_strength

            # 2. Get SpliceAI pathogenicity scores
            spliceai_scores = await self._get_spliceai_scores(
                gene_symbol, chromosome, start, end
            )
            if spliceai_scores:
                interpretation["pathogenicity"] = spliceai_scores

            # 3. Analyze protein domain impact
            if delta_psi is not None:
                protein_impact = await self._analyze_protein_impact(
                    gene_symbol, event_type, delta_psi
                )
                if protein_impact:
                    interpretation["protein_impact"] = protein_impact

            # 4. Check clinical databases
            clinical_info = await self._query_clinical_databases(gene_symbol, event_type)
            if clinical_info:
                interpretation["clinical_significance"] = clinical_info

            # 5. Therapeutic opportunities
            if include_therapeutics:
                therapeutics = await self._find_therapeutic_opportunities(
                    gene_symbol, event_type
                )
                if therapeutics:
                    interpretation["therapeutic_opportunities"] = therapeutics

            # 6. Generate summary interpretation
            summary = self._generate_summary(
                gene_symbol, event_type, delta_psi, fdr, interpretation
            )
            interpretation["summary"] = summary

            if not interpretation:
                return SkillResult(
                    skill_name=self.name,
                    success=False,
                    error=f"无法解读 {gene_symbol} 的 {event_type} 事件",
                )

            return SkillResult(
                skill_name=self.name,
                success=True,
                data={
                    "gene": gene_symbol,
                    "event_type": event_type,
                    "interpretation": interpretation,
                },
                metadata={
                    "delta_psi": delta_psi,
                    "fdr": fdr,
                    "genomic_location": (
                        f"{chromosome}:{start}-{end}" if chromosome and start else None
                    ),
                },
            )

        except Exception as exc:  # noqa: BLE001
            return SkillResult(
                skill_name=self.name,
                success=False,
                error=f"剪接事件解读失败: {str(exc)}",
            )

    async def _predict_splice_strength(
        self,
        chromosome: str,
        start: int,
        end: int,
        strand: str | None,
    ) -> dict[str, Any] | None:
        """Predict splice site strength using MaxEntScan or similar."""
        # This would integrate with MaxEntScan or SpliceSiteFinder
        # For now, return a placeholder indicating the integration point
        return {
            "method": "MaxEntScan (placeholder)",
            "note": "需要集成 MaxEntScan 或类似工具进行剪接位点强度预测",
            "location": f"{chromosome}:{start}-{end}",
            "strand": strand,
        }

    async def _get_spliceai_scores(
        self,
        gene_symbol: str,
        chromosome: str | None,
        start: int | None,
        end: int | None,
    ) -> dict[str, Any] | None:
        """Get SpliceAI delta score for variant/splice event."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # SpliceAI lookup via Ensembl VEP or direct API
                # For demonstration, query a mock endpoint
                if not (chromosome and start and end):
                    return None

                # In production, this would call:
                # https://spliceailookup.ucsc.edu/ or Ensembl VEP
                return {
                    "source": "SpliceAI (lookup pending)",
                    "ds_max": None,
                    "dp_acceptor_gain": None,
                    "dp_acceptor_loss": None,
                    "dp_donor_gain": None,
                    "dp_donor_loss": None,
                    "note": f"需要查询 {gene_symbol} ({chromosome}:{start}-{end}) 的 SpliceAI 分数",
                }

        except Exception:  # noqa: BLE001
            return None

    async def _analyze_protein_impact(
        self,
        gene_symbol: str,
        event_type: str,
        delta_psi: float,
    ) -> dict[str, Any] | None:
        """Analyze impact on protein domains and function."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Fetch protein domains from UniProt
                response = await client.get(
                    f"https://rest.uniprot.org/uniprotkb/search?query=gene:{gene_symbol}&format=json&fields=domains"
                )

                if response.status_code != 200:
                    return None

                data = response.json()
                results = data.get("results", [])

                if not results:
                    return None

                domains = results[0].get("domains", [])
                impact_assessment = {
                    "event_type": event_type,
                    "delta_psi": delta_psi,
                    "affected_domains": [],
                    "functional_consequence": None,
                }

                # Determine likely impact based on event type
                if event_type == "SE":  # Skipped exon
                    impact_assessment["functional_consequence"] = (
                        "外显子跳跃可能导致蛋白结构域缺失或移码突变"
                        if abs(delta_psi) > 0.2
                        else "外显子跳跃程度较轻，可能影响有限"
                    )
                elif event_type == "RI":  # Retained intron
                    impact_assessment["functional_consequence"] = (
                        "内含子保留通常引入提前终止密码子，导致无义介导的mRNA降解"
                    )
                elif event_type in ("A5SS", "A3SS"):
                    impact_assessment["functional_consequence"] = (
                        "剪接位点改变可能导致蛋白C端或N端截短"
                    )

                # Map domains to potential impact
                for domain in domains[:5]:  # Top 5 domains
                    impact_assessment["affected_domains"].append(
                        {
                            "name": domain.get("name"),
                            "start": domain.get("start"),
                            "end": domain.get("end"),
                            "description": domain.get("description"),
                        }
                    )

                return impact_assessment

        except Exception:  # noqa: BLE001
            return None

    async def _query_clinical_databases(
        self, gene_symbol: str, event_type: str
    ) -> dict[str, Any] | None:
        """Query ClinVar, OMIM, and other clinical databases."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                clinical_data = {"clinvar": [], "omim": [], "cosmic": []}

                # Query ClinVar
                clinvar_response = await client.get(
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                    params={
                        "db": "clinvar",
                        "term": f"{gene_symbol}[gene] AND splicing",
                        "retmode": "json",
                        "retmax": 5,
                    },
                )

                if clinvar_response.status_code == 200:
                    clinvar_data_raw = clinvar_response.json()
                    ids = clinvar_data_raw.get("esearchresult", {}).get("idlist", [])
                    clinical_data["clinvar"] = [
                        {"clinvar_id": cid, "gene": gene_symbol} for cid in ids[:3]
                    ]

                # Query OMIM
                omim_response = await client.get(
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                    params={
                        "db": "omim",
                        "term": gene_symbol,
                        "retmode": "json",
                        "retmax": 3,
                    },
                )

                if omim_response.status_code == 200:
                    omim_data_raw = omim_response.json()
                    ids = omim_data_raw.get("esearchresult", {}).get("idlist", [])
                    clinical_data["omim"] = [
                        {"omim_id": oid, "gene": gene_symbol} for oid in ids[:3]
                    ]

                # Filter out empty results
                return {k: v for k, v in clinical_data.items() if v}

        except Exception:  # noqa: BLE001
            return None

    async def _find_therapeutic_opportunities(
        self, gene_symbol: str, event_type: str
    ) -> dict[str, Any] | None:
        """Find therapeutic targeting opportunities."""
        # This would integrate with drug databases and ASO design tools
        therapeutic_info = {
            "targeting_strategies": [],
            "existing_drugs": [],
            "clinical_trials": [],
        }

        # General strategies based on event type
        if event_type == "SE":
            therapeutic_info["targeting_strategies"].append(
                {
                    "strategy": "反义寡核苷酸 (ASO)",
                    "mechanism": "阻断剪接沉默子或增强剪接增强子结合",
                    "example": "Nusinersen (Spinraza) for SMN2 exon 7 inclusion",
                }
            )
        elif event_type == "RI":
            therapeutic_info["targeting_strategies"].append(
                {
                    "strategy": "小分子剪接调节剂",
                    "mechanism": "调节剪接因子活性以促进内含子去除",
                    "example": "Risdiplam for SMN2 splicing modulation",
                }
            )

        # Check ClinicalTrials.gov for ongoing trials
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                trials_response = await client.get(
                    "https://clinicaltrials.gov/api/v2/studies",
                    params={
                        "query.term": f"{gene_symbol} AND splicing",
                        "pageSize": 3,
                    },
                )

                if trials_response.status_code == 200:
                    trials_data = trials_response.json()
                    studies = trials_data.get("studies", [])
                    therapeutic_info["clinical_trials"] = [
                        {
                            "nct_id": study.get("protocolSection", {}).get(
                                "identificationModule", {}
                            ).get("nctId"),
                            "title": study.get("protocolSection", {})
                            .get("identificationModule", {})
                            .get("briefTitle"),
                            "status": study.get("protocolSection", {})
                            .get("statusModule", {})
                            .get("overallStatus"),
                        }
                        for study in studies[:3]
                    ]
        except Exception:  # noqa: BLE001
            pass

        return therapeutic_info if any(therapeutic_info.values()) else None

    def _generate_summary(
        self,
        gene_symbol: str,
        event_type: str,
        delta_psi: float | None,
        fdr: float | None,
        interpretation: dict[str, Any],
    ) -> str:
        """Generate a human-readable summary interpretation."""
        parts = [f"基因 {gene_symbol} 发生 {event_type} 型可变剪接事件。"]

        if delta_psi is not None:
            direction = "增加" if delta_psi > 0 else "减少"
            parts.append(f"剪接变化幅度为 {abs(delta_psi):.1%}（PSI {direction}）。")

        if fdr is not None and fdr < 0.05:
            parts.append(f"该变化具有统计学显著性（FDR = {fdr:.2e}）。")

        if "pathogenicity" in interpretation:
            parts.append("SpliceAI 致病性评分待查询。")

        if "protein_impact" in interpretation:
            consequence = interpretation["protein_impact"].get("functional_consequence")
            if consequence:
                parts.append(f"功能影响：{consequence}")

        if "therapeutic_opportunities" in interpretation:
            strategies = interpretation["therapeutic_opportunities"].get(
                "targeting_strategies", []
            )
            if strategies:
                parts.append(
                    f"潜在治疗策略：{strategies[0].get('strategy', '未知')}"
                )

        return "".join(parts)
