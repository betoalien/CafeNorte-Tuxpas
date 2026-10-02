select tienda_id, ciudad, region, timezone, run_id, ingested_at
from {{ source('silver', 'stores') }}
where run_id = {{ latest_successful_run_id() }}
