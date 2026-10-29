#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path

from src.app.shared.neo4j import get_driver

def main() -> None:
    cypher_path = Path(__file__).parent / "init.cypher"
    statements = cypher_path.read_text(encoding="utf-8").split(";")

    driver = get_driver()
    with driver.session() as session:
        for stmt in statements:
            stmt = stmt.rstrip()
            if not stmt or stmt.startswith("//"):
                continue
            session.run(stmt)
            print(f"OK: {stmt[:60]}....")
    driver.close()
    print("Neo4j schema initialized.")

if __name__ == "__main__":
    main()
