"""Small, explicit engine contract. Silver preparation remains owned by ingest."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EngineReport:
    engine: str
    versions: dict[str, str]
    fallbacks: dict[str, str] = field(default_factory=dict)
    rows: dict[str, int] = field(default_factory=dict)
    output_bytes: int = 0
    output_path: str | None = None


def engine_report(engine: str, data_dir: Path) -> EngineReport:
    return EngineReport(engine=engine, versions={"python": "", "polars": ""})


def validate_engine(value: str) -> str:
    if value not in {"polars", "pardox"}:
        raise ValueError(f"Unsupported engine: {value}")
    return value
