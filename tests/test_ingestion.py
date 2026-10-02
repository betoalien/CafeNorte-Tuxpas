import csv
import shutil
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from cafenorte import ingest


def query(sql: str) -> list[tuple]:
    with ingest.connect() as conn, conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def latest_run_id() -> str:
    return str(query("SELECT run_id FROM audit.run_log ORDER BY started_at DESC LIMIT 1")[0][0])


def test_real_sources_and_idempotence() -> None:
    ingest._run(uuid4(), ingest.now())
    first = query(
        """
        SELECT table_name, rows, units, amount FROM (
          SELECT 'pos_sales' AS table_name, count(*) AS rows, sum(cantidad) AS units,
                 sum(monto) AS amount FROM silver.pos_sales
          UNION ALL SELECT 'ecommerce_orders', count(*), sum(cantidad), sum(amount)
            FROM silver.ecommerce_orders
          UNION ALL SELECT 'inventory_snapshots', count(*), sum(stock_quantity), NULL
            FROM silver.inventory_snapshots
          UNION ALL SELECT 'stores', count(*), NULL, NULL FROM silver.stores
          UNION ALL SELECT 'products', count(*), NULL, NULL FROM silver.products
          UNION ALL SELECT 'sku_mappings', count(*), NULL, NULL FROM silver.sku_mappings
          UNION ALL SELECT 'exchange_rates', count(*), NULL, NULL FROM silver.exchange_rates
        ) silver_counts ORDER BY table_name
        """
    )
    first_run_id = latest_run_id()
    first_quarantine = query(
        "SELECT count(*) FROM audit.quarantine WHERE run_id = '" + first_run_id + "'"
    )[0][0]
    ingest._run(uuid4(), ingest.now())
    second = query(
        """
        SELECT table_name, rows, units, amount FROM (
          SELECT 'pos_sales' AS table_name, count(*) AS rows, sum(cantidad) AS units,
                 sum(monto) AS amount FROM silver.pos_sales
          UNION ALL SELECT 'ecommerce_orders', count(*), sum(cantidad), sum(amount)
            FROM silver.ecommerce_orders
          UNION ALL SELECT 'inventory_snapshots', count(*), sum(stock_quantity), NULL
            FROM silver.inventory_snapshots
          UNION ALL SELECT 'stores', count(*), NULL, NULL FROM silver.stores
          UNION ALL SELECT 'products', count(*), NULL, NULL FROM silver.products
          UNION ALL SELECT 'sku_mappings', count(*), NULL, NULL FROM silver.sku_mappings
          UNION ALL SELECT 'exchange_rates', count(*), NULL, NULL FROM silver.exchange_rates
        ) silver_counts ORDER BY table_name
        """
    )
    second_run_id = latest_run_id()
    second_quarantine = query(
        "SELECT count(*) FROM audit.quarantine WHERE run_id = '" + second_run_id + "'"
    )[0][0]
    assert first == second
    assert first_quarantine == second_quarantine
    assert first[3][1:] == (86490, 133383, Decimal("30947253.82"))
    assert first[0][1:] == (9947, 13292, Decimal("2984113.06"))


def test_cfdi_counts_and_positive_values() -> None:
    rows = query(
        """
        SELECT tipo_comprobante, count(*), min(cantidad), min(monto)
        FROM silver.pos_sales GROUP BY tipo_comprobante ORDER BY tipo_comprobante
        """
    )
    assert {row[0]: row[1] for row in rows} == {
        "I": 82518,
        "E": 3079,
        "P": 451,
        "N": 288,
        "T": 154,
    }
    assert all(row[2] > 0 and row[3] > Decimal("0") for row in rows)
    assert sum(row[1] for row in rows) == 86490


def test_latest_manifest_matches_source_hashes() -> None:
    manifests = query(
        """
        SELECT source_file, sha256_before, sha256_after
        FROM audit.ingestion_manifest
        WHERE run_id = (SELECT run_id FROM audit.run_log WHERE status = 'succeeded' AND load_mode <> 'skipped'
                        ORDER BY started_at DESC LIMIT 1)
        ORDER BY source_file
        """
    )
    paths = {"datos/" + path.name: path for path in Path("datos").iterdir()}
    assert len(manifests) == 4
    for source_file, before, after in manifests:
        actual = ingest.sha256(paths[source_file])
        assert before == actual
        assert after == actual


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


def test_real_incremental_and_full_modes_with_temp_sources(tmp_path, monkeypatch) -> None:
    temp_data = tmp_path / "datos"
    shutil.copytree(Path("datos"), temp_data)
    original_data = ingest.DATA
    monkeypatch.setattr(ingest, "DATA", temp_data)
    try:
        ingest._run(uuid4(), datetime.now(UTC), force=True)
        baseline = query(
            "SELECT venta_id, run_id, monto FROM silver.pos_sales ORDER BY venta_id LIMIT 1"
        )[0]
        baseline_other = query("SELECT run_id FROM silver.ecommerce_orders LIMIT 1")[0][0]

        ingest._run(uuid4(), datetime.now(UTC))
        assert (
            query(f"SELECT run_id FROM silver.pos_sales WHERE venta_id = '{baseline[0]}'")[0][0]
            == baseline[1]
        )

        sales_path = temp_data / "sales.csv"
        with sales_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
            fieldnames = rows[0].keys()
        for index in range(3):
            row = dict(rows[index])
            row["venta_id"] = f"D1-3-NEW-{index}"
            rows.append(row)
        with sales_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        ingest._run(uuid4(), datetime.now(UTC))
        assert query("SELECT count(*) FROM silver.pos_sales")[0][0] == 86493
        assert (
            query(f"SELECT run_id FROM silver.pos_sales WHERE venta_id = '{baseline[0]}'")[0][0]
            == baseline[1]
        )

        rows[0]["monto"] = "999.99"
        with sales_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        ingest._run(uuid4(), datetime.now(UTC))
        assert query(f"SELECT monto FROM silver.pos_sales WHERE venta_id = '{baseline[0]}'")[0][
            0
        ] == Decimal("999.99")
        assert query("SELECT count(*) - count(DISTINCT venta_id) FROM silver.pos_sales")[0][0] == 0
        assert query("SELECT run_id FROM silver.ecommerce_orders LIMIT 1")[0][0] == baseline_other

        rows = [row for row in rows if row["venta_id"] != "V00000000"]
        with sales_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        ingest._run(uuid4(), datetime.now(UTC))
        assert (
            query(f"SELECT count(*) FROM silver.pos_sales WHERE venta_id = '{baseline[0]}'")[0][0]
            == 0
        )
    finally:
        monkeypatch.setattr(ingest, "DATA", original_data)
        ingest._run(uuid4(), datetime.now(UTC), force=True)
