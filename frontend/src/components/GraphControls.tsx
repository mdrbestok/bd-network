'use client';

import { useState } from 'react';
import { Settings2, Filter, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TrialFilter } from '@/lib/api';

interface GraphControlsProps {
  trialFilter: TrialFilter;
  onTrialFilterChange: (filter: TrialFilter) => void;
  includeSites: boolean;
  onIncludeSitesChange: (include: boolean) => void;
  pinOnDrag: boolean;
  onPinOnDragChange: (pin: boolean) => void;
  phases: string[];
  selectedPhases: string[];
  onPhasesChange: (phases: string[]) => void;
  modalities: string[];
  selectedModalities: string[];
  onModalitiesChange: (modalities: string[]) => void;
}

const TRIAL_FILTER_OPTIONS: { value: TrialFilter; label: string }[] = [
  { value: 'none', label: 'No trials' },
  { value: 'recruiting', label: 'Recruiting trials' },
  { value: 'active_not_recruiting', label: 'Active, not recruiting' },
  { value: 'all', label: 'All trials' },
];

export default function GraphControls({
  trialFilter,
  onTrialFilterChange,
  includeSites,
  onIncludeSitesChange,
  pinOnDrag,
  onPinOnDragChange,
  phases,
  selectedPhases,
  onPhasesChange,
  modalities,
  selectedModalities,
  onModalitiesChange,
}: GraphControlsProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Settings2 className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">Display Options</span>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs text-blue-600 hover:underline"
        >
          {isExpanded ? 'Less' : 'More'}
        </button>
      </div>

      {/* Basic controls */}
      <div className="space-y-3">
        {/* Include Sites toggle: ON = show sites/academic, OFF = industry only */}
        <div className="flex items-center justify-between">
          <label className="text-xs text-gray-600" title="Turn on to show sites, academic, and non-industry sponsors">
            Include Sites
          </label>
          <button
            onClick={() => onIncludeSitesChange(!includeSites)}
            className={cn(
              'relative w-10 h-5 rounded-full transition-colors',
              includeSites ? 'bg-blue-500' : 'bg-gray-300'
            )}
          >
            <div
              className={cn(
                'absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform shadow',
                includeSites ? 'translate-x-5' : 'translate-x-0.5'
              )}
            />
          </button>
        </div>

        {/* Show trials dropdown */}
        <div>
          <label className="block text-xs text-gray-600 mb-1">Show Trials</label>
          <select
            value={trialFilter}
            onChange={(e) => onTrialFilterChange(e.target.value as TrialFilter)}
            className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 bg-white"
          >
            {TRIAL_FILTER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>


        {/* Pin on drag toggle */}
        <div className="flex items-center justify-between">
          <label className="text-xs text-gray-600" title="When enabled, dragged nodes stay where you place them">
            Pin Nodes on Drag
          </label>
          <button
            onClick={() => onPinOnDragChange(!pinOnDrag)}
            className={cn(
              'relative w-10 h-5 rounded-full transition-colors',
              pinOnDrag ? 'bg-blue-500' : 'bg-gray-300'
            )}
          >
            <div
              className={cn(
                'absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform shadow',
                pinOnDrag ? 'translate-x-5' : 'translate-x-0.5'
              )}
            />
          </button>
        </div>
      </div>

      {/* Expanded filters */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-100 space-y-4">
          {/* Phase filter */}
          {phases.length > 0 && (
            <div>
              <label className="flex items-center text-xs text-gray-600 mb-2">
                <Filter className="w-3 h-3 mr-1" />
                Phase Filter
              </label>
              <div className="flex flex-wrap gap-1">
                {phases.map((phase) => (
                  <button
                    key={phase}
                    onClick={() => {
                      if (selectedPhases.includes(phase)) {
                        onPhasesChange(selectedPhases.filter((p) => p !== phase));
                      } else {
                        onPhasesChange([...selectedPhases, phase]);
                      }
                    }}
                    className={cn(
                      'text-xs px-2 py-1 rounded border transition-colors',
                      selectedPhases.includes(phase)
                        ? 'bg-blue-100 border-blue-300 text-blue-700'
                        : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                    )}
                  >
                    {phase}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Modality filter */}
          {modalities.length > 0 && (
            <div>
              <label className="flex items-center text-xs text-gray-600 mb-2">
                <Filter className="w-3 h-3 mr-1" />
                Modality Filter
              </label>
              <div className="flex flex-wrap gap-1">
                {modalities.map((modality) => (
                  <button
                    key={modality}
                    onClick={() => {
                      if (selectedModalities.includes(modality)) {
                        onModalitiesChange(
                          selectedModalities.filter((m) => m !== modality)
                        );
                      } else {
                        onModalitiesChange([...selectedModalities, modality]);
                      }
                    }}
                    className={cn(
                      'text-xs px-2 py-1 rounded border transition-colors',
                      selectedModalities.includes(modality)
                        ? 'bg-green-100 border-green-300 text-green-700'
                        : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                    )}
                  >
                    {modality}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <p className="text-xs text-gray-500 mb-2">Legend</p>
        <div className="grid grid-cols-2 gap-2">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-xs text-gray-600">Industry Sponsor</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2.5 h-2.5 rounded-full bg-slate-400 opacity-70" />
            <span className="text-xs text-gray-600">Site/Academic</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 rotate-45 bg-green-500" />
            <span className="text-xs text-gray-600">Asset</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-amber-500" />
            <span className="text-xs text-gray-600">Trial</span>
          </div>
        </div>
      </div>
    </div>
  );
}
