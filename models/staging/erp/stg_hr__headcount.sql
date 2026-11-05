select
    company_id,
    strptime(reference_month, '%Y-%m')::date as reference_month,
    headcount
from {{ source('erp', 'hr_headcount') }}
