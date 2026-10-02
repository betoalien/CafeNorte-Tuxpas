from pathlib import Path

from cafenorte import ingest
from cafenorte.engines import pardox_engine


def test_pardox_reports_documented_fallbacks() -> None:
    report = pardox_engine.prepare(Path("datos"))
    assert report.rows["sales"] == 86490
    assert report.fallbacks["inventory.json"].startswith("polars:")
    assert report.fallbacks["ecommerce_orders.parquet"].startswith("polars:")


def test_pardox_silver_parity() -> None:
    checks = (
        ("pos_sales", "count(*), coalesce(sum(cantidad), 0), coalesce(sum(monto), 0)"),
        ("ecommerce_orders", "count(*), coalesce(sum(cantidad), 0), coalesce(sum(amount), 0)"),
        ("inventory_snapshots", "count(*), coalesce(sum(stock_quantity), 0), 0"),
    )
    with ingest.connect() as conn, conn.cursor() as cur:
        for table, aggregates in checks:
            cur.execute(f"SELECT {aggregates} FROM silver.{table}")
            reference = cur.fetchone()
            cur.execute(f"SELECT {aggregates} FROM silver_pardox.{table}")
            assert cur.fetchone() == reference, f"parity difference in {table}"
        for expression in (
            (
                "tienda_id, date_trunc('month', fecha_hora_normalizada), "
                "count(*), sum(cantidad), sum(monto)"
            ),
            "tipo_comprobante, count(*), sum(cantidad), sum(monto)",
        ):
            reference_sql = (
                f"SELECT {expression} FROM silver.pos_sales GROUP BY 1, 2"
                if expression.startswith("tienda")
                else f"SELECT {expression} FROM silver.pos_sales GROUP BY 1"
            )
            cur.execute(reference_sql)
            reference = sorted(cur.fetchall(), key=str)
            cur.execute(reference_sql.replace("silver.", "silver_pardox."))
            assert sorted(cur.fetchall(), key=str) == reference
