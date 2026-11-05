"""
Incremental load of Brazil's monthly inflation (IPCA, SGS series 433) from the
Central Bank of Brazil open data API into `raw.bcb_ipca_monthly`.

- First run: full backfill from START_DATE.
- Next runs: only months after the latest one already loaded (idempotent upsert).
- Retries with backoff, because public APIs time out.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import requests

SERIES_ID = 433  # IPCA - monthly % change
START_DATE = date(2024, 1, 1)
URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados"
WAREHOUSE = Path(__file__).resolve().parents[1] / "warehouse.duckdb"


def fetch(start: date, end: date, attempts: int = 4) -> list[dict]:
    params = {"formato": "json", "dataInicial": start.strftime("%d/%m/%Y"), "dataFinal": end.strftime("%d/%m/%Y")}
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(URL.format(series=SERIES_ID), params=params, timeout=30)
            if resp.status_code == 404:  # the API answers 404 when there is no data in the window
                return []
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == attempts:
                raise
            wait = 2 ** attempt
            print(f"BCB API attempt {attempt} failed ({exc}); retrying in {wait}s")
            time.sleep(wait)
    return []


def main() -> None:
    con = duckdb.connect(str(WAREHOUSE))
    con.execute("create schema if not exists raw")
    con.execute("""create table if not exists raw.bcb_ipca_monthly (
        reference_date date primary key, ipca_pct decimal(8, 4), loaded_at timestamp)""")

    last = con.execute("select max(reference_date) from raw.bcb_ipca_monthly").fetchone()[0]
    start = (last + timedelta(days=32)).replace(day=1) if last else START_DATE
    end = date.today()
    if start > end:
        print("IPCA already up to date")
        return

    rows = fetch(start, end)
    loaded_at = datetime.now()
    records = [(datetime.strptime(r["data"], "%d/%m/%Y").date(), float(r["valor"]), loaded_at) for r in rows]
    if records:
        con.executemany(
            """insert into raw.bcb_ipca_monthly values (?, ?, ?)
               on conflict (reference_date) do update set ipca_pct = excluded.ipca_pct, loaded_at = excluded.loaded_at""",
            records,
        )
    total = con.execute("select count(*) from raw.bcb_ipca_monthly").fetchone()[0]
    print(f"IPCA: {len(records)} new month(s) loaded from {start:%Y-%m}; {total} months in warehouse")
    con.close()


if __name__ == "__main__":
    main()
