export interface Project {
  id: string;
  bureau_id: string;
  client_id: string;
  name: string;
  reporting_year: number;
  methodology_id: string;
  status: string;
  reporting_frameworks: string[] | null;
  sector_code: string | null;
  language: "fr" | "en" | "ar" | null;
  ndc_target_year: number | null;
  ndc_baseline_year: number | null;
  created_at: string;
}

export interface Client {
  id: string;
  bureau_id: string;
  name: string;
  sector: string;
  naics_code: string | null;
  secteur_maroc: string | null;
  is_listed_bvc: boolean;
  rse_reporting_required: boolean;
  created_at: string;
}

export interface ActivityFact {
  id: string;
  bureau_id: string;
  project_id: string;
  category: string;
  sub_category: string | null;
  description: string;
  activity_value: string;
  activity_unit: string;
  period_start: string;
  period_end: string;
  scope: number;
  scope2_type: string | null;
  state: "proposed" | "validated";
  provenance: Record<string, unknown> | null;
  created_at: string;
}

export interface ReportSnapshot {
  id: string;
  bureau_id: string;
  project_id: string;
  reporting_year: number;
  state_hash: string;
  totals_co2e: Record<string, number>;
  scope2_location_t: string | null;
  scope2_market_t: string | null;
  gwp_basis: string;
  uncertainty: Record<string, unknown>;
  computation_trace: unknown[];
  factor_set_versions: unknown;
  reconciliation: unknown;
  gri_305_data: Record<string, number> | null;
  ndc_alignment: Record<string, unknown> | null;
  intensity_metrics: Record<string, number> | null;
  created_at: string;
}

export interface Document {
  id: string;
  bureau_id: string;
  project_id: string;
  original_filename: string;
  processing_status: "pending" | "processing" | "done" | "error";
  extraction_confidence: number | null;
  created_at: string;
}

export interface Anomaly {
  id: string;
  bureau_id: string;
  project_id: string;
  activity_fact_id: string | null;
  anomaly_type: string;
  severity: string;
  description: string;
  resolved: boolean;
  created_at: string;
}
