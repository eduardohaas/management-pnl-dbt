-- Every BRL spent by the shared service center must land on some company, every month.
with spent as (
    select l.reference_month, sum(l.amount_brl) as amount
    from {{ ref('int_ledger_by_pnl_line') }} as l
    inner join {{ ref('stg_erp__companies') }} as c using (company_id)
    where c.is_shared_service_center
    group by all
),

allocated as (
    select reference_month, sum(allocated_amount_brl) as amount
    from {{ ref('int_shared_costs_allocated') }}
    group by all
)

select spent.reference_month, spent.amount as spent, allocated.amount as allocated
from spent
left join allocated using (reference_month)
where abs(spent.amount - coalesce(allocated.amount, 0)) > 0.01
