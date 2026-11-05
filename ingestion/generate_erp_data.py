"""
Generate a synthetic ERP extract for a fictional Brazilian group of companies
and load it into the `raw` schema of the local DuckDB warehouse.

The data is deterministic (fixed seed) and intentionally carries the kind of
mess real ERP exports have, so the staging layer has real work to do:
  - general ledger lines re-exported twice (duplicate entry_id)
  - dates as 'DD/MM/YYYY' strings
  - account codes with stray whitespace
  - debit/credit columns instead of a signed amount
"""

from __future__ import annotations

import random
from datetime import date
from pathlib import Path

import duckdb

SEED = 42
WAREHOUSE = Path(__file__).resolve().parents[1] / "warehouse.duckdb"
MONTHS = [date(y, m, 1) for y in (2024, 2025) for m in range(1, 13)]

COMPANIES = [
    # id, name, segment, is_shared_service_center
    ("C00", "Grupo Sul - Shared Service Center", "Shared services", True),
    ("C01", "Sul Alimentos Industria", "Food manufacturing", False),
    ("C02", "Sul Distribuidora", "Wholesale distribution", False),
    ("C03", "Sul Logistica", "Logistics services", False),
]

# account_code, account_name, nature (credit = revenue-like, debit = expense-like)
ACCOUNTS = [
    ("3.1.01", "Gross sales revenue", "credit"),
    ("3.1.02", "Gross service revenue", "credit"),
    ("3.2.01", "Sales taxes", "debit"),
    ("3.2.02", "Returns and rebates", "debit"),
    ("4.1.01", "Cost of goods sold", "debit"),
    ("4.1.02", "Cost of services rendered", "debit"),
    ("5.1.01", "Freight on sales", "debit"),
    ("5.1.02", "Marketing", "debit"),
    ("5.2.01", "Payroll and benefits", "debit"),
    ("5.3.01", "Rent and facilities", "debit"),
    ("5.3.02", "IT and software", "debit"),
    ("5.3.03", "Third-party services", "debit"),
    ("6.1.01", "Financial income", "credit"),
    ("6.1.02", "Financial expenses", "debit"),
    ("7.1.01", "Income tax and social contribution", "debit"),
]

# Monthly baseline (BRL) per company and account. Shared service center only has overhead.
BASELINE = {
    "C01": {"3.1.01": 4_200_000, "3.2.01": 760_000, "3.2.02": 85_000, "4.1.01": 2_100_000,
            "5.1.01": 140_000, "5.1.02": 60_000, "5.2.01": 330_000, "5.3.01": 70_000,
            "5.3.02": 20_000, "5.3.03": 30_000, "6.1.01": 25_000, "6.1.02": 60_000},
    "C02": {"3.1.01": 2_900_000, "3.2.01": 520_000, "3.2.02": 110_000, "4.1.01": 1_650_000,
            "5.1.01": 110_000, "5.1.02": 30_000, "5.2.01": 150_000, "5.3.01": 45_000,
            "5.3.02": 12_000, "5.3.03": 18_000, "6.1.01": 12_000, "6.1.02": 45_000},
    "C03": {"3.1.02": 1_150_000, "3.2.01": 125_000, "4.1.02": 520_000,
            "5.2.01": 200_000, "5.3.01": 30_000, "5.3.02": 12_000, "5.3.03": 15_000,
            "6.1.01": 4_000, "6.1.02": 22_000},
    "C00": {"5.2.01": 190_000, "5.3.01": 35_000, "5.3.02": 70_000, "5.3.03": 45_000},
}

HEADCOUNT_BASE = {"C00": 38, "C01": 210, "C02": 95, "C03": 120}

# Food demand peaks at year end; logistics follows.
SEASONALITY = {1: .92, 2: .90, 3: 1.0, 4: .97, 5: 1.0, 6: .98, 7: .99, 8: 1.01, 9: 1.0, 10: 1.04, 11: 1.08, 12: 1.15}
REVENUE_DRIVEN = {"3.1.01", "3.1.02", "3.2.01", "3.2.02", "4.1.01", "4.1.02", "5.1.01"}


def build_ledger(rng: random.Random) -> list[tuple]:
    rows: list[tuple] = []
    entry_id = 100_000
    nature = {code: nat for code, _, nat in ACCOUNTS}
    for i, month in enumerate(MONTHS):
        growth = 1 + 0.006 * i  # ~7% a year
        for company, accounts in BASELINE.items():
            for code, base in accounts.items():
                factor = growth * (SEASONALITY[month.month] if code in REVENUE_DRIVEN else 1)
                total = base * factor * rng.uniform(0.95, 1.05)
                # Split each monthly total in a few postings, like a real ledger.
                parts = rng.randint(2, 5)
                weights = [rng.random() for _ in range(parts)]
                for w in weights:
                    entry_id += 1
                    amount = round(total * w / sum(weights), 2)
                    day = rng.randint(1, 28)
                    posted = date(month.year, month.month, day).strftime("%d/%m/%Y")
                    # Stray whitespace on ~3% of account codes.
                    account = f" {code} " if rng.random() < 0.03 else code
                    debit, credit = (amount, 0.0) if nature[code] == "debit" else (0.0, amount)
                    rows.append((entry_id, company, account, posted, debit, credit, f"Posting {entry_id}"))
        # Income tax: ~ flat monthly provision per operating company.
        for company, provision in (("C01", 95_000), ("C02", 40_000), ("C03", 28_000)):
            entry_id += 1
            posted = date(month.year, month.month, 28).strftime("%d/%m/%Y")
            amount = round(provision * growth * rng.uniform(0.9, 1.1), 2)
            rows.append((entry_id, company, "7.1.01", posted, amount, 0.0, "Income tax provision"))

    # The ERP re-exports ~1% of lines (same entry_id, later extraction).
    duplicates = rng.sample(rows, k=len(rows) // 100)
    return rows + duplicates


def build_headcount(rng: random.Random) -> list[tuple]:
    rows = []
    for i, month in enumerate(MONTHS):
        for company, base in HEADCOUNT_BASE.items():
            rows.append((company, month.strftime("%Y-%m"), int(base * (1 + 0.004 * i) + rng.randint(-3, 3))))
    return rows


def main() -> None:
    rng = random.Random(SEED)
    con = duckdb.connect(str(WAREHOUSE))
    con.execute("create schema if not exists raw")

    con.execute("create or replace table raw.erp_companies (company_id varchar, company_name varchar, segment varchar, is_shared_service_center boolean)")
    con.executemany("insert into raw.erp_companies values (?, ?, ?, ?)", COMPANIES)

    con.execute("create or replace table raw.erp_chart_of_accounts (account_code varchar, account_name varchar, nature varchar)")
    con.executemany("insert into raw.erp_chart_of_accounts values (?, ?, ?)", ACCOUNTS)

    ledger = build_ledger(rng)
    con.execute("""create or replace table raw.erp_general_ledger (
        entry_id integer, company_id varchar, account_code varchar, posting_date varchar,
        debit decimal(18, 2), credit decimal(18, 2), description varchar)""")
    con.executemany("insert into raw.erp_general_ledger values (?, ?, ?, ?, ?, ?, ?)", ledger)

    con.execute("create or replace table raw.hr_headcount (company_id varchar, reference_month varchar, headcount integer)")
    con.executemany("insert into raw.hr_headcount values (?, ?, ?)", build_headcount(rng))

    print(f"ERP extract loaded: {len(ledger):,} ledger lines, {len(COMPANIES)} companies, {len(MONTHS)} months -> {WAREHOUSE.name}")
    con.close()


if __name__ == "__main__":
    main()
