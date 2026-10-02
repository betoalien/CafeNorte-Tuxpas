from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CONTRACT_VERSION = "silver.v1"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SalesRecord(StrictModel):
    venta_id: str = Field(min_length=1)
    fecha_hora: datetime
    tienda_id: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    monto: float = Field(gt=0)
    moneda: str = Field(min_length=1)
    tipo_comprobante: str = Field(min_length=1)


class StoreRecord(StrictModel):
    tienda_id: str = Field(min_length=1)
    ciudad: str
    region: str
    timezone: str


class MappingRecord(StrictModel):
    sku_pos: str = Field(min_length=1)
    sku_erp: str | None = None
    handle: str | None = None


class CostRecord(StrictModel):
    fecha_vigencia: date
    costo_mxn: float = Field(ge=0)
    proveedor: str


class ProductRecord(StrictModel):
    sku_erp: str = Field(min_length=1)
    nombre: str
    categoria: str
    cost_history: list[CostRecord]


class SnapshotRecord(StrictModel):
    fecha: date
    tienda_id: str = Field(min_length=1)
    sku_erp: str = Field(min_length=1)
    cantidad_en_stock: int | Literal["N/A"]

    @field_validator("cantidad_en_stock")
    @classmethod
    def non_negative_or_unknown(cls, value: int | Literal["N/A"]) -> int | Literal["N/A"]:
        if value != "N/A" and value < 0:
            raise ValueError("stock must be non-negative or N/A")
        return value


class EcommerceOrderRecord(StrictModel):
    order_id: str = Field(min_length=1)
    fecha: datetime
    product_handle: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    amount: float = Field(gt=0)
    currency: str = Field(min_length=1)


class ExchangeRateRecord(StrictModel):
    fecha: date
    currency: str = Field(min_length=3, max_length=3)
    rate_to_mxn: float = Field(gt=0)


class Manifest(StrictModel):
    run_id: UUID
    source_file: str
    sha256_before: str
    sha256_after: str
    size_bytes: int = Field(ge=0)
    input_count: int = Field(ge=0)
    accepted_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    contract_version: str
    started_at: datetime
    completed_at: datetime

    @field_validator("sha256_before", "sha256_after")
    @classmethod
    def valid_hash(cls, value: str) -> str:
        if len(value) != 64:
            raise ValueError("SHA-256 must contain 64 hexadecimal characters")
        int(value, 16)
        return value


class QuarantineRecord(StrictModel):
    source: str
    record_key: str
    reason: str
    payload: dict[str, Any]
    run_id: UUID
