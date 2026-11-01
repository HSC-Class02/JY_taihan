"""Normalize OpenDART JSON and calculate dashboard financial ratios."""
from __future__ import annotations

import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORP_CODE = "00113207"  # 대한전선(주), 종목코드 001440
ACCOUNTS = json.loads((ROOT / "config" / "accounts.json").read_text(encoding="utf-8"))
REPORT_ORDER = {"11013": 1, "11012": 2, "11014": 3, "11011": 4}


def number(value):
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def pick(rows, candidates):
    for candidate in candidates:
        for row in rows:
            if candidate in (row.get("account_id"), row.get("account_nm")):
                value = number(row.get("thstrm_amount"))
                if value is not None:
                    return value
    return None


def ratio(a, b, multiplier=100):
    return round(a / b * multiplier, 2) if a is not None and b not in (None, 0) else None


def main():
    records = []
    raw_dir = ROOT / "data" / "raw"
    for path in sorted(raw_dir.glob("taihan_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        # Ignore stale API error payloads or empty response files.
        if str(doc.get("status")) != "000" or not doc.get("list"):
            continue
        if str(doc.get("corp_code")) != CORP_CODE:
            raise RuntimeError(
                f"기업 코드 불일치: {path.name}에 {doc.get('corp_code')}가 있습니다. "
                "다른 기업의 데이터가 섞이지 않도록 분석을 중단합니다."
            )

        rows = doc.get("list", [])
        values = {key: pick(rows, candidates) for key, candidates in ACCOUNTS.items()}
        values.update(
            year=int(doc["year"]),
            report_code=str(doc["reprt_code"]),
            category=doc["category"],
            period=f'{doc["year"]}-{doc["reprt_code"]}',
        )
        records.append(values)

    records.sort(
        key=lambda row: (row["year"], REPORT_ORDER.get(row["report_code"], 99))
    )
    if not records:
        raise RuntimeError(
            "분석할 유효 재무제표가 없습니다. "
            "수집 단계의 OpenDART 오류를 확인했습니다. 기존 대시보드 데이터를 보존합니다."
        )

    for index, row in enumerate(records):
        previous = next(
            (
                item for item in records[:index][::-1]
                if item["report_code"] == row["report_code"]
            ),
            None,
        )
        previous_revenue = (previous or {}).get("revenue")
        row["revenue_growth_pct"] = (
            ratio(row["revenue"] - previous_revenue, previous_revenue)
            if row["revenue"] is not None and previous_revenue is not None
            else None
        )
        row.update(
            gross_margin_pct=ratio(row["gross_profit"], row["revenue"]),
            operating_margin_pct=ratio(row["operating_income"], row["revenue"]),
            net_margin_pct=ratio(row["net_income"], row["revenue"]),
            roa_pct=ratio(row["net_income"], row["total_assets"]),
            roe_pct=ratio(row["net_income"], row["total_equity"]),
            current_ratio_pct=ratio(row["current_assets"], row["current_liabilities"]),
            quick_ratio_pct=ratio(
                (row["current_assets"] or 0) - (row["inventory"] or 0),
                row["current_liabilities"],
            ),
            debt_to_equity_pct=ratio(row["total_liabilities"], row["total_equity"]),
            inventory_turnover=ratio(row["cost_of_sales"], row["inventory"], 1),
            dso=ratio(row["receivables"], row["revenue"], 365),
            cfo_conversion_pct=ratio(row["operating_cash_flow"], row["net_income"]),
            free_cash_flow=(
                row["operating_cash_flow"] - abs(row["capex"] or 0)
                if row["operating_cash_flow"] is not None
                else None
            ),
        )

    fields = sorted({key for row in records for key in row})
    (ROOT / "data").mkdir(exist_ok=True)
    with (ROOT / "data" / "financial_summary.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    from datetime import datetime

    dashboard = {
        "company": "대한전선",
        "corp_code": CORP_CODE,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "records": records,
    }
    (ROOT / "data" / "dashboard.json").write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"분석 완료: 대한전선 재무자료 {len(records)}건")


if __name__ == "__main__":
    main()
