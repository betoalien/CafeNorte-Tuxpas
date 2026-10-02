select * from {{ ref('mart_source_reconciliation') }}
where input_rows <> certified_rows + excluded_rows
