select
    reference_date::date      as reference_month,
    ipca_pct::double / 100     as ipca_rate
from {{ source('bcb', 'bcb_ipca_monthly') }}
