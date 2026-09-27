# 대한전선 OpenDART 재무 분석 대시보드

<a href="https://hsc-class02.github.io/JY_taihan/"><img src="assets/taihan-badge.png" alt="대한전선 대시보드 바로가기" width="180"></a>

### [대시보드 바로가기](https://hsc-class02.github.io/JY_taihan/)

대한전선(DART 고유번호 `00105929`)의 사업보고서·반기보고서·분기보고서를 2010년부터 OpenDART에서 수집하고, 핵심 재무수치와 재무비율을 정리하는 자동화 프로젝트입니다.

## 대시보드

상단은 핵심 KPI와 추세 그래프, 하단은 Annual / Half-year / Quarterly 테이블로 구성됩니다. API 키를 등록한 뒤 Actions에서 한 번 실행하면 데이터가 채워집니다.

## 제공 범위

- 수집 기간: 2010년 1월 1일 이후
- 보고서: 사업보고서(`11011`), 반기보고서(`11012`), 1분기(`11013`), 3분기(`11014`)
- 주요 수치: 매출액, 매출원가, 매출총이익, 영업이익, 법인세차감전이익, 당기순이익, 자산·부채·자본, 현금, 매출채권, 재고자산, 영업현금흐름, CAPEX
- 재무비율: 성장률, 매출총/영업/순이익률, ROA, ROE, 유동·당좌비율, 부채비율, 재고회전율, DSO, CFO 전환율, FCF
- GitHub Actions: 매월 1일 09:00 KST 자동 갱신 및 GitHub Pages 재배포

## API 키 및 Pages 설정

1. [OpenDART](https://opendart.fss.or.kr/)에서 인증키를 발급받습니다.
2. GitHub 저장소에서 **Settings → Secrets and variables → Actions → New repository secret**으로 이동합니다.
3. Name에 `DART_API_KEY`, Secret에 발급받은 키를 넣습니다.
4. **Settings → Pages → Build and deployment → Source**를 `GitHub Actions`로 선택합니다.
5. **Actions → Update OpenDART data and deploy dashboard → Run workflow**를 한 번 실행합니다.

키는 저장소나 ZIP에 넣지 않습니다. 자세한 내용은 [API_KEY_SETUP.txt](API_KEY_SETUP.txt)를 참고하세요.

## 로컬 실행

```powershell
Copy-Item env.example.txt .env
# .env의 DART_API_KEY= 뒤에 인증키 입력
python -m pip install -r requirements.txt
python scripts/fetch_opendart.py --start-year 2010
python scripts/analyze.py
python -m http.server 8000
```

브라우저에서 `http://localhost:8000`을 열면 대시보드를 확인할 수 있습니다. 이 프로젝트는 정보 제공 목적이며 투자 권유가 아닙니다.
