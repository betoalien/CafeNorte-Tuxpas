select fecha, tienda_id, sku_erp as product_id, stock_quantity, stock_raw_value,
       quality_status, quality_reason, now() as built_at, 'business_metrics.v1'::text as logic_version
from {{ ref('stg_inventory_snapshots') }}
