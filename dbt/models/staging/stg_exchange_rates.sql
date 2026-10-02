select fecha, currency, rate_to_mxn::numeric, fx_quality_flag, run_id, ingested_at
from {{ source('silver', 'exchange_rates') }}
where run_id = {{ latest_successful_run_id() }}
