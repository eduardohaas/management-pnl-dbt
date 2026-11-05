-- Allocation moves costs between companies but never creates or destroys money:
-- the group's net income in the P&L must equal the raw ledger result, month by month.
with pnl as (
    select reference_month, sum(net_income) as net_income
    from {{ ref('rpt_pnl_monthly') }}
    group by all
),

ledger as (
    select reference_month, sum(amount_brl) as net_income
    from {{ ref('stg_erp__general_ledger') }}
    group by all
)

select pnl.reference_month, pnl.net_income as pnl_net_income, ledger.net_income as ledger_net_income
from pnl
full outer join ledger using (reference_month)
where abs(coalesce(pnl.net_income, 0) - coalesce(ledger.net_income, 0)) > 1
