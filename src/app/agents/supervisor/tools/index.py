from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

_TOKEN = re.compile(r"[a-z0-9]+|[ㄱ-ㆎ가-힣一-鿿]")
_K1 = 1.5
_B = 0.75


def tokenize(text: str) -> list[str]:
    # NOTE: Hangul is split per character. Proper segmentation needs a morphological
    # analyzer or at least bigrams; keep this in mind when retrieval quality matters.
    return _TOKEN.findall(text.lower())


@dataclass
class Bm25Index:
    names: list[str]
    postings: dict[str, list[tuple[int, int]]]
    doc_lengths: list[int]
    avg_length: float

    @classmethod
    def from_names(cls, names: list[str]) -> Bm25Index:
        postings: dict[str, list[tuple[int, int]]] = {}
        doc_lengths: list[int] = []

        for doc, name in enumerate(names):
            tokens = tokenize(name)
            doc_lengths.append(len(tokens))
            for term, tf in Counter(tokens).items():
                postings.setdefault(term, []).append((doc, tf))

        avg_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0.0
        return cls(names=list(names), postings=postings, doc_lengths=doc_lengths, avg_length=avg_length)

    def search(self, query: str, k: int) -> list[str]:
        n = len(self.names)
        if not n or k <= 0 or self.avg_length <= 0:
            return []

        scores: dict[int, float] = {}
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
