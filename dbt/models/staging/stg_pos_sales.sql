select
    venta_id,
    fecha_hora_normalizada as sale_at,
    fecha_hora_original,
    tienda_id,
    sku,
    product_number,
    cantidad::numeric as quantity,
    monto::numeric as amount_mxn,
    moneda,
    tipo_comprobante,
    run_id,
    ingested_at
from {{ source('silver', 'pos_sales') }}
where run_id = {{ latest_successful_run_id() }}
