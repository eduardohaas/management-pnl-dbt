-- Monthly ledger totals per company and P&L line.
select
    gl.company_id,
    gl.reference_month,
    gl.account_code,
    map.pnl_line,
    sum(gl.amount_brl) as amount_brl
from {{ ref('stg_erp__general_ledger') }} as gl
inner join {{ ref('account_pnl_mapping') }} as map
    on gl.account_code = map.account_code
group by all
