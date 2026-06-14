from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from embedding_cache import LibraryEmbeddingCache, build_library_fingerprint
from models import LibraryPaper


class CountingEmbedder:
    def __init__(self):
        self.calls = 0

    def encode(self, texts: list[str]) -> np.ndarray:
        self.calls += 1
        rows = []
        for index, text in enumerate(texts):
            rows.append(np.array([float(len(text)), float(index + 1)], dtype=np.float32))
        return np.stack(rows, axis=0)


class EmbeddingCacheTest(unittest.TestCase):
    def test_load_or_compute_reuses_cached_library_embeddings(self) -> None:
        papers = [
            LibraryPaper(
                title="Graph Neural Networks",
                abstract="Message passing for graph data.",
                source_file="data/library.example.bib",
                doi="10.1000/gnn",
            ),
            LibraryPaper(
                title="Vision Transformers",
                abstract="Transformer architectures for image recognition.",
                source_file="data/library.example.bib",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = LibraryEmbeddingCache(Path(tmp_dir), "BAAI/bge-small-en-v1.5")
            embedder = CountingEmbedder()

            first = cache.load_or_compute(papers, embedder)
            second = cache.load_or_compute(papers, embedder)

        self.assertEqual(1, embedder.calls)
        self.assertEqual(first.shape, second.shape)
        self.assertTrue(np.array_equal(first, second))

    def test_fingerprint_changes_when_library_content_changes(self) -> None:
        base = [
            LibraryPaper(
                title="Graph Neural Networks",
                abstract="Message passing for graph data.",
                source_file="data/library.example.bib",
            )
        ]
        modified = [
            LibraryPaper(
                title="Graph Neural Networks",
                abstract="A different abstract changes the semantic cache key.",
                source_file="data/library.bib",
            )
        ]

        self.assertNotEqual(
            build_library_fingerprint("BAAI/bge-small-en-v1.5", base),
            build_library_fingerprint("BAAI/bge-small-en-v1.5", modified),
        )


if __name__ == "__main__":
    unittest.main()
