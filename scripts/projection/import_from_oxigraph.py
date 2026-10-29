#!/usr/bin/env python
from __future__ import annotations

import argparse
import asyncio

from src.app.projection.service import ProjectionService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import triples from Oxigraph/GraphDB into Neo4j projection")
    parser.add_argument("--graph", required=True, help="Named graph IRI")
    parser.add_argument("--tenant", default="test", help="Tenant slug")
    parser.add_argument("--version", default="v1", help="Ontology version")
    args = parser.parse_args()

    svc = ProjectionService()
    res = await svc.rebuild_from_graph(args.graph, args.tenant, args.version)
    print(res)


if __name__ == "__main__":
    asyncio.run(main())
