from pathlib import Path

from cafenorte import ingest
from cafenorte.engines import pardox_engine
from cafenorte.engines.parity import check_parity


def test_pardox_reports_documented_fallbacks() -> None:
    report = pardox_engine.prepare(Path("datos"))
    assert report.rows["sales"] == 86490
    assert report.fallbacks["inventory.json"].startswith("polars:")
    assert "ecommerce_orders" not in report.fallbacks


def test_pardox_silver_parity() -> None:
    with ingest.connect() as conn, conn.cursor() as cur:
        assert check_parity(conn) == []
        cur.execute("SELECT count(*), sum(cantidad), sum(monto) FROM silver.pos_sales")
        assert cur.fetchone()[:2] == (86490, 133383)


def test_pardox_native_to_sql_count() -> None:
    written, accepted = pardox_engine.native_load_pos_sales(
        Path("datos/sales.csv"),
        __import__("uuid").uuid4(),
        __import__("datetime").datetime.now(__import__("datetime").UTC),
    )
    assert written == 86490
    assert accepted == 86490


def test_pardox_parity_negative_control() -> None:
    with ingest.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT venta_id, monto FROM silver_pardox.pos_sales LIMIT 1")
        venta_id, original = cur.fetchone()
        cur.execute(
            "UPDATE silver_pardox.pos_sales SET monto = monto + 1 WHERE venta_id = %s",
            (venta_id,),
        )
        assert check_parity(conn) == [str(venta_id)]
        cur.execute(
            "UPDATE silver_pardox.pos_sales SET monto = %s WHERE venta_id = %s",
            (original, venta_id),
        )
        assert check_parity(conn) == []


def test_pardox_parity_deleted_row_control() -> None:
    with ingest.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT venta_id FROM silver_pardox.pos_sales LIMIT 1")
        venta_id = cur.fetchone()[0]
        cur.execute("DELETE FROM silver_pardox.pos_sales WHERE venta_id = %s", (venta_id,))
        assert check_parity(conn) == [str(venta_id)]
        cur.execute(
            "INSERT INTO silver_pardox.pos_sales SELECT * FROM silver.pos_sales "
            "WHERE venta_id = %s",
            (venta_id,),
        )
        assert check_parity(conn) == []
