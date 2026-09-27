"""Fetch Taihan Electric Wire periodic filings and financial statements from OpenDART."""
from __future__ import annotations
import argparse, datetime as dt, json, os, pathlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORP_CODE = "00105929"  # Taihan Electric Wire
REPORTS = {"11011": "annual", "11012": "half_year", "11013": "quarterly", "11014": "quarterly"}

def api_key():
    key = os.getenv("DART_API_KEY", "")
    if not key and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("DART_API_KEY="): key = line.split("=", 1)[1].strip()
    if not key: raise SystemExit("DART_API_KEY가 없습니다. API_KEY_SETUP.txt를 확인하세요.")
    return key

def get_json(path, params):
    response = requests.get("https://opendart.fss.or.kr/api/" + path, params=params, timeout=60)
    response.raise_for_status(); return response.json()

def main(start_year: int):
    key = api_key(); raw = ROOT / "data" / "raw"; raw.mkdir(parents=True, exist_ok=True)
    source = ROOT / "reports" / "source"; source.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().strftime("%Y%m%d"); years = list(range(start_year, dt.date.today().year + 1))

    def listing_for(year):
        return get_json("list.json", {"crtfc_key":key,"corp_code":CORP_CODE,"bgn_de":f"{year}0101","end_de":today,"pblntf_ty":"A","page_count":100}).get("list", [])

    disclosures = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for rows in pool.map(listing_for, years):
            disclosures.extend(item for item in rows if any(x in item.get("report_nm", "") for x in ("사업보고서", "반기보고서", "분기보고서")) and "정정" not in item.get("report_nm", ""))

    def download_document(item):
        out = source / f'{item["rcept_no"]}.zip'
        if out.exists(): return
        response = requests.get("https://opendart.fss.or.kr/api/document.xml", params={"crtfc_key":key,"rcept_no":item["rcept_no"]}, timeout=60)
        response.raise_for_status()
        if response.content.startswith(b"PK"): out.write_bytes(response.content)

    def fetch_financial(task):
        year, code, category, out = task
        data = get_json("fnlttSinglAcntAll.json", {"crtfc_key":key,"corp_code":CORP_CODE,"bsns_year":str(year),"reprt_code":code,"fs_div":"CFS"})
        if data.get("status") != "000":
            data = get_json("fnlttSinglAcntAll.json", {"crtfc_key":key,"corp_code":CORP_CODE,"bsns_year":str(year),"reprt_code":code,"fs_div":"OFS"})
        data.update({"year":year,"reprt_code":code,"category":category,"corp_code":CORP_CODE})
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    financial_tasks = [(year, code, category, raw / f"taihan_{year}_{code}.json") for year in years for code, category in REPORTS.items() if not (raw / f"taihan_{year}_{code}.json").exists()]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(fetch_financial, financial_tasks))
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(download_document, disclosures))
    (ROOT / "reports" / "opendart_disclosures.json").write_text(json.dumps(disclosures, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--start-year", type=int, default=2010)
    main(parser.parse_args().start_year)
