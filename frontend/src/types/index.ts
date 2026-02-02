// Node types for the graph
export type NodeType = 'company' | 'asset' | 'trial' | 'deal';

export interface GraphNode {
  id: string;
  type: NodeType;
  label: string;
  data: Record<string, unknown>;
  // For react-force-graph
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphEdge {
  id: string;
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
  label: string;
  data: Record<string, unknown>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// API response types
export interface Company {
  company_id: string;
  name: string;
  aliases: string[];
  country?: string;
  public_flag?: boolean;
  tickers: string[];
  cik?: string;
  status?: string;
  trials?: Trial[];
  assets?: Asset[];
  deals?: Deal[];
  evidence?: Evidence[];
}

export interface Asset {
  asset_id: string;
  name: string;
  synonyms: string[];
  modality?: string;
  targets: string[];
  indications: string[];
  stage_current?: string;
  modality_confidence?: number;
  targets_confidence?: number;
  trials?: Trial[];
  owners?: Company[];
  deals?: Deal[];
  evidence?: Evidence[];
}

export interface Trial {
  trial_id: string;
  title: string;
  phase?: string;
  status?: string;
  start_date?: string;
  completion_date?: string;
  interventions: string[];
  conditions: string[];
  sponsors: string[];
  collaborators: string[];
  enrollment?: number;
  study_type?: string;
  brief_summary?: string;
  source_url: string;
  evidence?: Evidence[];
  role?: string; // For sponsor relationship
}

export interface Deal {
  deal_id: string;
  deal_type: string;
  announce_date?: string;
  summary?: string;
  status?: string;
  value_usd?: number;
  evidence?: Evidence[];
  role?: string; // For party relationship
}

export interface Evidence {
  source_type: string;
  source_url?: string;
  source_id?: string;
  confidence: number;
  extracted_at: string;
  input_fields?: string[];
}

export interface LandscapeData {
  indication: string;
  assets_by_phase: Array<{ phase: string; count: number }>;
  sponsors_by_trial_count: Array<{ sponsor: string; id: string; trial_count: number }>;
  modalities: Array<{ modality: string; count: number }>;
  targets: Array<{ target: string; count: number }>;
  total_trials: number;
  total_assets: number;
  total_companies: number;
  standard_of_care: StandardOfCare;
}

export interface StandardOfCare {
  available: boolean;
  note: string;
  placeholder_info?: {
    indication_full_name: string;
    needs_citation: boolean;
    summary: string;
    key_agents: Array<{
      name: string;
      approved: boolean;
      notes: string;
    }>;
    disclaimer: string;
  };
}

export interface SearchResults {
  companies: Array<Company & { score: number }>;
  assets: Array<Asset & { score: number }>;
  trials: Array<Trial & { score: number }>;
}

export interface HealthStatus {
  status: string;
  database: string;
  stats: {
    companies: number;
    assets: number;
    trials: number;
    deals: number;
    documents: number;
  };
}

export interface IngestResponse {
  status: string;
  indication: string;
  stats: {
    trials: number;
    companies: number;
    assets: number;
    documents: number;
    sponsor_relations: number;
    asset_trial_relations: number;
    ownership_relations: number;
  };
}
