with source_rows as (
    select 'POS'::text as source_name, sale_date as period, product_id, match_method,
           count(*) as input_rows, sum(quantity) as input_units, sum(amount_mxn) as input_amount,
           count(*) filter (where amount_mxn is not null and effective_unit_cost_mxn is not null
                            and match_method <> 'unmatched') as certified_rows,
           sum(quantity) filter (where amount_mxn is not null and effective_unit_cost_mxn is not null
                                and match_method <> 'unmatched') as certified_units,
           sum(amount_mxn) filter (where amount_mxn is not null and effective_unit_cost_mxn is not null
                                  and match_method <> 'unmatched') as certified_amount,
           count(*) filter (where match_method = 'unmatched') as unmatched_rows,
           count(*) filter (where amount_mxn is null) as no_fx_rows,
           count(*) filter (where effective_unit_cost_mxn is null) as no_cost_rows,
           count(*) filter (where amount_mxn is null or effective_unit_cost_mxn is null
                            or match_method = 'unmatched') as excluded_rows
    from {{ ref('fct_sales') }} where source_name = 'POS'
    group by sale_date, product_id, match_method
    union all
    select 'Shopify', sale_date, product_id, match_method, count(*), sum(quantity), sum(amount_mxn),
           count(*) filter (where amount_mxn is not null and effective_unit_cost_mxn is not null
                            and match_method <> 'unmatched'),
           sum(quantity) filter (where amount_mxn is not null and effective_unit_cost_mxn is not null
                                and match_method <> 'unmatched'),
           sum(amount_mxn) filter (where amount_mxn is not null and effective_unit_cost_mxn is not null
                                  and match_method <> 'unmatched'),
           count(*) filter (where match_method = 'unmatched'), count(*) filter (where amount_mxn is null),
           count(*) filter (where effective_unit_cost_mxn is null),
           count(*) filter (where amount_mxn is null or effective_unit_cost_mxn is null
                            or match_method = 'unmatched')
    from {{ ref('fct_sales') }} where source_name = 'Shopify'
    group by sale_date, product_id, match_method
)
select *, now() as built_at, 'business_metrics.v1'::text as logic_version
from source_rows
