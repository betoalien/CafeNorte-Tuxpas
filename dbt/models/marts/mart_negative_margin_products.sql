select product_id, channel, tienda_id, sum(quantity) as units,
       sum(amount_mxn) as sales_mxn, sum(quantity * effective_unit_cost_mxn) as cost_mxn,
       sum(gross_margin_mxn) as gross_margin_mxn,
       '2025-04-01/2026-03-31'::text as period, now() as built_at,
       'business_metrics.v1'::text as logic_version
from {{ ref('fct_sales') }}
where amount_mxn is not null and effective_unit_cost_mxn is not null
group by product_id, channel, tienda_id
having sum(gross_margin_mxn) < 0
