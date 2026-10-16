"""Literature search skill for splicing analysis.

Searches scientific literature for:
- Gene-specific splicing studies
- Disease associations with alternative splicing
- Functional validation of splice variants
- Clinical trials targeting splicing

Sources: PubMed, Europe PMC, Semantic Scholar
"""

from __future__ import annotations

from typing import Any

import httpx

from splicegaip.skills.base import BaseSkill, SkillResult


class LiteratureSearchSkill(BaseSkill):
    """Search scientific literature for splicing-related evidence."""

    @property
    def name(self) -> str:
        return "literature_search"

    @property
    def description(self) -> str:
        return "搜索科学文献，查找基因剪接相关证据、疾病关联、功能验证和临床研究（支持PubMed/Europe PMC/Semantic Scholar）"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (gene name, disease, or keywords)",
                },
                "max_results": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum number of results to return",
                },
                "year_from": {
                    "type": "integer",
                    "description": "Start year filter (e.g., 2020)",
                },
                "year_to": {
                    "type": "integer",
                    "description": "End year filter (e.g., 2026)",
                },
                "include_abstracts": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include abstract text in results",
                },
                "sources": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["pubmed", "europe_pmc", "semantic_scholar"]},
                    "default": ["pubmed"],
                    "description": "Literature sources to search",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        query = kwargs.get("query")
        max_results = kwargs.get("max_results", 10)
        year_from = kwargs.get("year_from")
        year_to = kwargs.get("year_to")
        include_abstracts = kwargs.get("include_abstracts", True)
        sources = kwargs.get("sources", ["pubmed"])

        if not query:
            return SkillResult(
                skill_name=self.name,
                success=False,
                error="必须提供搜索查询词",
            )

        try:
            all_results = []

            # Search each requested source
            for source in sources:
                if source == "pubmed":
                    results = await self._search_pubmed(
                        query, max_results, year_from, year_to, include_abstracts
                    )
                    all_results.extend(results)
                elif source == "europe_pmc":
                    results = await self._search_europe_pmc(
                        query, max_results, year_from, year_to, include_abstracts
                    )
                    all_results.extend(results)
                elif source == "semantic_scholar":
                    results = await self._search_semantic_scholar(
                        query, max_results, year_from, year_to, include_abstracts
                    )
                    all_results.extend(results)

            # Sort by relevance (citation count, recency)
            all_results.sort(
                key=lambda x: (x.get("citation_count", 0), int(x.get("year", "0") or "0")),
                reverse=True,
            )

            # Limit to max_results
            limited_results = all_results[:max_results]

            if not limited_results:
                # Return success with empty results instead of error
                return SkillResult(
                    skill_name=self.name,
                    success=True,
                    data={
                        "query": query,
                        "results": [],
                        "total_found": 0,
                        "sources_searched": sources,
                        "note": "未找到相关文献，可能原因：1) 查询词过于具体 2) 网络问题 3) API限制",
                    },
                    metadata={
                        "filters": {
                            "year_from": year_from,
                            "year_to": year_to,
                            "include_abstracts": include_abstracts,
                        }
                    },
                )

            return SkillResult(
                skill_name=self.name,
                success=True,
                data={
                    "query": query,
                    "results": limited_results,
                    "total_found": len(all_results),
                    "sources_searched": sources,
                },
                metadata={
                    "filters": {
                        "year_from": year_from,
                        "year_to": year_to,
                        "include_abstracts": include_abstracts,
                    }
                },
            )

        except Exception as exc:  # noqa: BLE001
            return SkillResult(
                skill_name=self.name,
                success=False,
                error=f"文献搜索失败: {str(exc)}",
            )

    async def _search_pubmed(
        self,
        query: str,
        max_results: int,
        year_from: int | None,
        year_to: int | None,
        include_abstracts: bool,
    ) -> list[dict[str, Any]]:
        """Search PubMed via NCBI E-utilities."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Build date filter
                date_filter = ""
                if year_from and year_to:
                    date_filter = f"{year_from}/01/01:{year_to}/12/31[dp]"
                elif year_from:
                    date_filter = f"{year_from}/01/01:3000[dp]"

                full_query = f"({query}) AND (alternative splicing OR splice variant)"
                if date_filter:
                    full_query += f" AND {date_filter}"

                # Search for PMIDs
                search_response = await client.get(
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                    params={
                        "db": "pubmed",
                        "term": full_query,
                        "retmode": "json",
                        "retmax": max_results,
                        "sort": "relevance",
                    },
                )

                if search_response.status_code != 200:
                    return []

                search_data = search_response.json()
                pmids = search_data.get("esearchresult", {}).get("idlist", [])

                if not pmids:
                    return []

                # Fetch details for each PMID
                results = []
                fetch_response = await client.get(
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                    params={
                        "db": "pubmed",
                        "id": ",".join(pmids),
                        "retmode": "json",
                    },
                )

                if fetch_response.status_code == 200:
                    summary_data = fetch_response.json()
                    result_dict = summary_data.get("result", {})
                    
                    # NCBI returns a dict with PMIDs as keys, plus "uids" list
                    uids = result_dict.get("uids", [])
                    
                    for uid in uids:
                        item = result_dict.get(uid, {})
                        if isinstance(item, dict):
                            authors_list = item.get("authors", [])
                            results.append(
                                {
                                    "title": item.get("title"),
                                    "authors": ", ".join([a.get("name", "") for a in authors_list[:3]]),
                                    "journal": item.get("source"),
                                    "year": str(item.get("pubdate", ""))[:4],
                                    "pmid": uid,
                                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}",
                                    "citation_count": 0,
                                    "abstract": "",
                                    "source": "PubMed",
                                }
                            )

                # Fetch abstracts if requested
                if include_abstracts and results:
                    abstract_response = await client.get(
                        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                        params={
                            "db": "pubmed",
                            "id": ",".join(pmids),
                            "retmode": "xml",
                            "rettype": "abstract",
                        },
                    )
                    # Parse XML for abstracts (simplified - would need proper XML parsing)
                    # For now, leave abstracts empty

                return results

        except Exception:  # noqa: BLE001
            return []

    async def _search_europe_pmc(
        self,
        query: str,
        max_results: int,
        year_from: int | None,
        year_to: int | None,
        include_abstracts: bool,
    ) -> list[dict[str, Any]]:
        """Search Europe PMC API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {
                    "query": f'(TITLE:"{query}" OR ABSTRACT:"{query}") AND "alternative splicing"',
                    "resultType": "core",
                    "pageSize": max_results,
                    "format": "json",
                }

                if year_from and year_to:
                    params["firstPublicationDate"] = f"{year_from}-01-01"
                    params["lastPublicationDate"] = f"{year_to}-12-31"

                response = await client.get(
                    "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                    params=params,
                )

                if response.status_code != 200:
                    return []

                data = response.json()
                results = []
                for item in data.get("resultList", {}).get("results", []):
                    results.append(
                        {
                            "title": item.get("title"),
                            "authors": item.get("authorString"),
                            "journal": item.get("journalTitle"),
                            "year": str(item.get("publicationYear", "")),
                            "pmid": item.get("pmid"),
                            "pmcid": item.get("pmcid"),
                            "url": f"https://europepmc.org/article/{item.get('pmid')}",
                            "citation_count": item.get("citedByCount", 0),
                            "abstract": item.get("abstractText", "") if include_abstracts else "",
                            "source": "Europe PMC",
                        }
                    )

                return results

        except Exception:  # noqa: BLE001
            return []

    async def _search_semantic_scholar(
        self,
        query: str,
        max_results: int,
        year_from: int | None,
        year_to: int | None,
        include_abstracts: bool,
    ) -> list[dict[str, Any]]:
        """Search Semantic Scholar API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                params = {
                    "query": f"{query} alternative splicing",
                    "limit": max_results,
                    "fields": "title,authors,venue,year,citationCount,url,abstract",
                }

                response = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params=params,
                )

                if response.status_code != 200:
                    return []

                data = response.json()
                results = []
                for item in data.get("data", []):
                    year_val = item.get("year")
                    if year_from and year_val and year_val < year_from:
                        continue
                    if year_to and year_val and year_val > year_to:
                        continue

                    authors = item.get("authors", [])
                    results.append(
                        {
                            "title": item.get("title"),
                            "authors": ", ".join([a.get("name", "") for a in authors[:3]]),
                            "journal": item.get("venue"),
                            "year": str(year_val or ""),
                            "doi": item.get("externalIds", {}).get("DOI"),
                            "url": item.get("url"),
                            "citation_count": item.get("citationCount", 0),
                            "abstract": item.get("abstract", "") if include_abstracts else "",
                            "source": "Semantic Scholar",
                        }
                    )

                return results

        except Exception:  # noqa: BLE001
            return []
