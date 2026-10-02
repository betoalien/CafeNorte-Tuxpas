with detail as (
    select case when d.channel_type = 'POS' then 'FISICO' else 'ECOMMERCE' end as channel_type,
           g.month_start, sum(g.sales_mxn) as sales_mxn
    from {{ ref('mart_monthly_channel_growth') }} g
    join {{ ref('dim_channel') }} d using (channel)
    group by 1, 2
), aggregate as (
    select channel_type, month_start, sales_mxn
    from {{ ref('mart_monthly_channel_type_growth') }}
)
select * from (
    select channel_type, month_start from aggregate
    group by 1, 2 having count(*) <> 1
    union all
    select channel_type, month_start from aggregate
    where not exists (
        select 1 from detail d
        where d.channel_type = aggregate.channel_type
          and d.month_start = aggregate.month_start
          and round(d.sales_mxn, 2) = round(aggregate.sales_mxn, 2)
    )
    union all
    select channel_type, month_start from detail
    where not exists (
        select 1 from aggregate a
        where a.channel_type = detail.channel_type and a.month_start = detail.month_start
    )
) mismatches
