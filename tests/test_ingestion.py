from decimal import Decimal
from pathlib import Path

import pytest

from cafenorte import ingest

pytestmark = pytest.mark.skipif(
    not Path(".env").exists(), reason="requires the local PostgreSQL environment"
)


def query(sql: str) -> list[tuple]:
    with ingest.connect() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def test_real_sources_and_idempotence() -> None:
    ingest.main()
    first = query(
        """
        SELECT 'pos_sales', count(*), sum(cantidad), sum(monto) FROM silver.pos_sales
        UNION ALL SELECT 'ecommerce_orders', count(*), sum(cantidad), sum(amount)
          FROM silver.ecommerce_orders
        UNION ALL SELECT 'inventory_snapshots', count(*), sum(coalesce(stock_quantity, 0)), NULL
          FROM silver.inventory_snapshots
        """
    )
    ingest.main()
    second = query(
        "SELECT table_name, count(*) FROM information_schema.tables "
        "WHERE table_schema = 'silver' GROUP BY table_name ORDER BY table_name"
    )
    assert first[0][1:] == (86490, 133383, Decimal("30947253.82"))
    assert first[1][1:] == (9947, 13292, Decimal("2984113.06"))
    assert second


def test_silver_privacy_quality_and_fx() -> None:
    pii = query(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'silver' AND column_name IN
        ('customer_name','customer_email','customer_rfc','shipping_address','shipping_city')
        """
    )
    assert pii == []
    assert (
        query(
            "SELECT count(*) FROM silver.inventory_snapshots "
            "WHERE stock_raw_value = 'N/A' AND stock_quantity IS NULL"
        )[0][0]
        == 4417
    )
    assert (
        query(
            "SELECT count(*) FROM silver.exchange_rates "
            "WHERE currency = 'MXN' AND rate_to_mxn = 1.0"
        )[0][0]
        > 0
    )
    assert (
        query(
            "SELECT count(*) FROM silver.exchange_rates "
            "WHERE fx_quality_flag = 'suspected_truncation'"
        )[0][0]
        == 63
    )
    assert (
        query(
            "SELECT count(*) FROM silver.sku_mappings "
            "WHERE sku_pos = 'CN-00006' AND sku_erp IS NULL"
        )[0][0]
        == 1
    )


def test_no_duplicate_business_keys() -> None:
    checks = query(
        """
        SELECT count(*) - count(DISTINCT venta_id) FROM silver.pos_sales
        UNION ALL SELECT count(*) - count(DISTINCT order_id)
          FROM silver.ecommerce_orders
        UNION ALL SELECT count(*) - count(DISTINCT (fecha, tienda_id, sku_erp))
          FROM silver.inventory_snapshots
        """
    )
    assert all(row[0] == 0 for row in checks)
