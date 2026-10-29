#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path

from src.app.shared.neo4j import close_driver, get_driver


def main() -> None:
    cypher_path = Path(__file__).parent / "init.cypher"
    if not cypher_path.exists():
        raise FileNotFoundError(f"Missing {cypher_path}")

    text = cypher_path.read_text(encoding="utf-8")
    statements = []
    for raw in text.split(";"):
        stmt = raw.strip()
        if not stmt:
            continue
        lines = []
        for line in stmt.splitlines():
            s = line.strip()
            if not s or s.startswith("//"):
                continue
            lines.append(line)
        cleaned = "\n".join(lines).strip()
        if cleaned:
            statements.append(cleaned)

    driver = get_driver()
    try:
        with driver.session() as session:
            for stmt in statements:
                session.run(stmt)
                print(f"OK: {stmt.splitlines()[0][:80]}...")
        print("Neo4j schema initialized successfully.")
    finally:
        close_driver()


if __name__ == "__main__":
    main()
