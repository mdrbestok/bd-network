'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, AlertCircle, Map } from 'lucide-react';
import LandscapeCards from '@/components/LandscapeCards';
import type { LandscapeData } from '@/types';
import { getLandscape } from '@/lib/api';
import { cn } from '@/lib/utils';

export default function LandscapePage() {
  const [indication, setIndication] = useState('MuM');
  const [data, setData] = useState<LandscapeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadLandscape = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await getLandscape(indication);
      setData(result);
    } catch (err) {
      console.error('Failed to load landscape:', err);
      setError('Failed to load landscape data. Make sure data has been ingested.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLandscape();
  }, [indication]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center">
            <Map className="w-6 h-6 mr-2 text-blue-500" />
            {indication} Landscape
          </h1>
          <p className="text-gray-500 mt-1">
            Competition analysis and standard of care summary
          </p>
        </div>

        <div className="flex items-center space-x-4">
          {/* Indication selector */}
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600">Indication:</label>
            <select
              value={indication}
              onChange={(e) => setIndication(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="MuM">MuM (Mucosal Melanoma)</option>
              {/* Add more indications as they become configured */}
            </select>
          </div>

          <button
            onClick={loadLandscape}
            disabled={loading}
            className={cn(
              'flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              loading
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            )}
          >
            <RefreshCw className={cn('w-4 h-4 mr-2', loading && 'animate-spin')} />
            Refresh
          </button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto" />
            <p className="mt-4 text-gray-500">Loading landscape data...</p>
          </div>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto" />
          <p className="mt-2 text-red-700">{error}</p>
          <p className="mt-1 text-sm text-red-500">
            Run ingestion from the Network page to load data first.
          </p>
        </div>
      ) : data ? (
        <LandscapeCards data={data} />
      ) : null}

      {/* Disclaimer */}
      <div className="mt-8 p-4 bg-gray-50 rounded-xl border border-gray-200">
        <p className="text-xs text-gray-500 text-center">
          <strong>Disclaimer:</strong> This landscape analysis is derived from publicly
          available clinical trial data from ClinicalTrials.gov. It is intended for
          informational purposes only and does not constitute medical advice. Treatment
          decisions should be based on consultation with qualified healthcare
          professionals and current clinical guidelines.
        </p>
      </div>
    </div>
  );
}
