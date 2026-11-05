-- Management P&L (DRE gerencial) per operating company, month and P&L line.
-- Shared service center costs leave the center and land on the companies as one allocation line.
with own_results as (
    select l.company_id, l.reference_month, l.pnl_line, l.amount_brl::double as amount_brl
    from {{ ref('int_ledger_by_pnl_line') }} as l
    inner join {{ ref('stg_erp__companies') }} as c using (company_id)
    where not c.is_shared_service_center
),

allocations as (
    select
        company_id,
        reference_month,
        'shared_service_allocation' as pnl_line,
        allocated_amount_brl as amount_brl
    from {{ ref('int_shared_costs_allocated') }}
),

unioned as (
    select * from own_results
    union all
    select * from allocations
),

aggregated as (
    select company_id, reference_month, pnl_line, sum(amount_brl) as amount_brl
    from unioned
    group by all
)

select
    agg.company_id,
    agg.reference_month,
    agg.pnl_line,
    lines.pnl_line_label,
    lines.pnl_line_order,
    round(agg.amount_brl, 2)                               as amount_brl,
    round(agg.amount_brl * defl.to_base_month_factor, 2)   as amount_brl_real
from aggregated as agg
inner join {{ ref('pnl_lines') }} as lines using (pnl_line)
left join {{ ref('int_ipca_deflator') }} as defl using (reference_month)
