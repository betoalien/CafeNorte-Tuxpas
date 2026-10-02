select sku_erp, product_number, nombre, categoria, cost_history, run_id, ingested_at
from {{ source('silver', 'products') }}
where run_id = {{ latest_successful_run_id() }}
