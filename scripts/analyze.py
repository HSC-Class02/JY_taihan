"""Normalize OpenDART JSON and calculate dashboard financial ratios."""
from __future__ import annotations
import csv, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
ACCOUNTS = json.loads((ROOT / "config" / "accounts.json").read_text(encoding="utf-8"))
def number(value):
    try: return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError): return None
def pick(rows, candidates):
    for candidate in candidates:
        for r in rows:
            if candidate in (r.get("account_id"), r.get("account_nm")): return number(r.get("thstrm_amount"))
    return None
def ratio(a,b,m=100): return round(a/b*m,2) if a is not None and b not in (None,0) else None
def main():
    records=[]
    for path in sorted((ROOT/"data/raw").glob("*.json")):
        doc=json.loads(path.read_text(encoding="utf-8")); rows=doc.get("list", [])
        if not rows: continue
        values={key:pick(rows, candidates) for key,candidates in ACCOUNTS.items()}
        values.update(year=doc["year"], report_code=doc["reprt_code"], category=doc["category"], period=f'{doc["year"]}-{doc["reprt_code"]}')
        records.append(values)
    records.sort(key=lambda x:(x["year"], x["report_code"]))
    for i,r in enumerate(records):
        previous=next((x for x in records[:i][::-1] if x["report_code"]==r["report_code"]), None)
        previous_revenue=(previous or {}).get("revenue")
        r["revenue_growth_pct"]=ratio(r["revenue"]-previous_revenue, previous_revenue) if r["revenue"] is not None and previous_revenue is not None else None
        r.update(gross_margin_pct=ratio(r["gross_profit"],r["revenue"]), operating_margin_pct=ratio(r["operating_income"],r["revenue"]), net_margin_pct=ratio(r["net_income"],r["revenue"]), roa_pct=ratio(r["net_income"],r["total_assets"]), roe_pct=ratio(r["net_income"],r["total_equity"]), current_ratio_pct=ratio(r["current_assets"],r["current_liabilities"]), quick_ratio_pct=ratio((r["current_assets"] or 0)-(r["inventory"] or 0),r["current_liabilities"]), debt_to_equity_pct=ratio(r["total_liabilities"],r["total_equity"]), inventory_turnover=ratio(r["cost_of_sales"],r["inventory"],1), dso=ratio(r["receivables"],r["revenue"],365), cfo_conversion_pct=ratio(r["operating_cash_flow"],r["net_income"]), free_cash_flow=(r["operating_cash_flow"] or 0)-abs(r["capex"] or 0) if r["operating_cash_flow"] is not None else None)
    fields=sorted({k for r in records for k in r})
    (ROOT/"data").mkdir(exist_ok=True)
    with (ROOT/"data/financial_summary.csv").open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fields); writer.writeheader(); writer.writerows(records)
    dashboard={"company":"대한전선", "corp_code":"00105929", "updated_at":__import__("datetime").datetime.now().isoformat(timespec="seconds"), "records":records}
    (ROOT/"data/dashboard.json").write_text(json.dumps(dashboard,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__ == "__main__": main()
