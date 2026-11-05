-- Share of each operating company in each allocation driver, per month.
with companies as (
    select company_id from {{ ref('stg_erp__companies') }} where not is_shared_service_center
),

headcount as (
    select hc.company_id, hc.reference_month, hc.headcount::double as driver_value
    from {{ ref('stg_hr__headcount') }} as hc
    inner join companies using (company_id)
),

net_revenue as (
    select l.company_id, l.reference_month, sum(l.amount_brl)::double as driver_value
    from {{ ref('int_ledger_by_pnl_line') }} as l
    inner join companies using (company_id)
    where l.pnl_line in ('gross_revenue', 'deductions')
    group by all
),

drivers as (
    select 'headcount' as allocation_driver, * from headcount
    union all
    select 'net_revenue' as allocation_driver, * from net_revenue
)

select
    allocation_driver,
    company_id,
    reference_month,
    driver_value,
    driver_value / sum(driver_value) over (partition by allocation_driver, reference_month) as driver_share
from drivers
