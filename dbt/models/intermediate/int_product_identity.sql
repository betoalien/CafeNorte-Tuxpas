with pos as (
    select
        'POS'::text as source_name,
        s.venta_id as source_id,
        s.product_number,
        s.sku as source_sku,
        m.sku_pos is not null as has_mapping,
        m.sku_erp as mapped_sku_erp,
        p.sku_erp as product_id,
        case
            when m.sku_erp is not null and p.sku_erp is not null then 'explicit'
            when m.sku_pos is not null and m.sku_erp is null and p.sku_erp is not null
                then 'product_number_null_erp'
            when m.sku_pos is null and p.sku_erp is not null then 'product_number'
            else 'unmatched'
        end as match_method
    from {{ ref('stg_pos_sales') }} s
    left join {{ ref('stg_sku_mappings') }} m on m.sku_pos = s.sku
    left join {{ ref('stg_products') }} p on p.product_number = s.product_number
), shopify as (
    select
        'Shopify'::text as source_name,
        o.order_id as source_id,
        o.product_number,
        o.product_handle as source_sku,
        m.handle is not null as has_mapping,
        m.sku_erp as mapped_sku_erp,
        p.sku_erp as product_id,
        case
            when m.sku_erp is not null and p_explicit.sku_erp is not null then 'explicit'
            when m.handle is not null and m.sku_erp is null and p.sku_erp is not null
                and o.handle_name_normalized = regexp_replace(lower(translate(p.nombre,
                    'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN')), '[^a-z0-9]', '', 'g')
                then 'product_number_null_erp'
            when m.handle is null and p.sku_erp is not null
                and o.handle_name_normalized = regexp_replace(lower(translate(p.nombre,
                    'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN')), '[^a-z0-9]', '', 'g')
                then 'product_number'
            else 'unmatched'
        end as match_method
    from {{ ref('stg_ecommerce_orders') }} o
    left join {{ ref('stg_sku_mappings') }} m on m.handle = o.product_handle
    left join {{ ref('stg_products') }} p on p.product_number = o.product_number
    left join {{ ref('stg_products') }} p_explicit on p_explicit.sku_erp = m.sku_erp
)
select * from pos
union all
select * from shopify
