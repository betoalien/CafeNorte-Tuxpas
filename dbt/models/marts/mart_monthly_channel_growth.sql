with months as (
    select date_trunc('month', day)::date as month_start
    from generate_series(({{ var('anchor_date') }}::date - interval '12 months' + interval '1 day')::date, date_trunc('month', {{ var('anchor_date') }}::date), interval '1 month') day
), channels as (select channel from {{ ref('dim_channel') }}), grid as (
    select c.channel, m.month_start from channels c cross join months m
), totals as (
    select channel, date_trunc('month', sale_date)::date as month_start,
           sum(amount_mxn) as sales_mxn
    from {{ ref('fct_sales') }}
    where sale_date between ({{ var('anchor_date') }}::date - interval '12 months' + interval '1 day') and {{ var('anchor_date') }}::date
    group by channel, date_trunc('month', sale_date)::date
), monthly_values as (
    select g.channel, g.month_start, t.sales_mxn,
           lag(t.sales_mxn) over (partition by g.channel order by g.month_start) as previous_sales_mxn
    from grid g left join totals t using (channel, month_start)
)
select channel, month_start, sales_mxn, previous_sales_mxn,
       case when previous_sales_mxn is null then null
            when previous_sales_mxn = 0 then null
            else sales_mxn / previous_sales_mxn - 1 end as mom_growth_pct,
       case when month_start = ({{ var('anchor_date') }}::date - interval '12 months' + interval '1 day')::date then 'no_prior_month'
            when previous_sales_mxn = 0 then 'prior_month_zero' end as null_reason,
       to_char({{ var('anchor_date') }}::date - interval '12 months' + interval '1 day', 'YYYY-MM') || '/' || to_char({{ var('anchor_date') }}::date, 'YYYY-MM') as period, now() as built_at,
       'business_metrics.v1'::text as logic_version
from monthly_values
