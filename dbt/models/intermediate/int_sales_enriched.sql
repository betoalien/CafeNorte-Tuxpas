with pos as (
    select
        'POS'::text as source_name,
        s.venta_id::text as source_id,
        s.sale_at,
        s.tienda_id,
        i.product_id,
        i.match_method,
        s.quantity,
        s.amount_mxn,
        'MXN'::text as currency,
        'normal'::text as fx_quality_flag,
        c.effective_unit_cost_mxn,
        s.tipo_comprobante
    from {{ ref('stg_pos_sales') }} s
    join {{ ref('int_product_identity') }} i
      on i.source_name = 'POS' and i.source_id = s.venta_id
    left join {{ ref('int_effective_cost') }} c on c.venta_id = s.venta_id
), online as (
    select
        'Shopify'::text as source_name,
        o.order_id::text as source_id,
        o.ordered_at as sale_at,
        null::text as tienda_id,
        i.product_id,
        i.match_method,
        o.quantity,
        case when r.rate_to_mxn is not null then o.amount * r.rate_to_mxn else null end as amount_mxn,
        o.currency,
        r.fx_quality_flag,
        cost.effective_unit_cost_mxn,
        null::text as tipo_comprobante
    from {{ ref('stg_ecommerce_orders') }} o
    join {{ ref('int_product_identity') }} i
      on i.source_name = 'Shopify' and i.source_id = o.order_id
    left join {{ ref('stg_exchange_rates') }} r
      on r.fecha = o.ordered_at::date and r.currency = o.currency
    left join lateral (
        select (item->>'costo_mxn')::numeric as effective_unit_cost_mxn
        from {{ ref('stg_products') }} p
        cross join lateral jsonb_array_elements(p.cost_history) item
        where p.sku_erp = i.product_id and (item->>'fecha_vigencia')::date <= o.ordered_at::date
        order by (item->>'fecha_vigencia')::date desc limit 1
    ) cost on true
)
select * from pos
union all
select * from online
