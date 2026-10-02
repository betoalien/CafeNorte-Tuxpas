with expected(source_name, match_method, expected_count) as (
    values
        ('POS', 'explicit', 74141),
        ('POS', 'product_number', 6217),
        ('POS', 'product_number_null_erp', 6132),
        ('Shopify', 'explicit', 6959),
        ('Shopify', 'product_number', 1849),
        ('Shopify', 'product_number_null_erp', 1139)
), actual as (
    select source_name, match_method, count(*) as actual_count
    from {{ ref('int_product_identity') }}
    group by source_name, match_method
)
select e.* from expected e left join actual a using (source_name, match_method)
where coalesce(a.actual_count, 0) <> e.expected_count
