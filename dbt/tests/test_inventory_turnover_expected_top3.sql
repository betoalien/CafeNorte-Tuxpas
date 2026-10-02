with expected as (
    select * from (values
        ('ERP-PROV-MX-057-C', 1.362::numeric, 652::numeric, 478.74::numeric),
        ('ERP-PROV-MX-012-B', 1.226::numeric, null::numeric, null::numeric),
        ('ERP-PROV-MX-041-D', 1.201::numeric, null::numeric, null::numeric)
    ) as t(product_id, expected_ratio, expected_units, expected_inventory)
), actual as (
    select product_id, inventory_turnover_ratio, units_sold, average_valid_inventory_units
    from {{ ref('mart_inventory_turnover_top10') }}
    where ranking <= 3
)
select a.*
from actual a
join expected e using (product_id)
where abs(a.inventory_turnover_ratio - e.expected_ratio) > 0.001
   or (e.expected_units is not null and a.units_sold <> e.expected_units)
   or (e.expected_inventory is not null and abs(a.average_valid_inventory_units - e.expected_inventory) > 0.01)
union all
select e.product_id, null, null, null
from expected e
left join actual a using (product_id)
where a.product_id is null
