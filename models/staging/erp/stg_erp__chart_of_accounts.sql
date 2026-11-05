select
    trim(account_code) as account_code,
    account_name,
    nature
from {{ source('erp', 'erp_chart_of_accounts') }}
