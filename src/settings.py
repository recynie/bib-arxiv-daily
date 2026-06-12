from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ArxivSettings:
    categories: tuple[str, ...]
    max_candidates: int


@dataclass(frozen=True)
class EmbeddingSettings:
    model: str
    batch_size: int


@dataclass(frozen=True)
class RankingSettings:
    top_k_neighbors: int
    max_results: int


@dataclass(frozen=True)
class RuntimeSettings:
    data_dir: Path
    output_html: Path
    cache_dir: Path


@dataclass(frozen=True)
class AppSettings:
    arxiv: ArxivSettings
    embedding: EmbeddingSettings
    ranking: RankingSettings
    runtime: RuntimeSettings


def _require_int(section: dict, key: str, default: int) -> int:
    value = section.get(key, default)
    return int(value)


def _require_bool(section: dict, key: str, default: bool) -> bool:
    value = section.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def load_settings(config_path: Path) -> AppSettings:
    raw_data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    arxiv_section = raw_data.get("arxiv", {})
    embedding_section = raw_data.get("embedding", {})
    ranking_section = raw_data.get("ranking", {})
    runtime_section = raw_data.get("runtime", {})

    categories = tuple(str(item).strip() for item in arxiv_section.get("categories", []) if str(item).strip())

    return AppSettings(
        arxiv=ArxivSettings(
            categories=categories,
            max_candidates=_require_int(arxiv_section, "max_candidates", 80),
        ),
        embedding=EmbeddingSettings(
            model=str(embedding_section.get("model", "BAAI/bge-small-en-v1.5")),
            batch_size=_require_int(embedding_section, "batch_size", 32),
        ),
        ranking=RankingSettings(
            top_k_neighbors=max(1, _require_int(ranking_section, "top_k_neighbors", 5)),
            max_results=max(1, _require_int(ranking_section, "max_results", 15)),
        ),
        runtime=RuntimeSettings(
            data_dir=Path(runtime_section.get("data_dir", "data")),
            output_html=Path(runtime_section.get("output_html", "output/latest_report.html")),
            cache_dir=Path(runtime_section.get("cache_dir", ".cache/recommender")),
        ),
    )
