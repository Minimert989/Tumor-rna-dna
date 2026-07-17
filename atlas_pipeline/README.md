# All-Cancer Treatment Atlas Pipeline

이 프로젝트는 대표 암종을 수동으로 적은 표가 아니라, 가능한 범위에서 **전 암종·전 약물·전 임상시험·전 바이오마커 근거를 반복 수집하는 ETL 파이프라인**이다.

## 자동 수집되는 공개 소스

| 계층 | 소스 | 방식 |
|---|---|---|
| 전 암종 분류 | MSK OncoTree | 전체 tumorTypes API |
| FDA 승인 제품·신청·보충승인 | Drugs@FDA | 매일 갱신되는 전체 ZIP 12개 테이블 |
| 약물 라벨 | openFDA | 전체 drug-label bulk partitions 또는 API |
| 현재 SPL 메타데이터 | DailyMed | v2 REST API |
| 약물명 표준화 | RxNorm | REST API |
| 전 암종 임상시험 | ClinicalTrials.gov | API v2 전체 pagination + 중복 제거 |
| 변이–치료 근거 | OncoKB | 공식 API token 또는 공식 Annotator 출력 import |

## 자동 수집하지 않는 소스

NCCN, eviQ, Micromedex, Lexidrug는 완전 공개된 범용 API가 없거나 라이선스·계정 조건이 있다. 이 파이프라인은 로그인 우회나 무단 scraping을 하지 않는다.

대신 다음 export/import 계약을 제공한다.

- `manual_imports/nccn_recommendations.csv`
- `manual_imports/eviq_regimens.csv`
- `manual_imports/micromedex_monographs.csv`
- `manual_imports/lexidrug_monographs.csv`
- `manual_imports/oncokb_annotations.tsv`

기관에서 적법하게 내려받은 자료를 위 스키마로 넣으면 공개 API 자료와 동일한 DB에 병합된다.

## 설치

```bash
cd all_cancer_atlas_pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

OncoKB API를 사용할 때만 토큰을 지정한다.

```bash
export ONCOKB_API_TOKEN="..."
export OPENFDA_API_KEY="..."  # 선택
```

## 실행

### 1. 초기화

```bash
cancer-atlas init
```

### 2. 전체 공개 데이터 동기화

```bash
cancer-atlas sync \
  -s oncotree \
  -s drugs_at_fda \
  -s openfda_labels \
  -s dailymed \
  -s clinicaltrials
```

`openfda_labels.mode: bulk`가 기본이므로 전체 라벨 partition을 내려받는다. 저장공간과 시간이 많이 필요하다. 빠른 시험은 YAML에서 `mode: api`로 바꾼다.

### 3. OncoKB 변이 annotation

입력 열:

```text
Hugo_Symbol, Alteration, OncoTree_Code, Reference_Genome
```

실행:

```bash
cancer-atlas annotate-oncokb variants.tsv
```

대규모 MAF/CNA/fusion은 OncoKB 공식 Annotator를 실행한 뒤 `manual_imports/oncokb_annotations.tsv`로 넣는 방식이 더 적절하다.

### 4. 라이선스 자료 병합 및 암종 매핑

```bash
cancer-atlas compile
```

ClinicalTrials.gov의 condition은 OncoTree로 자동 매핑하며, 낮은 점수는 `mapping_issues`에 남긴다. 임의로 버리지 않는다.

### 5. QA와 export

```bash
cancer-atlas qa
cancer-atlas export-atlas
```

산출물:

```text
data/atlas.duckdb
exports/cancer_types.csv|parquet
exports/drug_products.csv|parquet
exports/drug_approvals.csv|parquet
exports/drug_labels.csv|parquet
exports/clinical_trials.csv|parquet
exports/biomarker_therapy.csv|parquet
exports/guidelines.csv|parquet
exports/regimens.csv|parquet
exports/licensed_monographs.csv|parquet
exports/coverage.csv|parquet
exports/mapping_issues.csv|parquet
exports/all_cancer_treatment_atlas.xlsx
reports/coverage.json
reports/coverage.md
```

## “싹다”의 정확한 의미

이 파이프라인은 다음을 지향한다.

1. OncoTree의 모든 암종 코드를 master taxonomy로 유지한다.
2. Drugs@FDA의 전체 제품·신청·보충승인을 보존한다.
3. openFDA의 전체 label partition을 원문과 checksum 단위로 보존한다.
4. ClinicalTrials.gov oncology query 결과를 끝까지 pagination하고 NCT ID로 중복 제거한다.
5. 매핑되지 않은 암종·약물·바이오마커를 삭제하지 않고 review queue로 보낸다.
6. 출처·버전·실행시각을 `source_runs`에 기록한다.

하지만 NCCN/Micromedex/Lexidrug의 전체 내용을 라이선스 없이 복제하는 것은 기술 문제가 아니라 사용권 문제다. 그래서 이 세 계층은 적법한 기관 export를 받아 병합하도록 설계되어 있다.

## 데이터 모델 핵심

- `cancer_types`: OncoTree 전체 계층
- `drug_products`: FDA 제품과 RxNorm 정규화
- `drug_approvals`: NDA/BLA 및 supplement action
- `drug_labels`: openFDA/DailyMed label sections
- `clinical_trials`: 모든 oncology trial 원문 JSON + 정규화 필드
- `biomarker_therapy_evidence`: OncoKB 근거
- `guideline_recommendations`: NCCN 등 가이드라인 권고
- `regimen_components`: eviQ 등 실제 투여 구성
- `licensed_monographs`: Micromedex/Lexidrug 기관 export
- `mapping_issues`: 자동매핑 실패와 수동 검토 큐

## 운영 권장

- Drugs@FDA: 매주 또는 매일
- openFDA/DailyMed: 매주
- ClinicalTrials.gov: 매주
- OncoTree/OncoKB: 월 1회
- NCCN/eviQ/기관 monograph: 버전 변경 때마다 수동 검토

GitHub Actions 예시는 `.github/workflows/update-atlas.yml`에 포함되어 있다.
