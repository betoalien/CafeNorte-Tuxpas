select fecha, tienda_id, sku_erp, stock_quantity, stock_raw_value, quality_status, quality_reason,
       run_id, ingested_at
from {{ source('silver', 'inventory_snapshots') }}
where run_id = {{ latest_successful_run_id() }}
