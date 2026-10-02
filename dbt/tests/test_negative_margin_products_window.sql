with totals as (
    select product_id, round(sum(gross_margin_mxn)::numeric, 2) as margin_mxn
    from {{ ref('mart_negative_margin_products') }}
    group by product_id
), expected as (
    select * from (values
        ('ERP-PROV-MX-015-D', -158216.09::numeric),
        ('ERP-PROV-MX-002-B', -47595.85::numeric),
        ('ERP-PROV-MX-001-A', -12663.62::numeric)
    ) as values(product_id, margin_mxn)
), mismatches as (
    select coalesce(t.product_id, e.product_id) as product_id
    from totals t full join expected e using (product_id)
    where t.product_id is null or e.product_id is null
       or abs(t.margin_mxn - e.margin_mxn) > 0.01
)
select * from mismatches
