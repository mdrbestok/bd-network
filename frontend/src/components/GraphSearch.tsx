'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, X, Building2, Target, FlaskConical } from 'lucide-react';
import type { GraphNode, NodeType } from '@/types';
import { cn, nodeColorsBgLight, nodeColorsText } from '@/lib/utils';

interface GraphSearchProps {
  nodes: GraphNode[];
  onSelectNode: (node: GraphNode) => void;
  onHighlightNode: (nodeId: string | null) => void;
}

export default function GraphSearch({
  nodes,
  onSelectNode,
  onHighlightNode,
}: GraphSearchProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [results, setResults] = useState<GraphNode[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Search nodes when query changes
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    const searchTerm = query.toLowerCase();
    const matched = nodes
      .filter((node) => {
        const label = node.label?.toLowerCase() || '';
        const name = (node.data as any)?.name?.toLowerCase() || '';
        const synonyms = ((node.data as any)?.synonyms || []).join(' ').toLowerCase();
        const aliases = ((node.data as any)?.aliases || []).join(' ').toLowerCase();
        
        return (
          label.includes(searchTerm) ||
          name.includes(searchTerm) ||
          synonyms.includes(searchTerm) ||
          aliases.includes(searchTerm)
        );
      })
      .slice(0, 10);

    setResults(matched);
    setIsOpen(matched.length > 0);
    setSelectedIndex(0);
  }, [query, nodes]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!isOpen) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (results[selectedIndex]) {
          handleSelect(results[selectedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        setQuery('');
        onHighlightNode(null);
        break;
    }
  }, [isOpen, results, selectedIndex]);

  // Handle selection
  const handleSelect = (node: GraphNode) => {
    onSelectNode(node);
    onHighlightNode(node.id);
    setIsOpen(false);
    setQuery(node.label);
  };

  // Highlight on hover
  const handleResultHover = (node: GraphNode) => {
    onHighlightNode(node.id);
  };

  // Clear search
  const handleClear = () => {
    setQuery('');
    setResults([]);
    setIsOpen(false);
    onHighlightNode(null);
    inputRef.current?.focus();
  };

  // Get icon for node type
  const getIcon = (type: NodeType) => {
    switch (type) {
      case 'company':
        return <Building2 className="w-4 h-4" />;
      case 'asset':
        return <Target className="w-4 h-4" />;
      case 'trial':
        return <FlaskConical className="w-4 h-4" />;
      default:
        return null;
    }
  };

  return (
    <div className="relative">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          placeholder="Search companies, assets..."
          className="w-full pl-10 pr-10 py-2.5 bg-white border border-gray-300 rounded-lg 
                     focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     text-sm placeholder-gray-400"
        />
        {query && (
          <button
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 
                       hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-4 h-4 text-gray-400" />
          </button>
        )}
      </div>

      {/* Results Dropdown */}
      {isOpen && results.length > 0 && (
        <div
          ref={resultsRef}
          className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 
                     rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto"
        >
          {results.map((node, index) => (
            <button
              key={node.id}
              onClick={() => handleSelect(node)}
              onMouseEnter={() => {
                setSelectedIndex(index);
                handleResultHover(node);
              }}
              className={cn(
                'w-full px-3 py-2.5 flex items-center space-x-3 text-left transition-colors',
                index === selectedIndex ? 'bg-blue-50' : 'hover:bg-gray-50'
              )}
            >
              <div
                className={cn(
                  'p-1.5 rounded-md',
                  nodeColorsBgLight[node.type],
                  nodeColorsText[node.type]
                )}
              >
                {getIcon(node.type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {node.label}
                </p>
                <p className="text-xs text-gray-500 capitalize">{node.type}</p>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* No results message */}
      {isOpen && query && results.length === 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 
                        rounded-lg shadow-lg z-50 p-4 text-center">
          <p className="text-sm text-gray-500">No results found</p>
        </div>
      )}
    </div>
  );
}
