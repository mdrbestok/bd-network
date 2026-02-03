import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { NodeType } from '@/types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Node type colors for graph visualization
export const nodeColors: Record<NodeType, string> = {
  company: '#3b82f6', // blue
  asset: '#10b981', // green
  trial: '#f59e0b', // amber
  deal: '#8b5cf6', // purple
};

export const nodeColorsBg: Record<NodeType, string> = {
  company: 'bg-blue-500',
  asset: 'bg-green-500',
  trial: 'bg-amber-500',
  deal: 'bg-purple-500',
};

export const nodeColorsBgLight: Record<NodeType, string> = {
  company: 'bg-blue-100',
  asset: 'bg-green-100',
  trial: 'bg-amber-100',
  deal: 'bg-purple-100',
};

export const nodeColorsText: Record<NodeType, string> = {
  company: 'text-blue-600',
  asset: 'text-green-600',
  trial: 'text-amber-600',
  deal: 'text-purple-600',
};

export const nodeColorsBorder: Record<NodeType, string> = {
  company: 'border-blue-500',
  asset: 'border-green-500',
  trial: 'border-amber-500',
  deal: 'border-purple-500',
};

// Edge type styles
export const edgeStyles: Record<string, { color: string; dashed: boolean }> = {
  OWNS: { color: '#6b7280', dashed: false },
  DEVELOPS: { color: '#3b82f6', dashed: false }, // Blue for company-asset via trial
  SPONSORS_TRIAL: { color: '#9ca3af', dashed: true },
  HAS_TRIAL: { color: '#d1d5db', dashed: true },
  PARTY_TO: { color: '#a855f7', dashed: false },
  COVERS: { color: '#22c55e', dashed: false },
};

// Format phase for display
export function formatPhase(phase?: string): string {
  if (!phase) return 'Unknown';
  
  const phaseMap: Record<string, string> = {
    'PHASE1': 'Phase 1',
    'PHASE2': 'Phase 2',
    'PHASE3': 'Phase 3',
    'PHASE4': 'Phase 4',
    'EARLY_PHASE1': 'Early Phase 1',
    'NOT_APPLICABLE': 'N/A',
  };
  
  return phaseMap[phase.toUpperCase()] || phase;
}

// Format trial status
export function formatStatus(status?: string): string {
  if (!status) return 'Unknown';
  
  const statusMap: Record<string, string> = {
    'RECRUITING': 'Recruiting',
    'ACTIVE_NOT_RECRUITING': 'Active, not recruiting',
    'COMPLETED': 'Completed',
    'TERMINATED': 'Terminated',
    'WITHDRAWN': 'Withdrawn',
    'SUSPENDED': 'Suspended',
    'NOT_YET_RECRUITING': 'Not yet recruiting',
    'ENROLLING_BY_INVITATION': 'Enrolling by invitation',
  };
  
  return statusMap[status.toUpperCase().replace(', ', '_').replace(' ', '_')] || status;
}

// Get status color
export function getStatusColor(status?: string): string {
  if (!status) return 'text-gray-500';
  
  const s = status.toLowerCase();
  if (s.includes('recruit')) return 'text-green-600';
  if (s.includes('active')) return 'text-blue-600';
  if (s.includes('completed')) return 'text-gray-600';
  if (s.includes('terminated') || s.includes('withdrawn')) return 'text-red-600';
  if (s.includes('suspended')) return 'text-amber-600';
  
  return 'text-gray-500';
}

/** Sort order for trial status: active first, then completed, then terminated/withdrawn */
const TRIAL_STATUS_ORDER: Record<string, number> = {
  RECRUITING: 0,
  NOT_YET_RECRUITING: 1,
  ACTIVE_NOT_RECRUITING: 2,
  ENROLLING_BY_INVITATION: 3,
  SUSPENDED: 4,
  COMPLETED: 5,
  TERMINATED: 6,
  WITHDRAWN: 7,
};

export function sortTrialsActiveFirst(trials: { status?: string }[]): typeof trials {
  return [...trials].sort((a, b) => {
    const orderA = TRIAL_STATUS_ORDER[a.status?.toUpperCase() ?? ''] ?? 10;
    const orderB = TRIAL_STATUS_ORDER[b.status?.toUpperCase() ?? ''] ?? 10;
    return orderA - orderB;
  });
}

// Truncate text
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

// Format confidence score
export function formatConfidence(confidence?: number): string {
  if (confidence === undefined || confidence === null) return '';
  return `${Math.round(confidence * 100)}%`;
}
