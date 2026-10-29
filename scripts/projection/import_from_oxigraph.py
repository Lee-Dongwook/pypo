#!/usr/bin/env python
from __future__ import annotations

import argparse
import asyncio

from src.app.projection.service import ProjectionService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import triples from Oxigraph/GraphDB into Neo4j projection")
    parser.add_argument("--graph", action="append", required=True, help="Named graph IRI (repeatable)")
    parser.add_argument("--tenant", default="test", help="Tenant slug")
    parser.add_argument("--version", default="v1", help="Ontology version")
    parser.add_argument("--inferred", action="store_true", help="Mark the graph as inferred output")
    parser.add_argument(
        "--inferred-graph",
        action="append",
        default=None,
        help="Mark only this named graph IRI as inferred (repeatable)",
    )
    parser.add_argument("--rule-id", default=None, help="Rule id for inferred triples")
    parser.add_argument("--no-replace", action="store_true", help="Keep the existing projection")
    parser.add_argument("--max-triples", type=int, default=None, help="Per-graph triple limit")
    args = parser.parse_args()

    svc = ProjectionService()

    if len(args.graph) == 1:
        inferred = args.inferred or (
            args.inferred_graph is not None and args.graph[0] in args.inferred_graph
        )
        print(
            await svc.rebuild_from_graph(
                args.graph[0],
                args.tenant,
                args.version,
                inferred=inferred,
                rule_id=args.rule_id,
                replace=not args.no_replace,
                max_triples=args.max_triples,
            )
        )
    else:
        print(
            await svc.rebuild_from_graphs(
                args.graph,
                args.tenant,
                args.version,
                inferred=args.inferred,
                inferred_graphs=set(args.inferred_graph) if args.inferred_graph else None,
                rule_id=args.rule_id,
                replace=not args.no_replace,
                max_triples=args.max_triples,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
