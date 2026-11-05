select
    company_id,
    company_name,
    segment,
    is_shared_service_center
from {{ source('erp', 'erp_companies') }}
