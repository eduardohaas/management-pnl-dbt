-- Shared service center costs pushed down to operating companies.
-- Which driver applies to each cost account is a business rule kept in seeds/allocation_rules.csv.
with shared_costs as (
    select l.reference_month, l.account_code, l.amount_brl
    from {{ ref('int_ledger_by_pnl_line') }} as l
    inner join {{ ref('stg_erp__companies') }} as c using (company_id)
    where c.is_shared_service_center
)

select
    d.company_id,
    s.reference_month,
    s.account_code,
    r.allocation_driver,
    d.driver_share,
    s.amount_brl * d.driver_share as allocated_amount_brl
from shared_costs as s
inner join {{ ref('allocation_rules') }} as r
    on s.account_code = r.account_code
inner join {{ ref('int_allocation_drivers') }} as d
    on r.allocation_driver = d.allocation_driver
   and s.reference_month = d.reference_month
