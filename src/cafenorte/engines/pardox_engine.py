"""PardoX adapter limited to APIs published by PardoX 0.3.4.

PardoX can read CSV, but its published Python API does not document a safe conversion
to the typed records used by this project. Therefore Silver preparation deliberately
falls back to the Polars/Pydantic path and records that fact.
"""

from pathlib import Path

from .common import EngineReport


def prepare(data_dir: Path) -> EngineReport:
    import pardox as px

    report = EngineReport(
        engine="pardox", versions={"pardox": getattr(px, "__version__", "unknown")}
    )
    sales = px.read_csv(str(data_dir / "sales.csv"))
    report.rows["sales"] = int(sales.shape[0])
    report.fallbacks.update(
        {
            "sales": "polars: published SDK does not document typed-record conversion",
            "inventory.json": "polars: nested JSON reader not documented",
            "ecommerce_orders.parquet": "polars: parquet reader not documented",
            "exchange_rates.csv": "polars: Silver preparation remains Polars/Pydantic",
        }
    )
    return report
