# All-Cancer Treatment Atlas Pipeline

API와 정규화 규칙을 이용해 전 암종 분류, 승인 약물, 약물 라벨, 임상시험, 바이오마커–치료 근거를 반복 수집하는 ETL 프로젝트다. 사람이 선정한 대표 암종 목록이 아니라 **OncoTree 전체 암종 계층**을 master taxonomy로 사용한다.

## 자동 수집 계층

| 계층 | 기본 소스 | 방식 |
|---|---|---|
| 전 암종 분류 | MSK OncoTree | 전체 tumor type API |
| FDA 제품·신청·보충승인 | Drugs@FDA | 전체 데이터 ZIP |
| 약물 라벨 | openFDA | API 또는 전체 bulk partition |
| SPL 메타데이터 | DailyMed | REST API |
| 약물명 표준화 | RxNorm | REST API |
| 전 암종 임상시험 | ClinicalTrials.gov | API v2 pagination + NCT 중복 제거 |
| 변이–치료 근거 | OncoKB | API token 또는 Annotator import |

NCCN, eviQ, Micromedex, Lexidrug는 라이선스·계정 범위 안에서 확보한 export를 import한다. 로그인 우회나 무단 scraping은 하지 않는다.

## 빠른 실행

GitHub connector는 바이너리 ZIP을 직접 커밋하지 못하므로 archive를 base64 text parts로 보존한다. 먼저 checksum을 검증하면서 원본 ZIP을 복원한다.

```bash
bash pipeline/reconstruct.sh
rm -rf pipeline/src
mkdir -p pipeline/src
unzip pipeline/all_cancer_atlas_pipeline.zip -d pipeline/src
cd pipeline/src/all_cancer_atlas_pipeline

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env

cancer-atlas init
cancer-atlas full
```

`pipeline/reconstruct.sh`는 다음 SHA-256과 ZIP 내부 무결성을 확인한다.

```text
c60142705ac71d28a555a751031b23d777dfd50b22a923d8383579b64dc6d3c8
```

빠른 테스트에서는 `config/pipeline.yaml`의 openFDA mode를 `api`로 바꾸고 임상시험 수집 범위를 제한한다. exhaustive mode는 openFDA 전체 라벨 partition과 OncoTree 기반 임상시험 검색 때문에 장시간·대용량 작업이다.

## 주요 산출물

```text
data/atlas.duckdb
exports/cancer_types.csv
exports/drug_products.csv
exports/drug_approvals.csv
exports/drug_labels.csv
exports/clinical_trials.csv
exports/biomarker_therapy.csv
exports/guidelines.csv
exports/regimens.csv
exports/licensed_monographs.csv
exports/coverage.csv
exports/mapping_issues.csv
exports/all_cancer_treatment_atlas.xlsx
reports/coverage.json
reports/coverage.md
```

## GitHub Actions

- `validate-pipeline.yml`: pull request에서 archive 복원, 설치, syntax 검사, unit test, DB 초기화를 수행한다.
- `update-atlas.yml`: 매주 월요일 공개 API를 동기화하고 DuckDB·CSV·Parquet·Excel·QA 보고서를 artifact로 저장한다.

OncoKB와 openFDA 키는 repository secrets에 둔다.

```text
OPENFDA_API_KEY
ONCOKB_API_TOKEN
```

키가 없어도 공개 범위의 소스는 작동하도록 설계하되, API rate limit과 OncoKB 라이선스 범위가 달라질 수 있다.

## 데이터 원칙

1. OncoTree 전체 계층을 master cancer taxonomy로 유지한다.
2. 원문 필드와 정규화 필드를 함께 저장한다.
3. 매핑 실패 기록을 삭제하지 않고 `mapping_issues` 검토 큐에 보존한다.
4. source URL, 실행 시각, checksum, record count를 provenance로 기록한다.
5. 임상시험 등록은 임상 효능 입증과 구분한다.
6. 승인약·가이드라인·임상시험·전임상 근거를 별도 evidence layer로 유지한다.
7. 암종, 약물, 변이의 자동 매핑은 confidence score와 검토 상태를 저장한다.
8. 공개 API 데이터와 구독형 monograph를 동일 출처처럼 취급하지 않는다.

전체 소스와 모듈은 `pipeline/archive_parts/`에 분할 저장된 archive에 포함돼 있다. 구조 설명은 `docs/ARCHITECTURE.md`를 참고한다.
