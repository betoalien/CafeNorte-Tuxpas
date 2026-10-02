select
    order_id,
    fecha as ordered_at,
    product_handle,
    product_number,
    handle_name_normalized,
    cantidad::numeric as quantity,
    amount::numeric as amount,
    currency,
    run_id,
    ingested_at
from {{ source('silver', 'ecommerce_orders') }}
where run_id = {{ latest_successful_run_id() }}
