"""Retrieval over a small corpus of sample form guidance documents.

Every answer carries a traceable source reference (document id + section id).
A question with no sufficiently matching passage returns ``None`` — the caller
must report "no source found" instead of letting a model improvise.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CORPUS_DIR = Path(__file__).parent / "fixtures" / "corpus"

_STOPWORDS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "how", "i", "in", "is",
    "it", "my", "of", "or", "the", "to", "what", "when", "where", "which", "who",
    "will", "you", "your",
}

# A passage must share at least this many meaningful terms with the question.
_MIN_OVERLAP = 2


@dataclass(frozen=True)
class SourceRef:
    doc_id: str
    section_id: str
    heading: str


@dataclass(frozen=True)
class Passage:
    text: str
    source: SourceRef


def _terms(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS}


class Corpus:
    def __init__(self, documents: list[dict]) -> None:
        self._documents = documents

    @classmethod
    def load(cls, corpus_dir: Path = DEFAULT_CORPUS_DIR) -> "Corpus":
        documents = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(corpus_dir.glob("*.json"))
        ]
        return cls(documents)

    def search(self, question: str) -> Passage | None:
        """Return the best-matching passage with its source, or ``None``."""
        query_terms = _terms(question)
        best: tuple[int, Passage] | None = None
        for doc in self._documents:
            for section in doc["sections"]:
                overlap = len(query_terms & _terms(section["heading"] + " " + section["text"]))
                if overlap >= _MIN_OVERLAP and (best is None or overlap > best[0]):
                    best = (
                        overlap,
                        Passage(
                            text=section["text"],
                            source=SourceRef(
                                doc_id=doc["doc_id"],
                                section_id=section["section_id"],
                                heading=section["heading"],
                            ),
                        ),
                    )
        return best[1] if best else None
