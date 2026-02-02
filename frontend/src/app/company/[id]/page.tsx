'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  Building2,
  ArrowLeft,
  ExternalLink,
  FlaskConical,
  Target,
  FileText,
} from 'lucide-react';
import type { Company } from '@/types';
import { getCompany } from '@/lib/api';
import { cn, formatPhase, formatStatus, getStatusColor } from '@/lib/utils';

export default function CompanyPage() {
  const params = useParams();
  const companyId = params.id as string;

  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (companyId) {
      setLoading(true);
      getCompany(companyId)
        .then(setCompany)
        .catch((err) => {
          console.error(err);
          setError('Failed to load company');
        })
        .finally(() => setLoading(false));
    }
  }, [companyId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error || !company) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700">{error || 'Company not found'}</p>
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
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
              <Building2 className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{company.name}</h1>
              <p className="text-sm text-gray-500 font-mono">{company.company_id}</p>
            </div>
          </div>
          {company.public_flag && company.tickers?.length > 0 && (
            <span className="text-sm bg-gray-100 text-gray-600 px-3 py-1 rounded-full">
              {company.tickers.join(', ')}
            </span>
          )}
        </div>

        {/* Aliases */}
        {company.aliases?.length > 0 && (
          <div className="mt-4">
            <p className="text-xs text-gray-500 uppercase font-medium">Also known as</p>
            <p className="text-sm text-gray-700">{company.aliases.join(', ')}</p>
          </div>
        )}

        {/* Country */}
        {company.country && (
          <div className="mt-3">
            <p className="text-xs text-gray-500 uppercase font-medium">Country</p>
            <p className="text-sm text-gray-700">{company.country}</p>
          </div>
        )}
      </div>

      {/* Trials */}
      {company.trials && company.trials.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <FlaskConical className="w-5 h-5 mr-2 text-amber-500" />
            Clinical Trials ({company.trials.length})
          </h2>
          <div className="space-y-3">
            {company.trials.map((trial: any) => (
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
                  <div className="flex items-center space-x-2 ml-4">
                    {trial.role && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded capitalize">
                        {trial.role.replace('_', ' ')}
                      </span>
                    )}
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
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Assets */}
      {company.assets && company.assets.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <Target className="w-5 h-5 mr-2 text-green-500" />
            Assets ({company.assets.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {company.assets.map((asset: any) => (
              <Link
                key={asset.asset_id}
                href={`/asset/${encodeURIComponent(asset.asset_id)}`}
                className="bg-green-50 rounded-lg p-4 hover:bg-green-100 transition-colors"
              >
                <p className="font-medium text-gray-800">{asset.name}</p>
                {asset.modality && (
                  <span className="text-xs text-green-700 bg-green-200 px-2 py-0.5 rounded mt-1 inline-block">
                    {asset.modality}
                  </span>
                )}
                {asset.ownership?.confidence && (
                  <p className="text-xs text-gray-500 mt-1">
                    Ownership confidence: {Math.round(asset.ownership.confidence * 100)}%
                  </p>
                )}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Evidence */}
      {company.evidence && company.evidence.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <FileText className="w-5 h-5 mr-2 text-gray-500" />
            Data Sources
          </h2>
          <div className="space-y-2">
            {company.evidence.slice(0, 5).map((ev, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                <span className="text-sm text-gray-600 capitalize">{ev.source_type}</span>
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
