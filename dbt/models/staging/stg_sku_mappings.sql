select sku_pos, sku_erp, handle, run_id, ingested_at
from {{ source('silver', 'sku_mappings') }}
where run_id = {{ latest_successful_run_id() }}
