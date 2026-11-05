with source as (
    select * from {{ source('erp', 'erp_general_ledger') }}
),

deduplicated as (
    -- The ERP re-exports some postings; keep one row per entry_id.
    select *
    from source
    qualify row_number() over (partition by entry_id order by posting_date) = 1
)

select
    entry_id,
    company_id,
    trim(account_code)                                          as account_code,
    strptime(posting_date, '%d/%m/%Y')::date                    as posting_date,
    date_trunc('month', strptime(posting_date, '%d/%m/%Y'))::date as reference_month,
    -- Result-account sign convention: revenue positive, costs and expenses negative.
    (credit - debit)::decimal(18, 2)                            as amount_brl,
    description
from deduplicated
