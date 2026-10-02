from pathlib import Path

from cafenorte import ingest
from cafenorte.engines import pardox_engine


def test_pardox_reports_documented_fallbacks() -> None:
    report = pardox_engine.prepare(Path("datos"))
    assert report.rows["sales"] == 86490
    assert report.fallbacks["inventory.json"].startswith("polars:")
    assert "ecommerce_orders" not in report.fallbacks


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


def test_pardox_parity_negative_control() -> None:
    with ingest.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT venta_id, monto FROM silver_pardox.pos_sales LIMIT 1")
        venta_id, original = cur.fetchone()
        cur.execute(
            "UPDATE silver_pardox.pos_sales SET monto = monto + 1 WHERE venta_id = %s",
            (venta_id,),
        )
        cur.execute("SELECT monto FROM silver.pos_sales WHERE venta_id = %s", (venta_id,))
        reference = cur.fetchone()[0]
        cur.execute("SELECT monto FROM silver_pardox.pos_sales WHERE venta_id = %s", (venta_id,))
        altered = cur.fetchone()[0]
        assert altered != reference
        cur.execute(
            "UPDATE silver_pardox.pos_sales SET monto = %s WHERE venta_id = %s",
            (original, venta_id),
        )
