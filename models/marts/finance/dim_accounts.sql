select
    coa.account_code,
    coa.account_name,
    coa.nature,
    map.pnl_line,
    lines.pnl_line_label,
    lines.pnl_line_order
from {{ ref('stg_erp__chart_of_accounts') }} as coa
left join {{ ref('account_pnl_mapping') }} as map using (account_code)
left join {{ ref('pnl_lines') }} as lines using (pnl_line)
