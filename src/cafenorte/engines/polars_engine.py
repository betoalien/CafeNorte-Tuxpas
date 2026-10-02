"""Reference engine. Existing ingestion transformations remain the oracle."""

import json
import tempfile
import time
from pathlib import Path

import polars as pl

from .common import EngineReport


def prepare(data_dir: Path) -> EngineReport:
    report = EngineReport(engine="polars", versions={"polars": pl.__version__})
    started = time.perf_counter()
    sales = pl.read_csv(data_dir / "sales.csv")
    rates = pl.read_csv(data_dir / "exchange_rates.csv")
    orders = pl.read_parquet(data_dir / "ecommerce_orders.parquet")
    inventory = json.loads((data_dir / "inventory.json").read_text(encoding="utf-8"))
    report.stage_seconds["all"] = {"read": time.perf_counter() - started}
    report.source_rows = {
        "sales": sales.height,
        "exchange_rates": rates.height,
        "ecommerce_orders": orders.height,
        "inventory": len(inventory["snapshots"]),
    }
    report.rows.update(report.source_rows)
    before = time.perf_counter()
    valid = sales.filter(
        (pl.col("cantidad") > 0) & (pl.col("monto") > 0) & (pl.col("moneda") == "MXN")
    )
    valid.to_dicts()
    report.stage_seconds["all"]["validate"] = time.perf_counter() - before
    before = time.perf_counter()
    transformed = sales.with_columns(
        pl.col("sku").str.extract(r"(\d{3})(?:-[A-Za-z])?$", 1).alias("product_number")
    )
    transformed.to_dicts()
    report.stage_seconds["all"]["transform"] = time.perf_counter() - before
    before = time.perf_counter()
    transformed.to_dicts()
    report.stage_seconds["all"]["load"] = time.perf_counter() - before
    report.stage_seconds["all"]["total"] = time.perf_counter() - started
    output = Path(tempfile.mkstemp(suffix=".prdx")[1])
    output.unlink(missing_ok=True)
    csv_output = output.with_suffix(".csv")
    sales.write_csv(csv_output)
    report.output_path = str(csv_output)
    report.output_bytes = csv_output.stat().st_size
    return report
