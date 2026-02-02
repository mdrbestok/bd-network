'use client';

import {
  BarChart3,
  Building2,
  FlaskConical,
  Target,
  AlertTriangle,
  ExternalLink,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import type { LandscapeData } from '@/types';
import { cn, formatPhase } from '@/lib/utils';

interface LandscapeCardsProps {
  data: LandscapeData;
}

export default function LandscapeCards({ data }: LandscapeCardsProps) {
  return (
    <div className="space-y-6">
      {/* Summary stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          icon={<FlaskConical className="w-5 h-5 text-amber-500" />}
          label="Clinical Trials"
          value={data.total_trials}
          bgColor="bg-amber-50"
        />
        <StatCard
          icon={<Target className="w-5 h-5 text-green-500" />}
          label="Assets/Compounds"
          value={data.total_assets}
          bgColor="bg-green-50"
        />
        <StatCard
          icon={<Building2 className="w-5 h-5 text-blue-500" />}
          label="Companies"
          value={data.total_companies}
          bgColor="bg-blue-50"
        />
      </div>

      {/* Phase distribution */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <BarChart3 className="w-5 h-5 mr-2 text-gray-500" />
          Trials by Phase
        </h3>
        {data.assets_by_phase.length > 0 ? (
          <div className="space-y-3">
            {data.assets_by_phase.map((item) => (
              <div key={item.phase} className="flex items-center">
                <span className="w-24 text-sm text-gray-600">
                  {formatPhase(item.phase)}
                </span>
                <div className="flex-1 mx-3">
                  <div className="h-6 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-amber-400 to-amber-500 rounded-full"
                      style={{
                        width: `${Math.min(
                          100,
                          (item.count / Math.max(...data.assets_by_phase.map((p) => p.count))) * 100
                        )}%`,
                      }}
                    />
                  </div>
                </div>
                <span className="w-12 text-right text-sm font-medium text-gray-700">
                  {item.count}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">No phase data available</p>
        )}
      </div>

      {/* Top sponsors */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <Building2 className="w-5 h-5 mr-2 text-gray-500" />
          Top Sponsors by Trial Count
        </h3>
        {data.sponsors_by_trial_count.length > 0 ? (
          <div className="space-y-2">
            {data.sponsors_by_trial_count.slice(0, 10).map((item, index) => (
              <div
                key={item.id}
                className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
              >
                <div className="flex items-center">
                  <span className="w-6 text-sm text-gray-400">{index + 1}.</span>
                  <span className="text-sm text-gray-700">{item.sponsor}</span>
                </div>
                <span className="text-sm font-medium text-blue-600">
                  {item.trial_count} trials
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">No sponsor data available</p>
        )}
      </div>

      {/* Modalities and Targets */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Modalities */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Modalities</h3>
          {data.modalities.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {data.modalities.map((item) => (
                <span
                  key={item.modality}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-purple-100 text-purple-700"
                >
                  {item.modality}
                  <span className="ml-2 text-xs bg-purple-200 px-1.5 py-0.5 rounded-full">
                    {item.count}
                  </span>
                </span>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">Modality data being extracted...</p>
          )}
        </div>

        {/* Targets */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Molecular Targets</h3>
          {data.targets.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {data.targets.map((item) => (
                <span
                  key={item.target}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-teal-100 text-teal-700"
                >
                  {item.target}
                  <span className="ml-2 text-xs bg-teal-200 px-1.5 py-0.5 rounded-full">
                    {item.count}
                  </span>
                </span>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">Target data being extracted...</p>
          )}
        </div>
      </div>

      {/* Standard of Care */}
      <StandardOfCareCard soc={data.standard_of_care} indication={data.indication} />
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  bgColor,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  bgColor: string;
}) {
  return (
    <div className={cn('rounded-xl p-6', bgColor)}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">{label}</p>
          <p className="text-3xl font-bold text-gray-800 mt-1">{value}</p>
        </div>
        {icon}
      </div>
    </div>
  );
}

function StandardOfCareCard({
  soc,
  indication,
}: {
  soc: LandscapeData['standard_of_care'];
  indication: string;
}) {
  if (!soc.placeholder_info) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <AlertTriangle className="w-5 h-5 mr-2 text-amber-500" />
          Standard of Care
        </h3>
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <p className="text-gray-500">{soc.note}</p>
          <p className="text-xs text-gray-400 mt-2">
            Standard of care information requires validated medical sources
          </p>
        </div>
      </div>
    );
  }

  const info = soc.placeholder_info;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800 flex items-center">
          <AlertTriangle className="w-5 h-5 mr-2 text-amber-500" />
          Standard of Care - {info.indication_full_name}
        </h3>
        {info.needs_citation && (
          <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded-full">
            NEEDS CITED SOURCES
          </span>
        )}
      </div>

      {/* Disclaimer */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
        <p className="text-xs text-amber-800">{info.disclaimer}</p>
      </div>

      {/* Summary */}
      <p className="text-sm text-gray-700 mb-4">{info.summary}</p>

      {/* Key Agents */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-2">Key Agents</h4>
        <div className="space-y-2">
          {info.key_agents.map((agent) => (
            <div
              key={agent.name}
              className="flex items-start justify-between bg-gray-50 rounded-lg p-3"
            >
              <div className="flex items-center space-x-2">
                {agent.approved ? (
                  <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                ) : (
                  <XCircle className="w-4 h-4 text-gray-400 flex-shrink-0" />
                )}
                <div>
                  <p className="text-sm font-medium text-gray-800">{agent.name}</p>
                  <p className="text-xs text-gray-500">{agent.notes}</p>
                </div>
              </div>
              {agent.approved && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                  Approved
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-gray-400 mt-4 flex items-center">
        <AlertTriangle className="w-3 h-3 mr-1" />
        This is placeholder information for demonstration. Clinical decisions should be
        based on current guidelines.
      </p>
    </div>
  );
}
