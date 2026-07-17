# Tumor RNA/DNA — All-Cancer Treatment Atlas

전 암종 치료 정보를 사람이 선별한 대표 목록이 아니라 API·bulk dataset·정규화 규칙으로 수집하는 ETL 프로젝트다.

실행 가능한 소스는 [`atlas_pipeline/`](atlas_pipeline/)에 직접 포함돼 있다.

## 공개 데이터 자동 수집

- MSK OncoTree 전체 암종 계층
- Drugs@FDA 전체 제품·신청·보충승인 ZIP
- openFDA 전체 drug-label bulk partition 또는 API
- DailyMed v2 SPL 메타데이터
- RxNorm 약물명 표준화
- ClinicalTrials.gov API v2 전 암종 검색·pagination·NCT 중복 제거
- OncoKB API 또는 공식 Annotator 출력

NCCN, eviQ, Micromedex, Lexidrug는 인증이나 사용권을 우회하지 않는다. 기관에서 적법하게 확보한 export를 `atlas_pipeline/manual_imports/` 스키마로 병합한다.

## 실행

```bash
cd atlas_pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env

cancer-atlas init
cancer-atlas full
```

빠른 검증은 다음과 같다.

```bash
cd atlas_pipeline
python -m compileall -q src
pytest -q
cancer-atlas init
```

## 결과

```text
atlas_pipeline/data/atlas.duckdb
atlas_pipeline/exports/*.csv
atlas_pipeline/exports/*.parquet
atlas_pipeline/exports/all_cancer_treatment_atlas.xlsx
atlas_pipeline/reports/coverage.json
atlas_pipeline/reports/coverage.md
```

## 자동화

- `validate-pipeline.yml`: 설치, Python compile, unit test, DuckDB schema 초기화
- `update-atlas.yml`: 매주 공개 API 동기화, 정규화, QA, CSV/Parquet/Excel artifact 생성

선택적 repository secrets:

```text
OPENFDA_API_KEY
ONCOKB_API_TOKEN
```

구조와 evidence layer는 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)에 정리돼 있다.
