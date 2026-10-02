"""PardoX 0.3.4 implementation for the documented tabular sources."""

import tempfile
import time
from pathlib import Path

from .common import EngineReport


def prepare(data_dir: Path) -> EngineReport:
    import pardox as px

    started = time.perf_counter()
    report = EngineReport(
        engine="pardox", versions={"pardox": getattr(px, "__version__", "unknown")}
    )
    sales = px.read_csv(str(data_dir / "sales.csv"))
    report.source_rows = {"sales": int(sales.shape[0])}
    report.rows.update(report.source_rows)
    report.fallbacks["inventory.json"] = "polars: PardoX 0.3.4 has no nested JSON reader"
    read_seconds = time.perf_counter() - started
    before = time.perf_counter()
    sales.cast("cantidad", "Int64")
    sales.cast("monto", "Float64")
    sales.validate_contract({"columns": {"cantidad": {"min": 1}, "monto": {"min": 0}}})
    validate_seconds = time.perf_counter() - before
    before = time.perf_counter()
    sales.to_dict()
    transform_seconds = time.perf_counter() - before
    before = time.perf_counter()
    sales.to_dict()
    load_seconds = time.perf_counter() - before
    output = Path(tempfile.mkstemp(suffix=".prdx")[1])
    output.unlink(missing_ok=True)
    before = time.perf_counter()
    sales.to_prdx(str(output))
    output_seconds = time.perf_counter() - before
    report.output_path = str(output)
    report.output_bytes = output.stat().st_size
    report.stage_seconds["all"] = {
        "read": read_seconds,
        "validate": validate_seconds,
        "transform": transform_seconds,
        "load": load_seconds,
        "to_prdx": output_seconds,
        "total": time.perf_counter() - started,
    }
    return report
