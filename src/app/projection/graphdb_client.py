from __future__ import annotations

import re
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from src.app.shared.settings import settings

_IRI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s<>{}]*$")

_PAGE_QUERY = """
SELECT ?s ?p ?o WHERE {{
    GRAPH <{graph_iri}> {{
        ?s ?p ?o .
    }}
}}
ORDER BY ?s ?p ?o
LIMIT {limit} OFFSET {offset}
"""


class ProjectionTooLarge(RuntimeError):
    """The graph holds more triples than the caller allowed."""


@dataclass
class Triple:
    s: str
    p: str
    o: str
    o_type: str  # "uri" | "literal"
    o_lang: str | None = None
    o_datatype: str | None = None


def _check_iri(iri: str) -> str:
    # The graph IRI is interpolated into the query, so reject anything that could
    # close the <...> term or start a new pattern.
    if not _IRI.match(iri):
        raise ValueError(f"not a valid absolute IRI: {iri!r}")
    return iri


class GraphDBClient:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        page_size: int = 50_000,
        timeout: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        self.base_url = (base_url or settings.triplestore_url).rstrip("/")
        self.page_size = page_size
        self.timeout = timeout
        self._transport = transport

    def _query_url(self) -> str:
        return f"{self.base_url}{settings.triplestore_query_endpoint}"

    async def iter_pages(
        self,
        graph_iri: str,
        page_size: int | None = None,
    ) -> AsyncIterator[list[Triple]]:
        """Yield triples page by page until the graph is exhausted.

        OFFSET pagination is the only portable option across SPARQL stores; deep
        offsets cost more than keyset scans, so keep page_size large.
        """
        _check_iri(graph_iri)
        size = page_size or self.page_size
        if size <= 0:
            raise ValueError("page_size must be positive")

        offset = 0
        async with httpx.AsyncClient(timeout=self.timeout, transport=self._transport) as client:
            while True:
                page = await self._fetch_page(client, graph_iri, size, offset)
                yield page
                if len(page) < size:
                    return
                offset += size

    async def fetch_triples(self, graph_iri: str, *, max_triples: int | None = None) -> list[Triple]:
        """Fetch every triple of the graph, or fail loudly when it is too large."""
        triples: list[Triple] = []

        async for page in self.iter_pages(graph_iri):
            if max_triples is not None and len(triples) + len(page) > max_triples:
                raise ProjectionTooLarge(
                    f"graph {graph_iri} holds more than {max_triples} triples; "
                    "raise max_triples or project it in smaller named graphs"
                )
            triples.extend(page)

        return triples

    async def _fetch_page(
        self,
        client: httpx.AsyncClient,
        graph_iri: str,
        limit: int,
        offset: int,
    ) -> list[Triple]:
        query = _PAGE_QUERY.format(graph_iri=graph_iri, limit=limit, offset=offset)
        response = await client.post(
            self._query_url(),
            content=query,
            headers={
                "Accept": "application/sparql-results+json",
                "Content-Type": "application/sparql-query",
            },
        )
        response.raise_for_status()
        data = response.json()
        return _parse_bindings(data)


def _parse_bindings(data: dict) -> list[Triple]:
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
