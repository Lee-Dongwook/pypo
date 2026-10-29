from __future__ import annotations

from dataclasses import dataclass

import httpx

from src.app.shared.settings import settings


@dataclass
class Triple:
    s: str
    p: str
    o: str
    o_type: str  # "uri" | "literal"
    o_lang: str | None = None
    o_datatype: str | None = None


class GraphDBClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.triplestore_url

    async def fetch_triples(self, graph_iri: str, limit: int = 10_000) -> list[Triple]:
        sparql = f"""
        SELECT ?s ?p ?o WHERE {{
            GRAPH <{graph_iri}> {{
                ?s ?p ?o .
            }}
        }} LIMIT {limit}
        """

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}{settings.triplestore_query_endpoint}",
                content=sparql,
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/sparql-query",
                },
            )
            response.raise_for_status()
            data = response.json()

        triples: list[Triple] = []
        for binding in data.get("results", {}).get("bindings", []):
            s = binding["s"]["value"]
            p = binding["p"]["value"]
            o = binding["o"]
            if o["type"] == "uri":
                triples.append(Triple(s=s, p=p, o=o["value"], o_type="uri"))
                continue
            triples.append(
                Triple(
                    s=s,
                    p=p,
                    o=o["value"],
                    o_type="literal",
                    o_lang=o.get("xml:lang"),
                    o_datatype=o.get("datatype"),
                )
            )
        return triples

