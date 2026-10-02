"""PardoX 0.3.4 implementation for the documented tabular sources."""

import tempfile
import time
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

from .common import EngineReport


def connection_url() -> str:
    import os

    return (
        f"postgresql://{quote(os.environ.get('PIPELINE_USER', 'pipeline'))}:"
        f"{quote(os.environ['PIPELINE_PASSWORD'])}@{os.environ.get('POSTGRES_HOST', '127.0.0.1')}:"
        f"{os.environ.get('POSTGRES_PORT', '5432')}/{os.environ['POSTGRES_DB']}"
    )


def native_load_pos_sales(path: Path, run_id: UUID, ingested_at) -> tuple[int, int]:
    """Load PardoX's own DataFrame into an isolated stage and final table."""
    import pardox as px

    conn_url = connection_url()
    frame = px.read_csv(str(path))
    frame.cast("cantidad", "Int64")
    frame.cast("monto", "Float64")
    frame.validate_contract({"columns": {"cantidad": {"min": 1}, "monto": {"min": 0}}})
    records = frame.shape[0]
    px.execute_sql(conn_url, "DROP TABLE IF EXISTS silver_pardox.pos_sales_stage")
    px.execute_sql(
        conn_url,
        """CREATE TABLE silver_pardox.pos_sales_stage (
          venta_id text, fecha_hora text, tienda_id text, sku text,
          cantidad bigint, monto double precision, moneda text, tipo_comprobante text
        )""",
    )
    px.execute_sql(conn_url, "TRUNCATE silver_pardox.pos_sales_stage")
    written = frame.to_sql(conn_url, "silver_pardox.pos_sales_stage", mode="append")
    px.execute_sql(
        conn_url,
        """CREATE TABLE IF NOT EXISTS silver_pardox.pos_sales (
          venta_id text PRIMARY KEY, fecha_hora_original text NOT NULL,
          fecha_hora_normalizada timestamp NOT NULL, tienda_id text NOT NULL, sku text NOT NULL,
          product_number text, cantidad bigint NOT NULL, monto numeric(18,2) NOT NULL,
          moneda text NOT NULL, tipo_comprobante text NOT NULL, run_id uuid NOT NULL,
          ingested_at timestamptz NOT NULL, row_hash text NOT NULL
        )""",
    )
    px.execute_sql(conn_url, "TRUNCATE silver_pardox.pos_sales")
    px.execute_sql(
        conn_url,
        f"""INSERT INTO silver_pardox.pos_sales
        SELECT venta_id, fecha_hora, fecha_hora::timestamp, tienda_id, sku,
               right(regexp_replace(sku, '[^0-9]', '', 'g'), 3), cantidad,
               monto::numeric(18,2), moneda, tipo_comprobante, '{run_id}'::uuid,
               '{ingested_at.isoformat()}'::timestamptz, ''
        FROM silver_pardox.pos_sales_stage
        WHERE moneda = 'MXN'""",
    )
    return int(written), int(records)


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
