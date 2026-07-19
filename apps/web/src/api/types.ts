// Mirrors the Pydantic models. Keep in sync with models/*.py.

export type Role = "public" | "officer" | "senior_officer" | "admin";

export interface User {
  id: string;
  email: string;
  role: Role;
  full_name?: string | null;
  officer_id?: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  role: Role;
}

export interface PublicCaseView {
  case_id: string;
  crime_type: string;
  locality: string;
  occurred_on: string;
  status: string;
}

export interface OfficerCase extends PublicCaseView {
  street_address?: string | null;
  mo_details?: string | null;
  victim_names: string[];
  suspect_names: string[];
  phone_numbers: string[];
  narrative?: string | null;
}

export type Case = PublicCaseView | OfficerCase;

export interface Citation {
  case_id: string;
  locality?: string | null;
  occurred_on?: string | null;
  crime_type?: string | null;
  score?: number | null;
}

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  query: string;
  top_k?: number;
  filters?: Record<string, string>;
  history?: ChatTurn[];
  conversation_id?: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  retrieved_chunk_ids: string[];
  model: string;
  conversation_id?: string | null;
  detected_language: "en" | "hi" | "kn";
}

export interface TranscribeResponse {
  text: string;
  language: string;
  duration_seconds: number;
  provider: string;
}

export type RiskBand = "low" | "medium" | "high";

export interface FeatureContribution {
  name: string;
  value: string | number;
  contribution: number;
  explanation: string;
}

export interface RecidivismRequest {
  subject: string;
  reason: string;
}

export interface RecidivismResponse {
  subject: string;
  score: number;
  band: RiskBand;
  case_count: number;
  features: Record<string, string | number>;
  top_contributions: FeatureContribution[];
  model_version: string;
  is_stub: boolean;
  decision_note: string;
}

export type NodeKind = "case" | "suspect";
export type EdgeKind = "mentions" | "co_suspect";

export interface NetworkNode {
  id: string;
  label: string;
  kind: NodeKind;
  properties: Record<string, string | number | null>;
}

export interface NetworkEdge {
  id: string;
  source: string;
  target: string;
  kind: EdgeKind;
  weight: number;
}

export interface NetworkResponse {
  center_id: string;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  depth: number;
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  turn_count: number;
}

export interface Conversation extends ConversationSummary {
  user_id: string;
  turns: ChatTurn[];
}

export interface TrendBucket {
  bucket_start: string;
  count: number;
  by_crime_type: Record<string, number>;
}

export interface TrendsResponse {
  granularity: "week" | "month";
  from_date: string | null;
  to_date: string | null;
  buckets: TrendBucket[];
  total: number;
}

export interface LocalityCount {
  locality: string;
  count: number;
  top_crime_types: string[];
}

export interface TopLocalitiesResponse {
  limit: number;
  localities: LocalityCount[];
  total_cases: number;
}

export interface Hotspot {
  locality: string;
  count: number;
  crime_type: string | null;
  recent_count: number;
}

export interface HotspotsResponse {
  limit: number;
  window_days: number;
  hotspots: Hotspot[];
}

export interface MapPoint {
  case_id: string;
  crime_type: string;
  locality: string;
  status: string;
  occurred_on: string;
  lat: number;
  lng: number;
}

export interface MapResponse {
  points: MapPoint[];
  total: number;
}

export interface DossierCase {
  case_id: string;
  crime_type: string;
  locality: string;
  occurred_on: string;
  status: string;
}

export interface PersonDossier {
  name: string;
  case_count: number;
  localities: string[];
  crime_types: string[];
  co_accused: string[];
  first_seen: string | null;
  last_seen: string | null;
  recidivism_band: RiskBand | null;
  recidivism_score: number | null;
  cases: DossierCase[];
}
