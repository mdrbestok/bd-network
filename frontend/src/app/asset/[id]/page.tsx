'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  Target,
  ArrowLeft,
  ExternalLink,
  FlaskConical,
  Building2,
  FileText,
  AlertCircle,
} from 'lucide-react';
import type { Asset } from '@/types';
import { getAsset } from '@/lib/api';
import { cn, formatPhase, formatStatus, getStatusColor, formatConfidence } from '@/lib/utils';

export default function AssetPage() {
  const params = useParams();
  const assetId = params.id as string;

  const [asset, setAsset] = useState<Asset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (assetId) {
      setLoading(true);
      getAsset(assetId)
        .then(setAsset)
        .catch((err) => {
          console.error(err);
          setError('Failed to load asset');
        })
        .finally(() => setLoading(false));
    }
  }, [assetId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500" />
      </div>
    );
  }

  if (error || !asset) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700">{error || 'Asset not found'}</p>
          <Link href="/" className="text-blue-500 hover:underline mt-2 inline-block">
            Back to Network
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Back link */}
      <Link
        href="/"
        className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4 mr-1" />
        Back to Network
      </Link>

      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <Target className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{asset.name}</h1>
              <p className="text-sm text-gray-500 font-mono">{asset.asset_id}</p>
            </div>
          </div>
          {asset.stage_current && (
            <span className="text-sm bg-amber-100 text-amber-700 px-3 py-1 rounded-full capitalize">
              {asset.stage_current}
            </span>
          )}
        </div>

        {/* Synonyms */}
        {asset.synonyms?.length > 0 && (
          <div className="mt-4">
            <p className="text-xs text-gray-500 uppercase font-medium">Synonyms</p>
            <p className="text-sm text-gray-700">{asset.synonyms.join(', ')}</p>
          </div>
        )}

        {/* Modality */}
        {asset.modality && (
          <div className="mt-3">
            <p className="text-xs text-gray-500 uppercase font-medium">Modality</p>
            <div className="flex items-center space-x-2">
              <span className="text-sm bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                {asset.modality}
              </span>
              {asset.modality_confidence && (
                <span className="text-xs text-gray-400">
                  ({formatConfidence(asset.modality_confidence)} confidence)
                </span>
              )}
            </div>
          </div>
        )}

        {/* Targets */}
        {asset.targets?.length > 0 && (
          <div className="mt-3">
            <p className="text-xs text-gray-500 uppercase font-medium">Molecular Targets</p>
            <div className="flex flex-wrap gap-1 mt-1">
              {asset.targets.map((target) => (
                <span
                  key={target}
                  className="text-sm bg-teal-100 text-teal-700 px-2 py-0.5 rounded"
                >
                  {target}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Indications */}
        {asset.indications?.length > 0 && (
          <div className="mt-3">
            <p className="text-xs text-gray-500 uppercase font-medium">Indications</p>
            <p className="text-sm text-gray-700">{asset.indications.slice(0, 5).join(', ')}</p>
          </div>
        )}
      </div>

      {/* Ownership / Lineage */}
      {asset.owners && asset.owners.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <Building2 className="w-5 h-5 mr-2 text-blue-500" />
            Ownership (Inferred)
          </h2>
          <div className="space-y-3">
            {asset.owners.map((owner: any) => (
              <Link
                key={owner.company_id}
                href={`/company/${encodeURIComponent(owner.company_id)}`}
                className="flex items-center justify-between bg-blue-50 rounded-lg p-4 hover:bg-blue-100 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <Building2 className="w-5 h-5 text-blue-500" />
                  <span className="font-medium text-gray-800">{owner.name}</span>
                </div>
                {owner.ownership?.confidence && (
                  <span className="text-sm text-gray-500">
                    {formatConfidence(owner.ownership.confidence)} confidence
                  </span>
                )}
              </Link>
            ))}
          </div>
          <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-xs text-amber-800 flex items-start">
              <AlertCircle className="w-4 h-4 mr-1 flex-shrink-0" />
              Ownership is inferred from trial sponsorship data. This may not reflect
              current ownership or licensing arrangements.
            </p>
          </div>
        </div>
      )}

      {/* Trials */}
      {asset.trials && asset.trials.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <FlaskConical className="w-5 h-5 mr-2 text-amber-500" />
            Clinical Trials ({asset.trials.length})
          </h2>
          <div className="space-y-3">
            {asset.trials.map((trial: any) => (
              <div
                key={trial.trial_id}
                className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <a
                      href={trial.source_url || `https://clinicaltrials.gov/study/${trial.trial_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium text-blue-600 hover:underline flex items-center"
                    >
                      {trial.trial_id}
                      <ExternalLink className="w-3 h-3 ml-1" />
                    </a>
                    <p className="text-sm text-gray-700 mt-1">{trial.title}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-3 mt-2">
                  <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">
                    {formatPhase(trial.phase)}
                  </span>
                  <span className={cn('text-xs', getStatusColor(trial.status))}>
                    {formatStatus(trial.status)}
                  </span>
                </div>
                {trial.sponsors?.length > 0 && (
                  <div className="mt-2">
                    <span className="text-xs text-gray-500">Sponsors: </span>
                    <span className="text-xs text-gray-700">{trial.sponsors.join(', ')}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence */}
      {asset.evidence && asset.evidence.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <FileText className="w-5 h-5 mr-2 text-gray-500" />
            Data Sources
          </h2>
          <div className="space-y-2">
            {asset.evidence.slice(0, 5).map((ev, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                <div>
                  <span className="text-sm text-gray-600 capitalize">{ev.source_type}</span>
                  {ev.source_id && (
                    <span className="text-xs text-gray-400 ml-2">({ev.source_id})</span>
                  )}
                </div>
                {ev.source_url && (
                  <a
                    href={ev.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-500 hover:underline flex items-center"
                  >
                    View
                    <ExternalLink className="w-3 h-3 ml-1" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
