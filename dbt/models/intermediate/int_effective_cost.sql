select *
from (
    select
        s.venta_id,
        s.sku,
        c.sku_erp as product_id,
        (cost_item->>'fecha_vigencia')::date as effective_from,
        (cost_item->>'costo_mxn')::numeric as effective_unit_cost_mxn,
        row_number() over (
            partition by s.venta_id order by (cost_item->>'fecha_vigencia')::date desc
        ) as cost_rank
    from {{ ref('stg_pos_sales') }} s
    join {{ ref('stg_products') }} c on c.product_number = s.product_number
    cross join lateral jsonb_array_elements(c.cost_history) cost_item
    where (cost_item->>'fecha_vigencia')::date <= s.sale_at::date
) ranked
where cost_rank = 1
