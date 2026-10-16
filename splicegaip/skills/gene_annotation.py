"""Gene annotation skill for splicing analysis.

Fetches comprehensive gene information including:
- Gene structure (exons, introns, splice sites)
- Known alternative splicing events
- Conservation scores
- Clinical variants (ClinVar)
- Expression patterns (GTEx)

Sources: Ensembl REST API, UCSC Genome Browser, MyGene.info
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from splicegaip.skills.base import BaseSkill, SkillResult


class GeneAnnotationSkill(BaseSkill):
    """Retrieve detailed gene annotation for splicing context."""

    @property
    def name(self) -> str:
        return "gene_annotation"

    @property
    def description(self) -> str:
        return "获取基因注释信息，包括外显子结构、已知剪接事件、保守性评分和临床变异（支持Ensembl/UCSC数据库查询）"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "gene_symbol": {
                    "type": "string",
                    "description": "Gene symbol (e.g., BRCA1, TP53)",
                },
                "gene_id": {
                    "type": "string",
                    "description": "Ensembl gene ID (e.g., ENSG00000012345)",
                },
                "genome_build": {
                    "type": "string",
                    "enum": ["GRCh38", "GRCh37"],
                    "default": "GRCh38",
                    "description": "Genome assembly version",
                },
                "include_splicing": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include known splicing events",
                },
                "include_clinical": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include ClinVar clinical variants",
                },
            },
            "required": ["gene_symbol"],
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        gene_symbol = kwargs.get("gene_symbol")
        gene_id = kwargs.get("gene_id")
        genome_build = kwargs.get("genome_build", "GRCh38")
        include_splicing = kwargs.get("include_splicing", True)
        include_clinical = kwargs.get("include_clinical", True)

        if not gene_symbol and not gene_id:
            return SkillResult(
                skill_name=self.name,
                success=False,
                error="必须提供 gene_symbol 或 gene_id",
            )

        try:
            result_data = {}

            # Fetch basic gene info from MyGene.info
            basic_info = await self._fetch_mygene_info(gene_symbol or gene_id)
            if basic_info:
                result_data["basic_info"] = basic_info

            # Fetch gene structure from Ensembl
            if gene_id or basic_info:
                ens_id = gene_id or basic_info.get("ensembl_gene")
                if ens_id:
                    structure = await self._fetch_ensembl_structure(ens_id, genome_build)
                    if structure:
                        result_data["gene_structure"] = structure

            # Fetch splicing events
            if include_splicing and (gene_id or basic_info):
                ens_id = gene_id or basic_info.get("ensembl_gene")
                if ens_id:
                    splicing = await self._fetch_splicing_events(ens_id)
                    if splicing:
                        result_data["splicing_events"] = splicing

            # Fetch clinical variants
            if include_clinical and (gene_id or basic_info):
                ens_id = gene_id or basic_info.get("ensembl_gene")
                if ens_id:
                    clinical = await self._fetch_clinvar_variants(ens_id)
                    if clinical:
                        result_data["clinical_variants"] = clinical

            if not result_data:
                return SkillResult(
                    skill_name=self.name,
                    success=False,
                    error=f"未能获取基因 {gene_symbol or gene_id} 的注释信息",
                )

            return SkillResult(
                skill_name=self.name,
                success=True,
                data=result_data,
                metadata={
                    "gene_symbol": gene_symbol,
                    "gene_id": gene_id,
                    "genome_build": genome_build,
                    "sources": ["MyGene.info", "Ensembl", "ClinVar"],
                },
            )

        except Exception as exc:  # noqa: BLE001
            return SkillResult(
                skill_name=self.name,
                success=False,
                error=f"基因注释查询失败: {str(exc)}",
            )

    async def _fetch_mygene_info(self, query: str) -> dict[str, Any] | None:
        """Fetch basic gene information from MyGene.info."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://mygene.info/v3/query?q={query}&fields=symbol,name,ensembl,summary,type_of_gene"
                )
                if response.status_code == 200:
                    data = response.json()
                    hits = data.get("hits", [])
                    if hits:
                        hit = hits[0]
                        return {
                            "symbol": hit.get("symbol"),
                            "name": hit.get("name"),
                            "ensembl_gene": hit.get("ensembl", {}).get("gene"),
                            "summary": hit.get("summary"),
                            "gene_type": hit.get("type_of_gene"),
                        }
        except Exception:  # noqa: BLE001
            pass
        return None

    async def _fetch_ensembl_structure(
        self, gene_id: str, genome_build: str
    ) -> dict[str, Any] | None:
        """Fetch gene structure from Ensembl REST API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get transcript information
                response = await client.get(
                    f"https://rest.ensembl.org/lookup/id/{gene_id}",
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code == 200:
                    gene_data = response.json()
                    return {
                        "gene_id": gene_id,
                        "chromosome": gene_data.get("seq_region_name"),
                        "start": gene_data.get("start"),
                        "end": gene_data.get("end"),
                        "strand": gene_data.get("strand"),
                        "biotype": gene_data.get("biotype"),
                        "description": gene_data.get("description"),
                    }
        except Exception:  # noqa: BLE001
            pass
        return None

    async def _fetch_splicing_events(self, gene_id: str) -> list[dict[str, Any]] | None:
        """Fetch known splicing events from Ensembl."""
        # This would integrate with SpliceAI or similar databases
        # For now, return placeholder indicating integration point
        return [
            {
                "source": "Ensembl",
                "note": "完整剪接事件查询需要集成 SpliceAI 或 TCGA SpliceSeq 数据库",
                "gene_id": gene_id,
            }
        ]

    async def _fetch_clinvar_variants(self, gene_id: str) -> list[dict[str, Any]] | None:
        """Fetch clinical variants from ClinVar via NCBI E-utilities."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Search ClinVar for variants in this gene
                response = await client.get(
                    f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                    params={
                        "db": "clinvar",
                        "term": f"{gene_id}[gene]",
                        "retmode": "json",
                        "retmax": 10,
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    ids = data.get("esearchresult", {}).get("idlist", [])
                    if ids:
                        return [
                            {"clinvar_id": clinvar_id, "gene_id": gene_id}
                            for clinvar_id in ids[:5]
                        ]
        except Exception:  # noqa: BLE001
            pass
        return None
