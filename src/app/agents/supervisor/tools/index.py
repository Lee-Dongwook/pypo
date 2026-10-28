from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

_TOKEN = re.compile(r"[a-z0-9]+|[ㄱ-ㆎ가-힣一-鿿]")
_K1 = 1.5
_B = 0.75

def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())

@dataclass
class Bm25Index:
    names: list[str]
    postings: dict[str, list[tuple[int, int]]]
    doc_lengths: list[int]
    avg_length: float

    def search(self, query: str, k: int) -> list[str]:
        n = len(self.names)
        if not n:
            return []
        scores: dict[int, float] = []
        for term in tokenize(query):
            if not (postings := self.postings.get(term)):
                continue
            
            df = len(postings)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for doc, tf in postings:
                norm = tf + _K1 * (1 - _B + _B * self.doc_lengths[doc] / self.avg_length)
                scores[doc] = scores.get(doc, 0.0) + idf * (tf * (_K1 + 1)) / norm
        ranked = sorted(scores.items(), key=lambda p: (-p[1], p[0]))
        return [self.names[doc] for doc, _ in ranked[:k]]
