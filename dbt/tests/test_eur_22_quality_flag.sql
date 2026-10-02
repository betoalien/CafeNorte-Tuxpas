select * from {{ ref('stg_exchange_rates') }}
where currency = 'EUR' and rate_to_mxn = 22.0 and fx_quality_flag <> 'suspected_truncation'
