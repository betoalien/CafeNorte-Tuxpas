"""Reference engine. Existing ingestion transformations remain the oracle."""

from pathlib import Path

from .common import EngineReport


def prepare(data_dir: Path) -> EngineReport:
    return EngineReport(engine="polars", versions={})
