select
    source_name || ':' || source_id as sale_key,
    source_name, source_id, sale_at::date as sale_date, tienda_id,
    case when source_name = 'Shopify' then 'ONLINE' else tienda_id end as channel,
    product_id, quantity, amount_mxn, currency, effective_unit_cost_mxn,
    case when amount_mxn is not null and effective_unit_cost_mxn is not null
         then amount_mxn - quantity * effective_unit_cost_mxn end as gross_margin_mxn,
    match_method, fx_quality_flag, tipo_comprobante,
    now() as built_at, 'business_metrics.v1'::text as logic_version
from {{ ref('int_sales_enriched') }}
