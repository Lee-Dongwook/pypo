"""Cypher statements and query helpers shared by the search subgraph nodes."""

from __future__ import annotations

import re

FULLTEXT_INDEX_NAME = "combinedIndex"
FULLTEXT_INDEX_LABELS = "Link|Memo|File"
FULLTEXT_INDEX_PROPERTIES = "n.title, n.tags, n.description"

# The CJK analyzer is required for Korean/Chinese/Japanese text. `IF NOT EXISTS`
# keeps this safe to run on every cold start.
CREATE_FULLTEXT_INDEX = (
    f"CREATE FULLTEXT INDEX {FULLTEXT_INDEX_NAME} IF NOT EXISTS "
    f"FOR (n:{FULLTEXT_INDEX_LABELS}) ON EACH [{FULLTEXT_INDEX_PROPERTIES}] "
    "OPTIONS {indexConfig: {`fulltext.analyzer`: 'cjk'}}"
)

FULLTEXT_SEARCH = f"""
CALL db.index.fulltext.queryNodes('{FULLTEXT_INDEX_NAME}', $kw) YIELD node, score
WHERE node.user_uuid = $user_uuid
RETURN elementId(node) AS node_id,
    node.title AS title,
    node.url AS url,
    node.description AS description,
    node.tags AS tags,
    node.created_at AS created_at,
    score
ORDER BY score DESC
LIMIT $limit
"""

DEFAULT_RESULT_LIMIT = 5

# Lucene treats these as operators/grouping. Escaping them keeps free-form user
# input from turning into a parse error or an unintended boolean query.
_LUCENE_SPECIAL = re.compile(r'([+\-!(){}\[\]^"~*?:\\/&|])')


def escape_lucene(text: str) -> str:
    """Escape Lucene query syntax so ``text`` is matched literally."""
    return _LUCENE_SPECIAL.sub(r"\\\1", text)


__all__ = [
    "CREATE_FULLTEXT_INDEX",
    "DEFAULT_RESULT_LIMIT",
    "FULLTEXT_INDEX_NAME",
    "FULLTEXT_SEARCH",
    "escape_lucene",
]
