import type {
  GraphData,
  Company,
  Asset,
  Trial,
  LandscapeData,
  SearchResults,
  HealthStatus,
  IngestResponse,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}/api${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API error: ${response.status} - ${error}`);
  }

  return response.json();
}

// Health check
export async function getHealth(): Promise<HealthStatus> {
  return fetchApi<HealthStatus>('/health');
}

// Ingestion
export async function ingestClinicalTrials(
  indication: string = 'MuM',
  maxTrials?: number
): Promise<IngestResponse> {
  return fetchApi<IngestResponse>('/ingest/clinicaltrials', {
    method: 'POST',
    body: JSON.stringify({
      indication,
      max_trials: maxTrials,
    }),
  });
}

// Search
export async function search(query: string, limit: number = 20): Promise<SearchResults> {
  return fetchApi<SearchResults>(`/search?q=${encodeURIComponent(query)}&limit=${limit}`);
}

// Graph
export type TrialFilter = 'none' | 'recruiting' | 'active_not_recruiting' | 'all';

export async function getIndicationGraph(
  indication: string,
  options: {
    depth?: number;
    phases?: string[];
    modalities?: string[];
    includeTrials?: boolean;
    trialFilter?: TrialFilter;
  } = {}
): Promise<GraphData> {
  const params = new URLSearchParams({
    name: indication,
    depth: String(options.depth || 2),
    include_trials: String(options.includeTrials || false),
    trial_filter: options.trialFilter ?? 'none',
  });

  if (options.phases?.length) {
    params.set('phases', options.phases.join(','));
  }
  if (options.modalities?.length) {
    params.set('modalities', options.modalities.join(','));
  }

  const data = await fetchApi<{ nodes: any[]; edges: any[] }>(
    `/graph/indication?${params.toString()}`
  );

  // Transform edges to use source/target as strings for react-force-graph
  return {
    nodes: data.nodes,
    edges: data.edges.map((edge) => ({
      ...edge,
      source: typeof edge.source === 'object' ? edge.source.id : edge.source,
      target: typeof edge.target === 'object' ? edge.target.id : edge.target,
    })),
  };
}

// Company details
export async function getCompany(companyId: string): Promise<Company> {
  return fetchApi<Company>(`/company/${encodeURIComponent(companyId)}`);
}

// Asset details
export async function getAsset(assetId: string): Promise<Asset> {
  return fetchApi<Asset>(`/asset/${encodeURIComponent(assetId)}`);
}

// Update asset (user-confirmed modality, targets, owner; ingestion will not overwrite)
export async function updateAsset(
  assetId: string,
  payload: {
    modality?: string;
    targets?: string[];
    owner_company_id?: string;
    owner_company_name?: string;
  }
): Promise<Asset> {
  return fetchApi<Asset>(`/asset/${encodeURIComponent(assetId)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

// Create company by name (e.g. new sponsor). Returns company_id.
export async function createCompany(name: string): Promise<{ company_id: string; name: string }> {
  return fetchApi<{ company_id: string; name: string }>('/company', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

// Trial details
export async function getTrial(trialId: string): Promise<Trial> {
  return fetchApi<Trial>(`/trial/${encodeURIComponent(trialId)}`);
}

// Landscape
export async function getLandscape(indication: string = 'MuM'): Promise<LandscapeData> {
  return fetchApi<LandscapeData>(`/landscape?indication=${encodeURIComponent(indication)}`);
}

// Configuration
export async function getConfiguredIndications(): Promise<{
  default: string;
  indications: Record<string, string[]>;
}> {
  return fetchApi('/config/indications');
}
