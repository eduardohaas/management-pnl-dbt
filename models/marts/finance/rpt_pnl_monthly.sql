-- One row per company and month with the classic P&L subtotals and margins.
{% set lines = ['gross_revenue', 'deductions', 'cost_of_sales', 'selling_expenses', 'personnel_expenses',
                'administrative_expenses', 'shared_service_allocation', 'financial_result', 'income_tax'] %}

with pivoted as (
    select
        company_id,
        reference_month,
        {% for line in lines -%}
        sum(case when pnl_line = '{{ line }}' then amount_brl else 0 end) as {{ line }}{{ "," if not loop.last }}
        {% endfor %}
    from {{ ref('fct_management_pnl') }}
    group by all
),

subtotals as (
    select
        *,
        gross_revenue + deductions                                              as net_revenue,
        gross_revenue + deductions + cost_of_sales                              as gross_profit,
        gross_revenue + deductions + cost_of_sales + selling_expenses
            + personnel_expenses + administrative_expenses
            + shared_service_allocation                                         as operating_result
    from pivoted
)

select
    *,
    operating_result + financial_result                                         as earnings_before_tax,
    operating_result + financial_result + income_tax                            as net_income,
    round(gross_profit / nullif(net_revenue, 0), 4)                             as gross_margin,
    round(operating_result / nullif(net_revenue, 0), 4)                         as operating_margin,
    round((operating_result + financial_result + income_tax) / nullif(net_revenue, 0), 4) as net_margin
from subtotals
