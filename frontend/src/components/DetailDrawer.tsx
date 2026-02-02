'use client';

import { X, ExternalLink, AlertCircle, Building2, FlaskConical, FileText } from 'lucide-react';
import type { GraphNode, GraphEdge, Company, Asset, Trial } from '@/types';
import {
  cn,
  nodeColorsBg,
  nodeColorsBgLight,
  nodeColorsText,
  formatPhase,
  formatStatus,
  getStatusColor,
  formatConfidence,
} from '@/lib/utils';

interface DetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  node?: GraphNode | null;
  edge?: GraphEdge | null;
  entityData?: Company | Asset | Trial | null;
  loading?: boolean;
  onNavigateToNode?: (nodeId: string, nodeType: string) => void;
}

export default function DetailDrawer({
  isOpen,
  onClose,
  node,
  edge,
  entityData,
  loading,
  onNavigateToNode,
}: DetailDrawerProps) {
  if (!isOpen) return null;

  return (
    <div
      className={cn(
        'fixed right-0 top-0 h-full w-96 bg-white shadow-2xl z-50',
        'transform transition-transform duration-300 ease-out',
        'border-l border-gray-200 overflow-hidden',
        isOpen ? 'translate-x-0' : 'translate-x-full'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center space-x-2">
          {node && (
            <>
              <div
                className={cn(
                  'w-3 h-3 rounded-full',
                  nodeColorsBg[node.type]
                )}
              />
              <span className="font-medium text-sm capitalize">{node.type}</span>
            </>
          )}
          {edge && (
            <>
              <div className="w-3 h-3 rounded-full bg-gray-400" />
              <span className="font-medium text-sm">Relationship</span>
            </>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-200 rounded-full transition-colors"
        >
          <X className="w-5 h-5 text-gray-500" />
        </button>
      </div>

      {/* Content */}
      <div className="overflow-y-auto h-[calc(100%-60px)] p-4">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
          </div>
        ) : node ? (
          <NodeDetail node={node} entityData={entityData} onNavigateToNode={onNavigateToNode} />
        ) : edge ? (
          <EdgeDetail edge={edge} />
        ) : (
          <p className="text-gray-500 text-sm">Select a node or edge to view details</p>
        )}
      </div>
    </div>
  );
}

function NodeDetail({
  node,
  entityData,
  onNavigateToNode,
}: {
  node: GraphNode;
  entityData?: Company | Asset | Trial | null;
  onNavigateToNode?: (nodeId: string, nodeType: string) => void;
}) {
  const data = entityData || node.data;

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Title */}
      <div>
        <h2 className={cn('text-lg font-semibold', nodeColorsText[node.type])}>
          {node.label}
        </h2>
        <p className="text-xs text-gray-400 font-mono mt-1">{node.id}</p>
      </div>

      {/* Type-specific content */}
      {node.type === 'company' && <CompanyDetails data={data as any} onNavigateToNode={onNavigateToNode} />}
      {node.type === 'asset' && <AssetDetails data={data as any} onNavigateToNode={onNavigateToNode} />}
      {node.type === 'trial' && <TrialDetails data={data as any} onNavigateToNode={onNavigateToNode} />}
      {node.type === 'deal' && <DealDetails data={data as any} />}

      {/* Evidence section */}
      {(data as any)?.evidence && (data as any).evidence.length > 0 && (
        <div className="pt-4 border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Evidence</h3>
          <div className="space-y-2">
            {(data as any).evidence.slice(0, 3).map((ev: any, i: number) => (
              <div
                key={i}
                className="text-xs bg-gray-50 rounded p-2 flex items-start space-x-2"
              >
                <FileText className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-gray-600">{ev.source_type}</p>
                  {ev.source_url && (
                    <a
                      href={ev.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:underline flex items-center"
                    >
                      View source
                      <ExternalLink className="w-3 h-3 ml-1" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Helper to get company type display info
function getCompanyTypeInfo(companyType?: string): { label: string; color: string; bgColor: string } {
  switch (companyType) {
    case 'industry':
      return { label: 'Industry', color: 'text-blue-700', bgColor: 'bg-blue-100' };
    case 'academic':
      return { label: 'Academic', color: 'text-purple-700', bgColor: 'bg-purple-100' };
    case 'government':
      return { label: 'Government', color: 'text-gray-700', bgColor: 'bg-gray-200' };
    case 'investigator':
      return { label: 'Investigator', color: 'text-orange-700', bgColor: 'bg-orange-100' };
    default:
      return { label: 'Other', color: 'text-gray-600', bgColor: 'bg-gray-100' };
  }
}

// Group assets by their indications
function groupAssetsByIndication(assets: any[]): Map<string, any[]> {
  const groups = new Map<string, any[]>();
  
  for (const asset of assets) {
    const indications = asset.indications || [];
    if (indications.length === 0) {
      // No indication - put in "Other" group
      if (!groups.has('Other')) groups.set('Other', []);
      groups.get('Other')!.push(asset);
    } else {
      // Add to each indication group (asset can be in multiple)
      for (const indication of indications.slice(0, 2)) { // Limit to first 2 indications
        const key = indication.length > 40 ? indication.slice(0, 40) + '...' : indication;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key)!.push(asset);
      }
    }
  }
  
  return groups;
}

function CompanyDetails({ data, onNavigateToNode }: { data: any; onNavigateToNode?: (nodeId: string, nodeType: string) => void }) {
  const typeInfo = getCompanyTypeInfo(data.company_type);
  const assetsByIndication = data.assets?.length > 0 ? groupAssetsByIndication(data.assets) : new Map();
  
  return (
    <div className="space-y-3">
      {/* Company Type Badge */}
      {data.company_type && (
        <div className="flex items-center space-x-2">
          <span className={cn('text-xs px-2 py-0.5 rounded font-medium', typeInfo.bgColor, typeInfo.color)}>
            {typeInfo.label}
          </span>
        </div>
      )}

      {data.aliases?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Aliases</p>
          <p className="text-sm text-gray-700">{data.aliases.join(', ')}</p>
        </div>
      )}

      {data.country && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Country</p>
          <p className="text-sm text-gray-700">{data.country}</p>
        </div>
      )}

      {data.trials?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium mb-2">
            Trials ({data.trials.length}) <span className="text-blue-500 font-normal">— click to focus</span>
          </p>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {data.trials.slice(0, 5).map((trial: any) => (
              <button
                key={trial.trial_id}
                onClick={() => onNavigateToNode?.(trial.trial_id, 'trial')}
                className="w-full text-left bg-amber-50 hover:bg-amber-100 rounded p-2 transition-colors cursor-pointer"
              >
                <p className="text-sm font-medium text-blue-600 hover:underline">{trial.trial_id}</p>
                <p className="text-xs text-gray-600 truncate">{trial.title}</p>
                <div className="flex items-center space-x-2 mt-1">
                  <span className="text-xs bg-amber-200 px-1.5 py-0.5 rounded">
                    {formatPhase(trial.phase)}
                  </span>
                  <span className={cn('text-xs', getStatusColor(trial.status))}>
                    {formatStatus(trial.status)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {assetsByIndication.size > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium mb-2">
            Assets ({data.assets.length}) <span className="text-blue-500 font-normal">— click to focus</span>
          </p>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {Array.from(assetsByIndication.entries()).map(([indication, assets]) => (
              <div key={indication}>
                <p className="text-xs text-gray-500 mb-1 italic">{indication}</p>
                <div className="flex flex-wrap gap-1.5">
                  {assets.map((asset: any) => (
                    <button
                      key={asset.asset_id}
                      onClick={() => onNavigateToNode?.(asset.asset_id, 'asset')}
                      className="text-xs bg-green-100 text-green-700 hover:bg-green-200 px-2 py-1 rounded cursor-pointer transition-colors"
                      title={asset.modality || undefined}
                    >
                      {asset.name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function AssetDetails({ data, onNavigateToNode }: { data: any; onNavigateToNode?: (nodeId: string, nodeType: string) => void }) {
  return (
    <div className="space-y-3">
      {data.synonyms?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Synonyms</p>
          <p className="text-sm text-gray-700">{data.synonyms.join(', ')}</p>
        </div>
      )}

      {data.modality && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Modality</p>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-700">{data.modality}</span>
            {data.modality_confidence && (
              <span className="text-xs text-gray-400">
                ({formatConfidence(data.modality_confidence)} confidence)
              </span>
            )}
          </div>
        </div>
      )}

      {data.targets?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Targets</p>
          <div className="flex flex-wrap gap-1 mt-1">
            {data.targets.map((target: string) => (
              <span
                key={target}
                className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded"
              >
                {target}
              </span>
            ))}
          </div>
        </div>
      )}

      {data.stage_current && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Stage</p>
          <p className="text-sm text-gray-700">{formatPhase(data.stage_current)}</p>
        </div>
      )}

      {data.owners?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium mb-2">
            Owners (Inferred) <span className="text-blue-500 font-normal">— click to focus</span>
          </p>
          <div className="space-y-2">
            {data.owners.map((owner: any) => (
              <button
                key={owner.company_id}
                onClick={() => onNavigateToNode?.(owner.company_id, 'company')}
                className="w-full bg-blue-50 hover:bg-blue-100 rounded p-2 flex items-center justify-between transition-colors cursor-pointer"
              >
                <div className="flex items-center space-x-2">
                  <Building2 className="w-4 h-4 text-blue-500" />
                  <span className="text-sm text-blue-600 hover:underline">{owner.name}</span>
                </div>
                {owner.ownership?.confidence && (
                  <span className="text-xs text-gray-400">
                    {formatConfidence(owner.ownership.confidence)}
                  </span>
                )}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-2 flex items-center">
            <AlertCircle className="w-3 h-3 mr-1" />
            Ownership inferred from trial sponsorship
          </p>
        </div>
      )}

      {data.trials?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium mb-2">
            Trials ({data.trials.length}) <span className="text-blue-500 font-normal">— click to focus</span>
          </p>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {data.trials.slice(0, 5).map((trial: any) => (
              <button
                key={trial.trial_id}
                onClick={() => onNavigateToNode?.(trial.trial_id, 'trial')}
                className="w-full text-left bg-amber-50 hover:bg-amber-100 rounded p-2 transition-colors cursor-pointer"
              >
                <p className="text-sm font-medium text-blue-600 hover:underline">{trial.trial_id}</p>
                <p className="text-xs text-gray-600 truncate">{trial.title}</p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TrialDetails({ data, onNavigateToNode }: { data: any; onNavigateToNode?: (nodeId: string, nodeType: string) => void }) {
  // Helper to generate company ID from sponsor name (matches backend logic)
  const getCompanyId = (name: string) => `company_${name.toLowerCase().replace(/[^a-z0-9]+/g, '_')}`;

  return (
    <div className="space-y-3">
      <div>
        <p className="text-xs text-gray-500 uppercase font-medium">Title</p>
        <p className="text-sm text-gray-700">{data.title}</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Phase</p>
          <span className="text-sm bg-amber-100 text-amber-700 px-2 py-0.5 rounded inline-block">
            {formatPhase(data.phase)}
          </span>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Status</p>
          <span className={cn('text-sm', getStatusColor(data.status))}>
            {formatStatus(data.status)}
          </span>
        </div>
      </div>

      {data.enrollment && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Enrollment</p>
          <p className="text-sm text-gray-700">{data.enrollment.toLocaleString()}</p>
        </div>
      )}

      {data.sponsors?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">
            Sponsors <span className="text-blue-500 font-normal">— click to focus</span>
          </p>
          <div className="flex flex-wrap gap-1 mt-1">
            {data.sponsors.map((sponsor: string) => (
              <button
                key={sponsor}
                onClick={() => onNavigateToNode?.(getCompanyId(sponsor), 'company')}
                className="text-xs bg-blue-100 text-blue-700 hover:bg-blue-200 px-2 py-0.5 rounded cursor-pointer transition-colors"
              >
                {sponsor}
              </button>
            ))}
          </div>
        </div>
      )}

      {data.conditions?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Conditions</p>
          <p className="text-sm text-gray-700">{data.conditions.slice(0, 5).join(', ')}</p>
        </div>
      )}

      {data.brief_summary && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Summary</p>
          <p className="text-sm text-gray-600 line-clamp-4">{data.brief_summary}</p>
        </div>
      )}

      {data.source_url && (
        <div className="pt-2">
          <a
            href={data.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:underline flex items-center"
          >
            View on ClinicalTrials.gov
            <ExternalLink className="w-4 h-4 ml-1" />
          </a>
        </div>
      )}
    </div>
  );
}

function DealDetails({ data }: { data: any }) {
  return (
    <div className="space-y-3">
      <div>
        <p className="text-xs text-gray-500 uppercase font-medium">Deal Type</p>
        <span className="text-sm bg-purple-100 text-purple-700 px-2 py-0.5 rounded inline-block capitalize">
          {data.deal_type}
        </span>
      </div>

      {data.announce_date && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Announced</p>
          <p className="text-sm text-gray-700">{data.announce_date}</p>
        </div>
      )}

      {data.status && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Status</p>
          <p className="text-sm text-gray-700 capitalize">{data.status}</p>
        </div>
      )}

      {data.summary && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Summary</p>
          <p className="text-sm text-gray-600">{data.summary}</p>
        </div>
      )}
    </div>
  );
}

function EdgeDetail({ edge }: { edge: GraphEdge }) {
  return (
    <div className="space-y-4 animate-fade-in">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">{edge.type}</h2>
        <p className="text-xs text-gray-400 font-mono mt-1">{edge.id}</p>
      </div>

      <div className="space-y-2">
        <div className="bg-gray-50 rounded p-3">
          <p className="text-xs text-gray-500 uppercase font-medium">From</p>
          <p className="text-sm text-gray-700">
            {typeof edge.source === 'string' ? edge.source : edge.source.id}
          </p>
        </div>

        <div className="text-center text-gray-400">
          ↓ {edge.label || edge.type} ↓
        </div>

        <div className="bg-gray-50 rounded p-3">
          <p className="text-xs text-gray-500 uppercase font-medium">To</p>
          <p className="text-sm text-gray-700">
            {typeof edge.target === 'string' ? edge.target : edge.target.id}
          </p>
        </div>
      </div>

      {edge.data && Object.keys(edge.data).length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium mb-2">Properties</p>
          <div className="space-y-1">
            {Object.entries(edge.data).map(([key, value]) => (
              <div key={key} className="flex justify-between text-sm">
                <span className="text-gray-600">{key}</span>
                <span className="text-gray-800">{String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
