# All-Cancer Treatment Atlas Pipeline

API와 정규화 규칙을 이용해 전 암종 분류, 승인 약물, 약물 라벨, 임상시험, 바이오마커–치료 근거를 반복 수집하는 ETL 프로젝트다.

## 자동 수집 계층

| 계층 | 기본 소스 | 방식 |
|---|---|---|
| 전 암종 분류 | MSK OncoTree | 전체 tumor type API |
| FDA 제품·신청·보충승인 | Drugs@FDA | 전체 데이터 ZIP |
| 약물 라벨 | openFDA | API 또는 bulk partition |
| SPL 메타데이터 | DailyMed | REST API |
| 약물명 표준화 | RxNorm | REST API |
| 전 암종 임상시험 | ClinicalTrials.gov | API v2 pagination |
| 변이–치료 근거 | OncoKB | API token 또는 Annotator import |

NCCN, eviQ, Micromedex, Lexidrug는 라이선스·계정 범위 안에서 확보한 export를 import한다. 로그인 우회나 무단 scraping은 하지 않는다.

## 빠른 실행

```bash
unzip pipeline/all_cancer_atlas_pipeline.zip -d pipeline/src
cd pipeline/src/all_cancer_atlas_pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
cancer-atlas init
cancer-atlas full
```

빠른 테스트에서는 `config/pipeline.yaml`의 openFDA mode를 `api`로 바꾸고 임상시험 수집 범위를 제한한다.

## 주요 산출물

```text
data/atlas.duckdb
exports/*.csv
exports/*.parquet
exports/all_cancer_treatment_atlas.xlsx
reports/coverage.json
reports/coverage.md
```

## GitHub Actions

`update-atlas.yml`은 매주 공개 API를 동기화하고 atlas DB·CSV·Excel·QA 보고서를 artifact로 저장한다. OncoKB와 openFDA 키는 repository secrets에 둔다.

```text
OPENFDA_API_KEY
ONCOKB_API_TOKEN
```

## 데이터 원칙

1. OncoTree 전체 계층을 master cancer taxonomy로 유지한다.
2. 원문과 정규화 필드를 함께 저장한다.
3. 매핑 실패 기록을 삭제하지 않고 review queue에 보존한다.
4. source URL, 실행 시각, checksum, record count를 provenance로 기록한다.
5. 임상시험 등록은 효능 입증과 구분한다.
6. 승인약·가이드라인·임상시험·전임상 근거를 서로 다른 evidence layer로 유지한다.

전체 소스와 모듈은 `pipeline/all_cancer_atlas_pipeline.zip`에 포함돼 있다. 구조 설명은 `docs/ARCHITECTURE.md`를 참고한다.
