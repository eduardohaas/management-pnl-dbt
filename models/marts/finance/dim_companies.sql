select
    company_id,
    company_name,
    segment,
    is_shared_service_center
from {{ ref('stg_erp__companies') }}
