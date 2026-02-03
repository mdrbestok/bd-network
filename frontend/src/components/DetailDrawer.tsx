'use client';

import { useState, useCallback, useEffect } from 'react';
import { X, ExternalLink, AlertCircle, Building2, Check, Plus } from 'lucide-react';
import type { GraphNode, GraphEdge, Company, Asset, Trial } from '@/types';
import {
  cn,
  nodeColorsBg,
  nodeColorsText,
  formatPhase,
  formatStatus,
  getStatusColor,
  formatConfidence,
  sortTrialsActiveFirst,
} from '@/lib/utils';
import { updateAsset, search } from '@/lib/api';

interface DetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  node?: GraphNode | null;
  edge?: GraphEdge | null;
  entityData?: Company | Asset | Trial | null;
  loading?: boolean;
  onNavigateToNode?: (nodeId: string, nodeType: string) => void;
  onRefreshEntity?: () => void;
}

export default function DetailDrawer({
  isOpen,
  onClose,
  node,
  edge,
  entityData,
  loading,
  onNavigateToNode,
  onRefreshEntity,
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
          <NodeDetail node={node} entityData={entityData} onNavigateToNode={onNavigateToNode} onRefreshEntity={onRefreshEntity} />
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
  onRefreshEntity,
}: {
  node: GraphNode;
  entityData?: Company | Asset | Trial | null;
  onNavigateToNode?: (nodeId: string, nodeType: string) => void;
  onRefreshEntity?: () => void;
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
      {node.type === 'asset' && <AssetDetails assetId={node.id} data={data as any} onNavigateToNode={onNavigateToNode} onRefreshEntity={onRefreshEntity} />}
      {node.type === 'trial' && <TrialDetails data={data as any} onNavigateToNode={onNavigateToNode} />}
      {node.type === 'deal' && <DealDetails data={data as any} />}

      {/* Evidence - compact one-liner */}
      {(data as any)?.evidence?.[0]?.source_url && (
        <p className="text-xs text-gray-500 pt-2 border-t border-gray-100">
          Source:{' '}
          <a
            href={(data as any).evidence[0].source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline inline-flex items-center"
          >
            {(data as any).evidence[0].source_type || 'View'}
            <ExternalLink className="w-3 h-3 ml-0.5" />
          </a>
        </p>
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
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {sortTrialsActiveFirst(data.trials).slice(0, 20).map((trial: any) => (
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

const MODALITY_OPTIONS = [
  'antibody',
  'small_molecule',
  'chemotherapy',
  'bispecific',
  'cell_therapy',
  'vaccine',
  'adc',
  'gene_therapy',
  'oncolytic_virus',
  'checkpoint_inhibitor',
  'peptide',
  'protein',
  'radiation',
  'other',
];

function AssetDetails({
  assetId,
  data,
  onNavigateToNode,
  onRefreshEntity,
}: {
  assetId: string;
  data: any;
  onNavigateToNode?: (nodeId: string, nodeType: string) => void;
  onRefreshEntity?: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editModality, setEditModality] = useState(data?.modality ?? '');
  const [editTargets, setEditTargets] = useState<string[]>(data?.targets ?? []);
  const [newTarget, setNewTarget] = useState('');
  const [ownerSearch, setOwnerSearch] = useState('');
  const [ownerSearchResults, setOwnerSearchResults] = useState<{ company_id: string; name: string }[]>([]);
  const [selectedOwnerId, setSelectedOwnerId] = useState<string | null>(null);
  const [newOwnerName, setNewOwnerName] = useState('');
  const [relationshipType, setRelationshipType] = useState('owns');
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    setEditModality(data?.modality ?? '');
    setEditTargets(data?.targets ?? []);
  }, [data?.modality, data?.targets]);

  const runOwnerSearch = useCallback(async (q: string) => {
    if (q.length < 2) {
      setOwnerSearchResults([]);
      return;
    }
    try {
      const res = await search(q, 10);
      const companies = (res.companies ?? []).map((c: any) => ({ company_id: c.company_id, name: c.name }));
      setOwnerSearchResults(companies);
    } catch {
      setOwnerSearchResults([]);
    }
  }, []);

  const handleSave = async () => {
    setSaveError(null);
    setSaving(true);
    try {
      const payload: { 
        modality?: string; 
        targets?: string[]; 
        owner_company_id?: string; 
        owner_company_name?: string;
        relationship_type?: string;
      } = {};
      if (editModality.trim()) payload.modality = editModality.trim();
      if (editTargets.length) payload.targets = editTargets;
      if (selectedOwnerId) {
        payload.owner_company_id = selectedOwnerId;
        payload.relationship_type = relationshipType;
      }
      if (newOwnerName.trim()) {
        payload.owner_company_name = newOwnerName.trim();
        payload.relationship_type = relationshipType;
      }
      await updateAsset(assetId, payload);
      if (onRefreshEntity) await onRefreshEntity();
      setEditing(false);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Save failed';
      setSaveError(message);
    } finally {
      setSaving(false);
    }
  };

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
          <div className="flex items-center flex-wrap gap-2">
            <span className="text-sm text-gray-700">{data.modality}</span>
            {data.modality_user_confirmed && (
              <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">User confirmed</span>
            )}
            {data.modality_confidence && !data.modality_user_confirmed && (
              <span className="text-xs text-gray-400">({formatConfidence(data.modality_confidence)} confidence)</span>
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
            {data.targets_user_confirmed && (
              <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">User confirmed</span>
            )}
          </div>
        </div>
      )}

      {data.stage_current && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium">Stage</p>
          <p className="text-sm text-gray-700">{formatPhase(data.stage_current)}</p>
        </div>
      )}

      {/* Connected Companies (Industry) - owns, licenses, comparator */}
      {(() => {
        const allConnected = data.connected_companies || data.owners || [];
        // Industry companies: owns, licenses, comparator relationships
        const industryCompanies = allConnected.filter((c: any) => {
          const relType = c.relationship_type || c.relationship?.type;
          const isIndustry = c.company_type === 'industry' || !c.company_type;
          const isIndustryRelation = relType === 'owns' || relType === 'licenses' || relType === 'uses_as_comparator';
          return isIndustry && isIndustryRelation;
        });
        // Sites: participates_in_trial OR any non-industry company type
        const sites = allConnected.filter((c: any) => {
          const relType = c.relationship_type || c.relationship?.type;
          const isNonIndustry = c.company_type && c.company_type !== 'industry';
          const isSiteRelation = relType === 'participates_in_trial';
          return isNonIndustry || isSiteRelation;
        });
        
        return (
          <>
            {industryCompanies.length > 0 && (
              <div>
                <p className="text-xs text-gray-500 uppercase font-medium mb-2">
                  Connected Companies <span className="text-blue-500 font-normal">— click to focus</span>
                </p>
                <div className="space-y-2">
                  {industryCompanies.map((company: any) => {
                    const relType = company.relationship_type || company.relationship?.type || 'owns';
                    const relColors: Record<string, { bg: string; text: string; label: string }> = {
                      owns: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'Owns' },
                      licenses: { bg: 'bg-purple-50', text: 'text-purple-700', label: 'Licenses' },
                      uses_as_comparator: { bg: 'bg-orange-50', text: 'text-orange-700', label: 'Comparator' },
                    };
                    const colors = relColors[relType] || relColors.owns;
                    
                    return (
                      <div
                        key={`${company.company_id}-${relType}`}
                        className={cn('flex items-center gap-2 w-full rounded p-2', colors.bg)}
                      >
                        <button
                          type="button"
                          onClick={() => onNavigateToNode?.(company.company_id, 'company')}
                          className="flex-1 flex items-center justify-between text-left min-w-0"
                        >
                          <div className="flex items-center space-x-2 min-w-0">
                            <Building2 className={cn('w-4 h-4 flex-shrink-0', colors.text)} />
                            <span className={cn('text-sm hover:underline truncate', colors.text)}>{company.name}</span>
                            <span className={cn('text-xs px-1.5 py-0.5 rounded flex-shrink-0', colors.bg, colors.text)}>
                              {colors.label}
                            </span>
                            {company.relationship?.user_confirmed && (
                              <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded flex-shrink-0">✓</span>
                            )}
                          </div>
                          {company.relationship?.confidence && !company.relationship?.user_confirmed && (
                            <span className="text-xs text-gray-400 flex-shrink-0 ml-1">{formatConfidence(company.relationship.confidence)}</span>
                          )}
                        </button>
                        {!company.relationship?.user_confirmed && relType === 'owns' && (
                          <button
                            type="button"
                            onClick={async () => {
                              try {
                                await updateAsset(assetId, { owner_company_id: company.company_id });
                                onRefreshEntity?.();
                              } catch (e) {
                                setSaveError(e instanceof Error ? e.message : 'Confirm failed');
                              }
                            }}
                            className="flex-shrink-0 text-xs font-medium text-green-700 bg-green-100 hover:bg-green-200 px-2 py-1 rounded"
                          >
                            Confirm
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
                {!industryCompanies.some((c: any) => c.relationship?.user_confirmed || c.ownership?.user_confirmed) && (
                  <p className="text-xs text-gray-400 mt-2 flex items-center">
                    <AlertCircle className="w-3 h-3 mr-1" />
                    Inferred from trials — click Confirm to lock ownership
                  </p>
                )}
              </div>
            )}
            
            {sites.length > 0 && (
              <div className="mt-3">
                <p className="text-xs text-gray-500 uppercase font-medium mb-2">
                  Connected Sites <span className="text-gray-400 font-normal">— participate in trials</span>
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {sites.slice(0, 10).map((site: any) => (
                    <button
                      key={site.company_id}
                      onClick={() => onNavigateToNode?.(site.company_id, 'company')}
                      className="text-xs bg-gray-100 text-gray-600 hover:bg-gray-200 px-2 py-1 rounded cursor-pointer transition-colors"
                      title={site.company_type}
                    >
                      {site.name}
                    </button>
                  ))}
                  {sites.length > 10 && (
                    <span className="text-xs text-gray-400 px-2 py-1">+{sites.length - 10} more</span>
                  )}
                </div>
              </div>
            )}
          </>
        );
      })()}

      {/* Confirm / Edit section */}
      <div className="pt-4 border-t border-gray-200">
        <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
          <Check className="w-4 h-4 mr-1.5 text-green-600" />
          Confirm or edit
        </h3>
        <p className="text-xs text-gray-500 mb-3">
          Your changes are kept on the next sync.
        </p>
        {!editing ? (
          <button
            type="button"
            onClick={() => { setEditing(true); setSaveError(null); }}
            className="w-full text-sm py-2 px-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
          >
            Edit modality, targets, or owner
          </button>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-gray-500 uppercase font-medium mb-1">Modality</label>
              <select
                value={editModality}
                onChange={(e) => setEditModality(e.target.value)}
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2"
              >
                <option value="">—</option>
                {MODALITY_OPTIONS.map((m) => (
                  <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 uppercase font-medium mb-1">Targets (molecular)</label>
              <div className="flex flex-wrap gap-1 mb-1">
                {editTargets.map((t) => (
                  <span
                    key={t}
                    className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded flex items-center gap-1"
                  >
                    {t}
                    <button
                      type="button"
                      onClick={() => setEditTargets((prev) => prev.filter((x) => x !== t))}
                      className="text-purple-500 hover:text-purple-700"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-1">
                <input
                  type="text"
                  value={newTarget}
                  onChange={(e) => setNewTarget(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newTarget.trim()) {
                      setEditTargets((prev) => [...prev, newTarget.trim()]);
                      setNewTarget('');
                    }
                  }}
                  placeholder="Add target (e.g. PD-1)"
                  className="flex-1 text-sm border border-gray-300 rounded-lg px-2 py-1"
                />
                <button
                  type="button"
                  onClick={() => {
                    if (newTarget.trim()) {
                      setEditTargets((prev) => [...prev, newTarget.trim()]);
                      setNewTarget('');
                    }
                  }}
                  className="text-sm px-2 py-1 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div>
              <label className="block text-xs text-gray-500 uppercase font-medium mb-1">Company Relationship</label>
              <input
                type="text"
                value={ownerSearch}
                onChange={(e) => {
                  setOwnerSearch(e.target.value);
                  runOwnerSearch(e.target.value);
                }}
                placeholder="Search existing sponsor"
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 mb-1"
              />
              {ownerSearchResults.length > 0 && (
                <ul className="border border-gray-200 rounded-lg divide-y max-h-32 overflow-y-auto mb-2">
                  {ownerSearchResults.map((c) => (
                    <li key={c.company_id}>
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedOwnerId(c.company_id);
                          setOwnerSearch(c.name);
                          setOwnerSearchResults([]);
                        }}
                        className="w-full text-left text-sm px-3 py-2 hover:bg-gray-50"
                      >
                        {c.name}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <input
                type="text"
                value={newOwnerName}
                onChange={(e) => setNewOwnerName(e.target.value)}
                placeholder="Or add new company by name"
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 mb-2"
              />
              {(selectedOwnerId || newOwnerName.trim()) && (
                <>
                  <label className="block text-xs text-gray-500 uppercase font-medium mb-1 mt-2">Relationship Type</label>
                  <select
                    value={relationshipType}
                    onChange={(e) => setRelationshipType(e.target.value)}
                    className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2"
                  >
                    <option value="owns">Owns</option>
                    <option value="licenses">Licenses</option>
                    <option value="uses_as_comparator">Uses as Comparator</option>
                  </select>
                  <p className="text-xs text-green-600 mt-1">
                    Will set company relationship on save
                  </p>
                </>
              )}
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="flex-1 text-sm py-2 px-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button
                type="button"
                onClick={() => { setEditing(false); setSaveError(null); }}
                className="text-sm py-2 px-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
            {saveError && (
              <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 mt-2">
                {saveError}
              </p>
            )}
          </div>
        )}
      </div>

      {data.trials?.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase font-medium mb-2">
            Trials ({data.trials.length}) <span className="text-blue-500 font-normal">— click to focus</span>
          </p>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {sortTrialsActiveFirst(data.trials).slice(0, 20).map((trial: any) => (
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
