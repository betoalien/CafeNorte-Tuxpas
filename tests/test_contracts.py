import json
from pathlib import Path
from uuid import uuid4

import polars as pl

from cafenorte.contracts import EcommerceOrderRecord, MappingRecord, SnapshotRecord
from cafenorte.ingest import parse_records

ROOT = Path(__file__).resolve().parents[1]


def test_na_is_unknown_not_zero() -> None:
    record = SnapshotRecord(
        fecha="2025-10-01", tienda_id="T001", sku_erp="ERP-001", cantidad_en_stock="N/A"
    )
    assert record.cantidad_en_stock == "N/A"


def test_null_mapping_is_preserved_and_product_number_is_recoverable() -> None:
    inventory = json.loads((ROOT / "datos/inventory.json").read_text(encoding="utf-8"))
    mapping = next(item for item in inventory["sku_mappings"] if item["sku_pos"] == "CN-00006")
    assert MappingRecord.model_validate(mapping).sku_erp is None
    assert any(item["sku_erp"].endswith("006-C") for item in inventory["catalogo"]["productos"])


def test_pii_columns_are_not_selected_for_silver() -> None:
    schema = pl.read_parquet(ROOT / "datos/ecommerce_orders.parquet").schema
    selected = set(EcommerceOrderRecord.model_fields)
    assert {"customer_name", "customer_email", "customer_rfc", "shipping_address"}.isdisjoint(
        selected
    )
    assert set(selected) <= set(schema)


def test_invalid_record_is_quarantined_without_discarding_it_silently() -> None:
    accepted, rejected = parse_records(
        "synthetic",
        [
            {
                "order_id": "bad",
                "fecha": "not-a-date",
                "product_handle": "x",
                "cantidad": 0,
                "amount": 1,
                "currency": "MXN",
            }
        ],
        EcommerceOrderRecord,
        lambda row: row["order_id"],
        uuid4(),
    )
    assert accepted == []
    assert rejected[0].record_key == "bad"
    assert rejected[0].payload["order_id"] == "bad"
