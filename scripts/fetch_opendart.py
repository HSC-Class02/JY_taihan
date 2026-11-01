"""Fetch Taihan Electric Wire filings and financial statements from OpenDART.

The company code is validated against OpenDART before any collection starts.
API errors are raised explicitly so an invalid key or company code can never
silently create an apparently successful but empty dashboard.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORP_CODE = "00113207"  # 대한전선(주), 종목코드 001440
REPORTS = {
    "11011": "annual",
    "11012": "half_year",
    "11013": "quarterly",
    "11014": "quarterly",
}
API_BASE = "https://opendart.fss.or.kr/api/"
MAX_WORKERS = 4


def api_key() -> str:
    key = os.getenv("DART_API_KEY", "").strip()
    if not key and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DART_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not key:
        raise SystemExit("DART_API_KEY가 없습니다. Repository Secrets의 이름을 확인하세요.")
    if len(key) != 40:
        raise SystemExit(
            f"DART_API_KEY 길이가 {len(key)}자입니다. OpenDART 인증키 40자리인지 확인하세요."
        )
    return key


def get_json(path: str, params: dict[str, Any], *, allow_no_data: bool = True) -> dict[str, Any]:
    """Call OpenDART and distinguish 'no data' from authentication/API errors."""
    try:
        response = requests.get(API_BASE + path, params=params, timeout=(15, 60))
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"OpenDART {path} HTTP 요청 실패: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"OpenDART {path}가 유효한 JSON을 반환하지 않았습니다.") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"OpenDART {path} 응답 형식이 올바르지 않습니다.")

    status = str(payload.get("status", ""))
    if status == "000":
        return payload
    if status == "013" and allow_no_data:
        return payload

    message = payload.get("message", "응답 메시지 없음")
    hints = {
        "010": "인증키가 등록되지 않았습니다. DART_API_KEY Secret을 확인하세요.",
        "011": "인증키가 사용 중지되었습니다. OpenDART에서 키 상태를 확인하세요.",
        "012": "API 접근 IP가 허용되지 않았습니다.",
        "020": "OpenDART 요청 한도를 초과했습니다. 잠시 후 다시 실행하세요.",
        "100": "요청 파라미터가 올바르지 않습니다.",
        "901": "인증키 보유기간이 만료되었습니다.",
    }
    detail = hints.get(status, str(message))
    raise RuntimeError(f"OpenDART {path} 오류(status={status}): {detail} / {message}")


def verify_company(key: str) -> None:
    company = get_json(
        "company.json",
        {"crtfc_key": key, "corp_code": CORP_CODE},
        allow_no_data=False,
    )
    name = str(company.get("corp_name") or company.get("stock_name") or "")
    if "대한전선" not in name:
        raise RuntimeError(
            f"기업 코드 검증 실패: {CORP_CODE} 조회 결과가 '{name}'입니다. "
            "수집을 중단해 다른 기업의 데이터가 저장되지 않도록 했습니다."
        )
    print(f"기업 코드 확인: {name} ({CORP_CODE})")


def listing_for(year: int, key: str) -> list[dict[str, Any]]:
    params = {
        "crtfc_key": key,
        "corp_code": CORP_CODE,
        "bgn_de": f"{year}0101",
        "end_de": dt.date.today().strftime("%Y%m%d"),
        "pblntf_ty": "A",
        "page_no": 1,
        "page_count": 100,
        "sort": "date",
        "sort_mth": "asc",
    }
    first = get_json("list.json", params)
    rows = list(first.get("list") or [])
    total_pages = int(first.get("total_page") or 1)
    for page_no in range(2, total_pages + 1):
        page_params = {**params, "page_no": page_no}
        page = get_json("list.json", page_params)
        rows.extend(page.get("list") or [])
    return [
        item for item in rows
        if any(label in str(item.get("report_nm", "")) for label in ("사업보고서", "반기보고서", "분기보고서"))
        and "철회" not in str(item.get("report_nm", ""))
    ]


def fetch_financial(task: tuple[int, str, str, pathlib.Path, str]) -> pathlib.Path | None:
    year, report_code, category, output, key = task
    params = {
        "crtfc_key": key,
        "corp_code": CORP_CODE,
        "bsns_year": str(year),
        "reprt_code": report_code,
        "fs_div": "CFS",
    }
    fs_div_used = "CFS"
    data = get_json("fnlttSinglAcntAll.json", params)
    if str(data.get("status")) == "013":
        fs_div_used = "OFS"
        data = get_json(
            "fnlttSinglAcntAll.json",
            {**params, "fs_div": fs_div_used},
        )
    if str(data.get("status")) == "013" or not data.get("list"):
        return None

    data.update({
        "year": year,
        "reprt_code": report_code,
        "category": category,
        "corp_code": CORP_CODE,
        "fs_div_used": fs_div_used,
    })
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def valid_cached_file(path: pathlib.Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return str(payload.get("status")) == "000" and bool(payload.get("list"))
    except (OSError, ValueError, AttributeError):
        return False


def download_document(item: dict[str, Any], key: str, output_dir: pathlib.Path) -> None:
    receipt_no = str(item.get("rcept_no", ""))
    if len(receipt_no) != 14:
        return
    output = output_dir / f"{receipt_no}.zip"
    if output.exists():
        return
    try:
        response = requests.get(
            API_BASE + "document.xml",
            params={"crtfc_key": key, "rcept_no": receipt_no},
            timeout=(15, 60),
        )
        response.raise_for_status()
        if response.content.startswith(b"PK"):
            output.write_bytes(response.content)
    except requests.RequestException as exc:
        # The dashboard is based on structured financial data. A failed
        # optional source-document download must not discard valid accounts.
        print(f"원문 ZIP 다운로드 건너뜀({receipt_no}): {exc}")


def main(start_year: int) -> None:
    key = api_key()
    verify_company(key)

    raw_dir = ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    source_dir = ROOT / "reports" / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    # Disclosure search can start in 2010, but OpenDART's structured
    # financial-statement endpoints accept business years from 2015 onward.
    years = list(range(start_year, dt.date.today().year + 1))
    financial_years = list(range(max(start_year, 2015), dt.date.today().year + 1))

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        listing_results = list(pool.map(lambda year: listing_for(year, key), years))
    disclosures = [item for rows in listing_results for item in rows]

    financial_tasks = []
    for year in financial_years:
        for report_code, category in REPORTS.items():
            output = raw_dir / f"taihan_{year}_{report_code}.json"
            if not valid_cached_file(output):
                # Remove a stale error/empty cache before requesting it again.
                output.unlink(missing_ok=True)
                financial_tasks.append((year, report_code, category, output, key))

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        fetched = list(pool.map(fetch_financial, financial_tasks))

    valid_files = [p for p in raw_dir.glob("taihan_*.json") if valid_cached_file(p)]
    if not disclosures:
        raise RuntimeError(
            f"{CORP_CODE} 대한전선의 2010년 이후 정기보고서 공시가 0건입니다. "
            "인증키·기업코드·OpenDART 응답을 확인하세요. 빈 데이터로 대시보드를 덮어쓰지 않았습니다."
        )
    if not valid_files:
        raise RuntimeError(
            "재무제표 API에서 유효한 자료를 한 건도 받지 못했습니다. "
            "OpenDART 응답과 API 키 권한을 확인하세요."
        )

    (ROOT / "reports" / "opendart_disclosures.json").write_text(
        json.dumps(disclosures, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Report ZIPs are optional source material; the repository keeps the
    # disclosure index and normalized financial data, not large ZIP archives.
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        list(pool.map(lambda item: download_document(item, key, source_dir), disclosures))

    print(
        f"수집 완료: 정기보고서 {len(disclosures)}건, "
        f"유효 재무제표 {len(valid_files)}건, 신규 수집 {sum(p is not None for p in fetched)}건"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2010)
    main(parser.parse_args().start_year)
