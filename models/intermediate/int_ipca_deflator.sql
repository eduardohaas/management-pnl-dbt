-- Factor that brings a nominal amount of a given month to the prices of the base month.
with chained as (
    select
        reference_month,
        -- Cumulative price index: product of (1 + monthly rate), computed via logs.
        exp(sum(ln(1 + ipca_rate)) over (order by reference_month)) as price_index
    from {{ ref('stg_bcb__ipca_monthly') }}
),

base as (
    select price_index as base_index
    from chained
    where reference_month = '{{ var("real_terms_base_month") }}'::date
)

select
    chained.reference_month,
    chained.price_index,
    base.base_index / chained.price_index as to_base_month_factor
from chained
cross join base
