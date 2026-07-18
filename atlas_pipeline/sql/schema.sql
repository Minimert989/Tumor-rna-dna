CREATE TABLE IF NOT EXISTS source_runs (
  run_id VARCHAR PRIMARY KEY,
  source VARCHAR NOT NULL,
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  status VARCHAR NOT NULL,
  source_version VARCHAR,
  records_read BIGINT DEFAULT 0,
  records_written BIGINT DEFAULT 0,
  raw_path VARCHAR,
  sha256 VARCHAR,
  error_message VARCHAR
);

CREATE TABLE IF NOT EXISTS cancer_types (
  oncotree_code VARCHAR PRIMARY KEY,
  name VARCHAR,
  main_type VARCHAR,
  tissue VARCHAR,
  level INTEGER,
  parent_code VARCHAR,
  nci_codes JSON,
  umls_codes JSON,
  synonyms JSON,
  deprecated BOOLEAN DEFAULT FALSE,
  version VARCHAR,
  raw_json JSON,
  source_run_id VARCHAR
);

CREATE TABLE IF NOT EXISTS drug_products (
  drug_id VARCHAR PRIMARY KEY,
  canonical_name VARCHAR,
  active_ingredient VARCHAR,
  brand_name VARCHAR,
  application_number VARCHAR,
  application_type VARCHAR,
  product_number VARCHAR,
  dosage_form VARCHAR,
  strength VARCHAR,
  route JSON,
  rxnorm_cui VARCHAR,
  marketing_status VARCHAR,
  source VARCHAR,
  source_record_id VARCHAR,
  raw_json JSON,
  source_run_id VARCHAR
);

CREATE TABLE IF NOT EXISTS drug_approvals (
  approval_id VARCHAR PRIMARY KEY,
  application_number VARCHAR,
  submission_type VARCHAR,
  submission_number VARCHAR,
  action_date DATE,
  status VARCHAR,
  review_priority VARCHAR,
  action_type VARCHAR,
  indication_text VARCHAR,
  document_url VARCHAR,
  source_run_id VARCHAR
);

CREATE TABLE IF NOT EXISTS drug_labels (
  label_id VARCHAR PRIMARY KEY,
  set_id VARCHAR,
  version VARCHAR,
  application_numbers JSON,
  brand_names JSON,
  generic_names JSON,
  active_ingredients JSON,
  route JSON,
  dosage_form JSON,
  indications_and_usage VARCHAR,
  dosage_and_administration VARCHAR,
  contraindications VARCHAR,
  boxed_warning VARCHAR,
  warnings_and_precautions VARCHAR,
  adverse_reactions VARCHAR,
  drug_interactions VARCHAR,
  clinical_studies VARCHAR,
  effective_time VARCHAR,
  source VARCHAR,
  source_url VARCHAR,
  raw_json JSON,
  source_run_id VARCHAR
);

CREATE TABLE IF NOT EXISTS clinical_trials (
  nct_id VARCHAR PRIMARY KEY,
  brief_title VARCHAR,
  official_title VARCHAR,
  study_type VARCHAR,
  phases JSON,
  overall_status VARCHAR,
  start_date VARCHAR,
  completion_date VARCHAR,
  conditions JSON,
  keywords JSON,
  interventions JSON,
  eligibility VARCHAR,
  minimum_age VARCHAR,
  maximum_age VARCHAR,
  sex VARCHAR,
  enrollment BIGINT,
  primary_outcomes JSON,
  secondary_outcomes JSON,
  has_results BOOLEAN,
  study_url VARCHAR,
  mapped_oncotree_codes JSON,
  raw_json JSON,
  source_run_id VARCHAR
);

CREATE TABLE IF NOT EXISTS biomarker_therapy_evidence (
  evidence_id VARCHAR PRIMARY KEY,
  gene VARCHAR,
  alteration VARCHAR,
  biomarker_type VARCHAR,
  oncotree_code VARCHAR,
  therapy VARCHAR,
  sensitivity_or_resistance VARCHAR,
  evidence_level VARCHAR,
  fda_level VARCHAR,
  oncogenic VARCHAR,
  mutation_effect VARCHAR,
  citations JSON,
  source VARCHAR,
  source_url VARCHAR,
  raw_json JSON,
  source_run_id VARCHAR
);

CREATE TABLE IF NOT EXISTS guideline_recommendations (
  recommendation_id VARCHAR PRIMARY KEY,
  source VARCHAR,
  source_version VARCHAR,
  cancer_name VARCHAR,
  oncotree_code VARCHAR,
  stage VARCHAR,
  setting VARCHAR,
  line_of_therapy VARCHAR,
  biomarker VARCHAR,
  regimen_name VARCHAR,
  recommendation_category VARCHAR,
  preferred_flag BOOLEAN,
  source_page VARCHAR,
  source_url VARCHAR,
  reviewed_by VARCHAR,
  reviewed_date DATE,
  notes VARCHAR,
  source_run_id VARCHAR
);

CREATE TABLE IF NOT EXISTS regimen_components (
  regimen_component_id VARCHAR PRIMARY KEY,
  source VARCHAR,
  protocol_id VARCHAR,
  protocol_version VARCHAR,
  cancer_name VARCHAR,
  oncotree_code VARCHAR,
  regimen_name VARCHAR,
  component_drug VARCHAR,
  rxnorm_cui VARCHAR,
  dose VARCHAR,
  dose_unit VARCHAR,
  route VARCHAR,
  day_pattern VARCHAR,
  cycle_days INTEGER,
  total_cycles VARCHAR,
  premedication VARCHAR,
  monitoring VARCHAR,
  dose_modification VARCHAR,
  major_toxicities VARCHAR,
  source_url VARCHAR,
  reviewed_date DATE,
  source_run_id VARCHAR
);

CREATE TABLE IF NOT EXISTS licensed_monographs (
  monograph_id VARCHAR PRIMARY KEY,
  source VARCHAR,
  export_date DATE,
  drug_name VARCHAR,
  rxnorm_cui VARCHAR,
  mechanism VARCHAR,
  indications VARCHAR,
  dosage VARCHAR,
  administration VARCHAR,
  contraindications VARCHAR,
  warnings VARCHAR,
  adverse_reactions VARCHAR,
  drug_interactions VARCHAR,
  renal_adjustment VARCHAR,
  hepatic_adjustment VARCHAR,
  monitoring VARCHAR,
  source_record_id VARCHAR,
  reviewed_date DATE,
  source_run_id VARCHAR
);

CREATE TABLE IF NOT EXISTS mapping_issues (
  issue_id VARCHAR PRIMARY KEY,
  entity_type VARCHAR,
  entity_id VARCHAR,
  source_text VARCHAR,
  proposed_oncotree_code VARCHAR,
  score DOUBLE,
  status VARCHAR,
  note VARCHAR,
  source_run_id VARCHAR
);

CREATE OR REPLACE VIEW atlas_cancer_coverage AS
SELECT
  c.oncotree_code,
  c.name,
  c.main_type,
  c.level,
  COUNT(DISTINCT g.recommendation_id) AS guideline_recommendations,
  COUNT(DISTINCT r.regimen_component_id) AS regimen_components,
  COUNT(DISTINCT e.evidence_id) AS biomarker_evidence,
  COUNT(DISTINCT t.nct_id) AS clinical_trials
FROM cancer_types c
LEFT JOIN guideline_recommendations g USING (oncotree_code)
LEFT JOIN regimen_components r USING (oncotree_code)
LEFT JOIN biomarker_therapy_evidence e USING (oncotree_code)
LEFT JOIN clinical_trials t ON list_contains(CAST(t.mapped_oncotree_codes AS VARCHAR[]), c.oncotree_code)
GROUP BY ALL;
