'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';

// Graph area dimensions (sidebar ~320px, padding, drawer possible)
const SIDEBAR_WIDTH = 320;
const PADDING_X = 32;
const PADDING_Y = 128;

function useGraphDimensions() {
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    const update = () => {
      setDimensions({
        width: Math.max(400, window.innerWidth - SIDEBAR_WIDTH - PADDING_X),
        height: Math.max(300, window.innerHeight - PADDING_Y),
      });
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  return dimensions;
}
import { Search, RefreshCw, Database, AlertCircle, X, Focus, ArrowLeft, Link2 } from 'lucide-react';
import NetworkGraph from '@/components/NetworkGraph';
import DetailDrawer from '@/components/DetailDrawer';
import GraphControls from '@/components/GraphControls';
import GraphSearch from '@/components/GraphSearch';
import type { GraphNode, GraphEdge, GraphData, Company, Asset, Trial } from '@/types';
import { getIndicationGraph, getCompany, getAsset, getTrial, getHealth, ingestClinicalTrials, type TrialFilter } from '@/lib/api';
import { cn } from '@/lib/utils';

// Helper to get edge endpoint IDs safely
function getEdgeEndpoints(edge: GraphEdge): { sourceId: string; targetId: string } {
  const sourceId = typeof edge.source === 'string' 
    ? edge.source 
    : (edge.source as any)?.id || String(edge.source);
  const targetId = typeof edge.target === 'string' 
    ? edge.target 
    : (edge.target as any)?.id || String(edge.target);
  return { sourceId, targetId };
}

// Helper function to get nodes within N hops of a target node
function getNodesWithinHops(
  targetNodeId: string,
  allNodes: GraphNode[],
  allEdges: GraphEdge[],
  maxHops: number
): GraphData {
  // Track node distances from target
  const nodeDistances = new Map<string, number>();
  nodeDistances.set(targetNodeId, 0);
  
  // Build adjacency map using node IDs
  const adjacency = new Map<string, Set<string>>();
  const edgeMap = new Map<string, GraphEdge>(); // edge key -> edge
  
  for (const edge of allEdges) {
    const { sourceId, targetId } = getEdgeEndpoints(edge);
    
    if (!adjacency.has(sourceId)) adjacency.set(sourceId, new Set());
    if (!adjacency.has(targetId)) adjacency.set(targetId, new Set());
    
    adjacency.get(sourceId)!.add(targetId);
    adjacency.get(targetId)!.add(sourceId);
    
    // Store edge by both directions for lookup
    edgeMap.set(`${sourceId}-${targetId}`, edge);
    edgeMap.set(`${targetId}-${sourceId}`, edge);
  }
  
  // BFS to find nodes within N hops
  let frontier = [targetNodeId];
  
  for (let distance = 1; distance <= maxHops; distance++) {
    const nextFrontier: string[] = [];
    
    for (const nodeId of frontier) {
      const neighbors = adjacency.get(nodeId);
      if (!neighbors) continue;
      
      for (const neighborId of neighbors) {
        if (!nodeDistances.has(neighborId)) {
          nodeDistances.set(neighborId, distance);
          nextFrontier.push(neighborId);
        }
      }
    }
    
    frontier = nextFrontier;
    if (frontier.length === 0) break;
  }
  
  // Get all nodes within hop distance
  const includedNodeIds = new Set(nodeDistances.keys());
  
  // Filter nodes - keep original references to preserve x/y positions
  const filteredNodes = allNodes.filter((n) => includedNodeIds.has(n.id));
  
  // Only include edges where BOTH endpoints are in our set
  const filteredEdges = allEdges.filter((e) => {
    const { sourceId, targetId } = getEdgeEndpoints(e);
    return includedNodeIds.has(sourceId) && includedNodeIds.has(targetId);
  });
  
  console.log(`Focus filter: ${maxHops} hops from ${targetNodeId} -> ${filteredNodes.length} nodes, ${filteredEdges.length} edges`);
  
  return { nodes: filteredNodes, edges: filteredEdges };
}

// Find shortest path between two nodes using BFS
interface PathResult {
  nodeIds: string[];
  edges: GraphEdge[];
  found: boolean;
}

function findShortestPath(
  startNodeId: string,
  endNodeId: string,
  allNodes: GraphNode[],
  allEdges: GraphEdge[]
): PathResult {
  if (startNodeId === endNodeId) {
    return { nodeIds: [startNodeId], edges: [], found: true };
  }
  
  // Build adjacency map with edge references
  const adjacency = new Map<string, Array<{ neighborId: string; edge: GraphEdge }>>();
  
  for (const edge of allEdges) {
    const { sourceId, targetId } = getEdgeEndpoints(edge);
    
    if (!adjacency.has(sourceId)) adjacency.set(sourceId, []);
    if (!adjacency.has(targetId)) adjacency.set(targetId, []);
    
    adjacency.get(sourceId)!.push({ neighborId: targetId, edge });
    adjacency.get(targetId)!.push({ neighborId: sourceId, edge });
  }
  
  // BFS to find shortest path
  const visited = new Set<string>([startNodeId]);
  const parent = new Map<string, { nodeId: string; edge: GraphEdge }>();
  const queue: string[] = [startNodeId];
  
  while (queue.length > 0) {
    const current = queue.shift()!;
    
    if (current === endNodeId) {
      // Reconstruct path
      const nodeIds: string[] = [];
      const edges: GraphEdge[] = [];
      let node = endNodeId;
      
      while (node !== startNodeId) {
        nodeIds.unshift(node);
        const parentInfo = parent.get(node)!;
        edges.unshift(parentInfo.edge);
        node = parentInfo.nodeId;
      }
      nodeIds.unshift(startNodeId);
      
      return { nodeIds, edges, found: true };
    }
    
    const neighbors = adjacency.get(current) || [];
    for (const { neighborId, edge } of neighbors) {
      if (!visited.has(neighborId)) {
        visited.add(neighborId);
        parent.set(neighborId, { nodeId: current, edge });
        queue.push(neighborId);
      }
    }
  }
  
  // No path found
  return { nodeIds: [], edges: [], found: false };
}

export default function NetworkPage() {
  const graphDimensions = useGraphDimensions();

  // Full graph data (from API)
  const [fullGraphData, setFullGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Focus state
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const [focusHops, setFocusHops] = useState(1); // Default to 1 hop for tighter focus
  const [graphRefreshKey, setGraphRefreshKey] = useState(0); // For forcing graph remount
  const [pendingFocusNodeId, setPendingFocusNodeId] = useState<string | null>(null); // For after reload
  
  // Control state
  const [indication, setIndication] = useState('MuM');
  const [trialFilter, setTrialFilter] = useState<TrialFilter>('none');
  const [showTrialSponsors, setShowTrialSponsors] = useState(false); // Hide trial-sponsor edges by default
  const [includeSites, setIncludeSites] = useState(false); // Default: industry only (sites off)
  const [pinOnDrag, setPinOnDrag] = useState(true); // Default to pinning nodes when dragged
  const [selectedPhases, setSelectedPhases] = useState<string[]>([]);
  const [selectedModalities, setSelectedModalities] = useState<string[]>([]);
  
  // Search/highlight state
  const [highlightedNodeId, setHighlightedNodeId] = useState<string | null>(null);
  
  // Drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const [entityData, setEntityData] = useState<Company | Asset | Trial | null>(null);
  const [entityLoading, setEntityLoading] = useState(false);
  
  // Navigation history for back button
  const [nodeHistory, setNodeHistory] = useState<string[]>([]);
  
  // Multi-select state
  const [selectedNodes, setSelectedNodes] = useState<GraphNode[]>([]);
  
  // Ingestion state
  const [ingesting, setIngesting] = useState(false);
  const [ingestMessage, setIngestMessage] = useState<string | null>(null);
  
  // Health check
  const [healthy, setHealthy] = useState<boolean | null>(null);

  // Compute displayed graph data (filtered by focus and industry type)
  const graphData = useMemo(() => {
    let data = fullGraphData;

    // When Include Sites is OFF, show only industry sponsors (filter out sites/academic).
    // company_type is lowercase from backend; treat missing/undefined as non-industry so they show when Include Sites is ON.
    if (!includeSites) {
      const industryNodeIds = new Set(
        data.nodes
          .filter((n) => {
            if (n.type !== 'company') return true;
            const ct = (n.data as any)?.company_type;
            return typeof ct === 'string' && ct.toLowerCase() === 'industry';
          })
          .map((n) => n.id)
      );

      data = {
        nodes: data.nodes.filter((n) => industryNodeIds.has(n.id)),
        edges: data.edges.filter((e) => {
          const sourceId = typeof e.source === 'string' ? e.source : (e.source as any)?.id;
          const targetId = typeof e.target === 'string' ? e.target : (e.target as any)?.id;
          return industryNodeIds.has(sourceId) && industryNodeIds.has(targetId);
        })
      };
    }
    
    // Filter out trial-sponsor edges if disabled
    if (!showTrialSponsors) {
      data = {
        nodes: data.nodes,
        edges: data.edges.filter((e) => e.type !== 'SPONSORS_TRIAL')
      };
    }
    
    // Apply focus filter (only if focused node is in the graph, else show full graph)
    if (focusedNodeId) {
      const focused = getNodesWithinHops(focusedNodeId, data.nodes, data.edges, focusHops);
      // If focus yields no nodes (e.g. focused node not in current filter), show full graph so we don't show "No Data Yet"
      if (focused.nodes.length > 0) return focused;
    }
    
    return data;
  }, [fullGraphData, focusedNodeId, focusHops, includeSites, showTrialSponsors]);

  // Get the focused node label for display
  const focusedNodeLabel = useMemo(() => {
    if (!focusedNodeId) return null;
    const node = fullGraphData.nodes.find((n) => n.id === focusedNodeId);
    return node?.label || focusedNodeId;
  }, [focusedNodeId, fullGraphData.nodes]);

  // Check API health on mount
  useEffect(() => {
    getHealth()
      .then((status) => {
        setHealthy(status.status === 'healthy');
        if (status.stats.trials === 0) {
          setError('No data loaded. Click "Ingest Data" to load clinical trials for MuM.');
          setLoading(false);
        }
      })
      .catch(() => {
        setHealthy(false);
        setError('Cannot connect to backend. Make sure the API is running.');
        setLoading(false);
      });
  }, []);

  // Load graph data
  const loadGraph = useCallback(async (preserveFocus = false) => {
    if (healthy === false) return;
    
    setLoading(true);
    setError(null);
    if (!preserveFocus) {
      setFocusedNodeId(null); // Reset focus when reloading (unless preserving)
    }
    
    try {
      const data = await getIndicationGraph(indication, {
        depth: 10, // Fetch all data, we filter client-side with hop distance
        trialFilter,
        phases: selectedPhases.length > 0 ? selectedPhases : undefined,
        modalities: selectedModalities.length > 0 ? selectedModalities : undefined,
      });
      
      setFullGraphData(data);
      
      if (data.nodes.length === 0) {
        setError('No data found. Try running ingestion first.');
      }
    } catch (err) {
      console.error('Failed to load graph:', err);
      setError('Failed to load graph data');
    } finally {
      setLoading(false);
    }
  }, [indication, trialFilter, selectedPhases, selectedModalities, healthy]);

  // Track if this is the initial load (using ref to avoid re-renders)
  const hasLoadedOnceRef = useRef(false);
  const prevIncludeSitesRef = useRef(includeSites);

  // Load graph on mount and when controls change
  useEffect(() => {
    if (healthy) {
      // Preserve focus on subsequent loads (when toggles change), not on initial load
      const shouldPreserveFocus = hasLoadedOnceRef.current;
      loadGraph(shouldPreserveFocus);
      hasLoadedOnceRef.current = true;
    }
  }, [loadGraph, healthy]);

  // When user turns "Include Sites" ON, refetch so we have fresh graph data (with company_type for all nodes)
  useEffect(() => {
    if (includeSites && !prevIncludeSitesRef.current && hasLoadedOnceRef.current) {
      loadGraph(true);
    }
    prevIncludeSitesRef.current = includeSites;
  }, [includeSites, loadGraph]);

  // Handler for changing hop count - force graph refresh when decreasing
  const handleHopChange = useCallback((newHops: number) => {
    const oldHops = focusHops;
    setFocusHops(newHops);
    
    // If decreasing hops, force a graph remount to properly remove nodes
    if (newHops < oldHops) {
      console.log(`Hop decrease: ${oldHops} -> ${newHops}, forcing refresh`);
      setGraphRefreshKey(k => k + 1);
    }
  }, [focusHops]);

  // Apply pending focus after data loads
  useEffect(() => {
    if (pendingFocusNodeId && fullGraphData.nodes.length > 0 && !loading) {
      const node = fullGraphData.nodes.find((n) => n.id === pendingFocusNodeId);
      if (node) {
        setFocusedNodeId(node.id);
        setHighlightedNodeId(node.id);
        setSelectedNode(node);
        setDrawerOpen(true);
      }
      setPendingFocusNodeId(null);
    }
  }, [pendingFocusNodeId, fullGraphData.nodes, loading]);

  // Handle node click - focus on this node (with multi-select support)
  const handleNodeClick = async (node: GraphNode, event?: MouseEvent) => {
    const isMultiSelect = event?.metaKey || event?.ctrlKey;
    
    if (isMultiSelect) {
      // Multi-select mode: toggle node in selection
      setSelectedNodes(prev => {
        const isAlreadySelected = prev.some(n => n.id === node.id);
        if (isAlreadySelected) {
          return prev.filter(n => n.id !== node.id);
        } else {
          return [...prev, node];
        }
      });
      // Don't change focus or load entity in multi-select mode
      return;
    }
    
    // Single select mode: clear multi-selection
    setSelectedNodes([]);
    
    // Add current focused node to history before navigating away
    if (focusedNodeId && focusedNodeId !== node.id) {
      setNodeHistory(prev => {
        // Don't add duplicates consecutively
        if (prev[prev.length - 1] === focusedNodeId) return prev;
        // Keep history manageable (max 20 items)
        const newHistory = [...prev, focusedNodeId].slice(-20);
        return newHistory;
      });
    }
    
    // Set focus to this node
    setFocusedNodeId(node.id);
    setHighlightedNodeId(node.id);
    
    // Open drawer with details
    setSelectedNode(node);
    setSelectedEdge(null);
    setDrawerOpen(true);
    setEntityLoading(true);
    setEntityData(null);
    
    try {
      let data: Company | Asset | Trial | null = null;
      
      if (node.type === 'company') {
        data = await getCompany(node.id);
      } else if (node.type === 'asset') {
        data = await getAsset(node.id);
      } else if (node.type === 'trial') {
        try {
          data = await getTrial(node.id);
        } catch {
          // Fallback: use trial data from graph if API fails (e.g. trial not in DB)
          data = (node.data as Trial) || null;
        }
      }
      
      setEntityData(data);
    } catch (err) {
      console.error('Failed to load entity:', err);
      // For trials, fall back to graph node data so drawer still shows something
      if (node.type === 'trial' && node.data) {
        setEntityData(node.data as Trial);
      }
    } finally {
      setEntityLoading(false);
    }
  };

  // Navigate back to previous node
  const handleGoBack = useCallback(() => {
    if (nodeHistory.length === 0) return;
    
    const previousNodeId = nodeHistory[nodeHistory.length - 1];
    const previousNode = fullGraphData.nodes.find(n => n.id === previousNodeId);
    
    if (previousNode) {
      // Remove from history
      setNodeHistory(prev => prev.slice(0, -1));
      
      // Navigate to the node (without adding to history again)
      setFocusedNodeId(previousNode.id);
      setHighlightedNodeId(previousNode.id);
      setSelectedNode(previousNode);
      setSelectedNodes([]);
      setSelectedEdge(null);
      setDrawerOpen(true);
      
      // Load entity data
      setEntityLoading(true);
      setEntityData(null);
      
      (async () => {
        try {
          let data: Company | Asset | Trial | null = null;
          if (previousNode.type === 'company') {
            data = await getCompany(previousNode.id);
          } else if (previousNode.type === 'asset') {
            data = await getAsset(previousNode.id);
          } else if (previousNode.type === 'trial') {
            data = await getTrial(previousNode.id);
          }
          setEntityData(data);
        } catch (err) {
          console.error('Failed to load entity:', err);
        } finally {
          setEntityLoading(false);
        }
      })();
    }
  }, [nodeHistory, fullGraphData.nodes]);

  // Find edges connecting selected nodes (for multi-select)
  const connectionsBetweenSelected = useMemo(() => {
    if (selectedNodes.length < 2) return [];
    
    const selectedIds = new Set(selectedNodes.map(n => n.id));
    
    return graphData.edges.filter((edge) => {
      const sourceId = typeof edge.source === 'string' ? edge.source : (edge.source as any)?.id;
      const targetId = typeof edge.target === 'string' ? edge.target : (edge.target as any)?.id;
      return selectedIds.has(sourceId) && selectedIds.has(targetId);
    });
  }, [selectedNodes, graphData.edges]);

  // Find shortest path between two selected nodes (uses full graph data for path finding)
  const shortestPath = useMemo(() => {
    if (selectedNodes.length !== 2) return null;
    
    const [nodeA, nodeB] = selectedNodes;
    const result = findShortestPath(nodeA.id, nodeB.id, fullGraphData.nodes, fullGraphData.edges);
    
    if (!result.found) return null;
    
    // Map node IDs to actual nodes
    const pathNodes = result.nodeIds
      .map(id => fullGraphData.nodes.find(n => n.id === id))
      .filter((n): n is GraphNode => n !== undefined);
    
    return {
      nodes: pathNodes,
      edges: result.edges,
      length: result.nodeIds.length - 1 // Number of hops
    };
  }, [selectedNodes, fullGraphData.nodes, fullGraphData.edges]);

  // Handle edge click
  const handleEdgeClick = (edge: GraphEdge) => {
    setSelectedEdge(edge);
    setSelectedNode(null);
    setEntityData(null);
    setDrawerOpen(true);
  };

  // Clear focus and show all nodes
  const handleShowAll = () => {
    setFocusedNodeId(null);
    setHighlightedNodeId(null);
  };

  // Handle ingestion
  const handleIngest = async () => {
    setIngesting(true);
    setIngestMessage(null);
    setError(null);
    
    try {
      const result = await ingestClinicalTrials(indication, 100);
      setIngestMessage(
        `Ingested ${result.stats.trials} trials, ${result.stats.companies} companies, ${result.stats.assets} assets`
      );
      setTimeout(() => {
        loadGraph();
        setIngestMessage(null);
      }, 2000);
    } catch (err) {
      console.error('Ingestion failed:', err);
      setError('Ingestion failed. Check backend logs.');
    } finally {
      setIngesting(false);
    }
  };

  // Handle search selection
  const handleSearchSelect = (node: GraphNode) => {
    handleNodeClick(node);
  };

  // Extract available phases and modalities from full data
  const availablePhases = [...new Set(
    fullGraphData.nodes
      .filter((n) => n.type === 'trial')
      .map((n) => (n.data as any).phase)
      .filter(Boolean)
  )];
  
  const availableModalities = [...new Set(
    fullGraphData.nodes
      .filter((n) => n.type === 'asset')
      .map((n) => (n.data as any).modality)
      .filter(Boolean)
  )];

  return (
    <div className="flex h-[calc(100vh-8rem)]">
      {/* Left sidebar - Controls */}
      <div className="w-80 flex-shrink-0 p-4 border-r border-gray-200 bg-white overflow-y-auto">
        <div className="space-y-5">
          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search Graph
            </label>
            <GraphSearch
              nodes={fullGraphData.nodes}
              onSelectNode={handleSearchSelect}
              onHighlightNode={setHighlightedNodeId}
            />
          </div>

          {/* Unified Hop Distance Control */}
          <div className={cn(
            "rounded-lg p-3 border",
            focusedNodeId 
              ? "bg-blue-50 border-blue-200" 
              : "bg-gray-50 border-gray-200"
          )}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <Focus className={cn("w-4 h-4", focusedNodeId ? "text-blue-600" : "text-gray-500")} />
                <span className={cn("text-sm font-medium", focusedNodeId ? "text-blue-800" : "text-gray-700")}>
                  {focusedNodeId ? 'Focused View' : 'Hop Distance'}
                </span>
              </div>
              {focusedNodeId && (
                <button
                  onClick={handleShowAll}
                  className="p-1 hover:bg-blue-100 rounded transition-colors"
                  title="Show all nodes"
                >
                  <X className="w-4 h-4 text-blue-600" />
                </button>
              )}
            </div>
            
            {focusedNodeId && (
              <p className="text-xs text-blue-700 truncate mb-2" title={focusedNodeLabel || ''}>
                From: <strong>{focusedNodeLabel}</strong>
              </p>
            )}
            
            <div className="flex items-center space-x-1">
              <span className={cn("text-xs mr-1", focusedNodeId ? "text-blue-600" : "text-gray-600")}>
                Show:
              </span>
              {[1, 2, 3].map((h) => (
                <button
                  key={h}
                  onClick={() => handleHopChange(h)}
                  className={cn(
                    'px-2.5 py-1 text-xs rounded transition-colors',
                    focusHops === h
                      ? focusedNodeId ? 'bg-blue-600 text-white' : 'bg-gray-700 text-white'
                      : focusedNodeId ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  )}
                >
                  {h} hop{h > 1 ? 's' : ''}
                </button>
              ))}
              <button
                onClick={() => handleHopChange(99)}
                className={cn(
                  'px-2.5 py-1 text-xs rounded transition-colors',
                  focusHops >= 99
                    ? focusedNodeId ? 'bg-blue-600 text-white' : 'bg-gray-700 text-white'
                    : focusedNodeId ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                )}
              >
                All
              </button>
            </div>
            
            <p className={cn("text-xs mt-2", focusedNodeId ? "text-blue-600" : "text-gray-500")}>
              Showing {graphData.nodes.length} of {fullGraphData.nodes.length} nodes
            </p>
            
            {focusedNodeId && (
              <button
                onClick={handleShowAll}
                className="mt-2 w-full text-xs bg-white border border-blue-200 rounded py-1 text-blue-700 hover:bg-blue-100 transition-colors"
              >
                ← Clear focus (show all)
              </button>
            )}
            
            {/* Back button */}
            {nodeHistory.length > 0 && (
              <button
                onClick={handleGoBack}
                className="mt-2 w-full text-xs bg-gray-100 border border-gray-200 rounded py-1 text-gray-700 hover:bg-gray-200 transition-colors flex items-center justify-center gap-1"
              >
                <ArrowLeft className="w-3 h-3" />
                Back to previous node
              </button>
            )}
          </div>
          
          {/* Multi-select panel */}
          {selectedNodes.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <Link2 className="w-4 h-4 text-amber-600" />
                  <span className="text-sm font-medium text-amber-800">
                    {selectedNodes.length} node{selectedNodes.length > 1 ? 's' : ''} selected
                  </span>
                </div>
                <button
                  onClick={() => setSelectedNodes([])}
                  className="text-amber-600 hover:text-amber-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              
              <p className="text-xs text-amber-700 mb-2">
                Ctrl/Cmd+click to add more nodes
              </p>
              
              {/* List selected nodes */}
              <div className="space-y-1 mb-3">
                {selectedNodes.map((node) => (
                  <div key={node.id} className="text-xs bg-white border border-amber-200 rounded px-2 py-1 flex items-center justify-between">
                    <span className="truncate">{node.label}</span>
                    <span className="text-amber-500 ml-2 capitalize">{node.type}</span>
                  </div>
                ))}
              </div>
              
              {/* Show shortest path between exactly 2 nodes */}
              {selectedNodes.length === 2 && (
                <div className="border-t border-amber-200 pt-2">
                  {shortestPath ? (
                    <>
                      <p className="text-xs font-medium text-amber-800 mb-2">
                        Shortest path ({shortestPath.length} hop{shortestPath.length !== 1 ? 's' : ''}):
                      </p>
                      <div className="bg-white border border-amber-200 rounded p-2 space-y-1">
                        {shortestPath.nodes.map((node, idx) => (
                          <div key={node.id}>
                            {/* Node */}
                            <div 
                              className="flex items-center gap-2 cursor-pointer hover:bg-amber-50 rounded px-1 py-0.5"
                              onClick={() => {
                                setSelectedNodes([]);
                                handleNodeClick(node);
                              }}
                            >
                              <span className={cn(
                                "w-2 h-2 rounded-full flex-shrink-0",
                                node.type === 'company' ? 'bg-blue-500' :
                                node.type === 'asset' ? 'bg-green-500' :
                                node.type === 'trial' ? 'bg-amber-500' : 'bg-gray-500'
                              )} />
                              <span className="text-xs font-medium truncate">{node.label}</span>
                              <span className="text-xs text-amber-500 capitalize">{node.type}</span>
                            </div>
                            
                            {/* Edge (if not last node) */}
                            {idx < shortestPath.edges.length && (
                              <div className="flex items-center ml-3 my-1 text-xs text-amber-600">
                                <span className="w-px h-3 bg-amber-300 mr-2" />
                                <span className="italic">{shortestPath.edges[idx].type}</span>
                                <span className="w-px h-3 bg-amber-300 ml-2" />
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <p className="text-xs text-amber-600 italic">
                      No path found between selected nodes
                    </p>
                  )}
                </div>
              )}
              
              {/* Show direct connections for 3+ nodes */}
              {selectedNodes.length > 2 && (
                <div className="border-t border-amber-200 pt-2">
                  <p className="text-xs font-medium text-amber-800 mb-1">
                    Direct connections: {connectionsBetweenSelected.length}
                  </p>
                  {connectionsBetweenSelected.length > 0 ? (
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {connectionsBetweenSelected.map((edge, idx) => {
                        const sourceNode = selectedNodes.find(n => n.id === (typeof edge.source === 'string' ? edge.source : (edge.source as any)?.id));
                        const targetNode = selectedNodes.find(n => n.id === (typeof edge.target === 'string' ? edge.target : (edge.target as any)?.id));
                        return (
                          <div key={idx} className="text-xs bg-white border border-amber-200 rounded px-2 py-1">
                            <span className="truncate">{sourceNode?.label}</span>
                            <span className="mx-1 text-amber-500">→</span>
                            <span className="text-amber-600">{edge.type}</span>
                            <span className="mx-1 text-amber-500">→</span>
                            <span className="truncate">{targetNode?.label}</span>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-xs text-amber-600 italic">
                      No direct edges between selected nodes
                    </p>
                  )}
                  <p className="text-xs text-amber-500 mt-2 italic">
                    Tip: Select exactly 2 nodes to see shortest path
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Indication selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Indication
            </label>
            <div className="relative">
              <input
                type="text"
                value={indication}
                onChange={(e) => setIndication(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                placeholder="e.g., MuM"
              />
              <Search className="absolute right-3 top-2.5 w-4 h-4 text-gray-400" />
            </div>
          </div>

          {/* Graph controls */}
          <GraphControls
            trialFilter={trialFilter}
            onTrialFilterChange={setTrialFilter}
            showTrialSponsors={showTrialSponsors}
            onShowTrialSponsorsChange={setShowTrialSponsors}
            includeSites={includeSites}
            onIncludeSitesChange={setIncludeSites}
            pinOnDrag={pinOnDrag}
            onPinOnDragChange={setPinOnDrag}
            phases={availablePhases}
            selectedPhases={selectedPhases}
            onPhasesChange={setSelectedPhases}
            modalities={availableModalities}
            selectedModalities={selectedModalities}
            onModalitiesChange={setSelectedModalities}
          />

          {/* Actions */}
          <div className="space-y-2">
            <button
              onClick={loadGraph}
              disabled={loading}
              className={cn(
                'w-full flex items-center justify-center px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                loading
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-500 text-white hover:bg-blue-600'
              )}
            >
              <RefreshCw className={cn('w-4 h-4 mr-2', loading && 'animate-spin')} />
              {loading ? 'Loading...' : 'Refresh Graph'}
            </button>

            <button
              onClick={handleIngest}
              disabled={ingesting}
              className={cn(
                'w-full flex items-center justify-center px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                ingesting
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-green-500 text-white hover:bg-green-600'
              )}
            >
              <Database className={cn('w-4 h-4 mr-2', ingesting && 'animate-spin')} />
              {ingesting ? 'Ingesting...' : 'Ingest Data'}
            </button>
          </div>

          {/* Messages */}
          {ingestMessage && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
              {ingestMessage}
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-start">
              <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {/* Stats */}
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase font-medium mb-2">Current View</p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-500">Nodes:</span>
                <span className="ml-1 font-medium">{graphData.nodes.length}</span>
                {focusedNodeId && (
                  <span className="text-gray-400 text-xs"> / {fullGraphData.nodes.length}</span>
                )}
              </div>
              <div>
                <span className="text-gray-500">Edges:</span>
                <span className="ml-1 font-medium">{graphData.edges.length}</span>
                {focusedNodeId && (
                  <span className="text-gray-400 text-xs"> / {fullGraphData.edges.length}</span>
                )}
              </div>
            </div>
          </div>

          {/* Connection status */}
          <div className="flex items-center space-x-2 text-xs">
            <div
              className={cn(
                'w-2 h-2 rounded-full',
                healthy === true ? 'bg-green-500' : healthy === false ? 'bg-red-500' : 'bg-yellow-500'
              )}
            />
            <span className="text-gray-500">
              {healthy === true ? 'Connected' : healthy === false ? 'Disconnected' : 'Checking...'}
            </span>
          </div>
        </div>
      </div>

      {/* Main content - Graph */}
      <div className="flex-1 p-4 relative">
        <div className="h-full">
          {loading && graphData.nodes.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto" />
                <p className="mt-4 text-gray-500">Loading network...</p>
              </div>
            </div>
          ) : graphData.nodes.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-md">
                <Database className="w-12 h-12 text-gray-300 mx-auto" />
                <h3 className="mt-4 text-lg font-medium text-gray-700">No Data Yet</h3>
                <p className="mt-2 text-sm text-gray-500">
                  Click "Ingest Data" to load clinical trials data for {indication} from
                  ClinicalTrials.gov
                </p>
              </div>
            </div>
          ) : (
            <NetworkGraph
              key={`${graphRefreshKey}-${includeSites ? 'sites' : 'industry'}`}
              data={graphData}
              onNodeClick={handleNodeClick}
              onEdgeClick={handleEdgeClick}
              highlightNodeId={highlightedNodeId}
              selectedNodeIds={selectedNodes.map(n => n.id)}
              pinOnDrag={pinOnDrag}
              refreshKey={graphRefreshKey}
              width={graphDimensions.width}
              height={graphDimensions.height}
            />
          )}
        </div>

        {/* Page title overlay */}
        <div className="absolute top-6 left-6 bg-white/90 backdrop-blur-sm rounded-lg px-4 py-2 shadow-sm border border-gray-200">
          <h1 className="text-lg font-semibold text-gray-800">
            {indication} Network
          </h1>
          <p className="text-xs text-gray-500">
            {focusedNodeId ? `Focused on ${focusedNodeLabel}` : 'Companies, Assets, and Trials'}
          </p>
        </div>

        {/* Keyboard hints */}
        <div className="absolute bottom-6 left-6 bg-white/80 backdrop-blur-sm rounded-lg px-3 py-2 shadow-sm border border-gray-200">
          <p className="text-xs text-gray-500">
            Scroll to zoom • Drag to pan • Click nodes to focus
          </p>
        </div>

        {/* Show All button overlay when focused */}
        {focusedNodeId && (
          <button
            onClick={handleShowAll}
            className="absolute top-6 right-6 bg-white hover:bg-gray-50 rounded-lg px-4 py-2 shadow-sm border border-gray-200 text-sm font-medium text-gray-700 transition-colors"
          >
            ← Show All ({fullGraphData.nodes.length} nodes)
          </button>
        )}
      </div>

      {/* Detail drawer */}
      <DetailDrawer
        isOpen={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
        }}
        node={selectedNode}
        edge={selectedEdge}
        entityData={entityData}
        loading={entityLoading}
        onRefreshEntity={async () => {
          if (!selectedNode) return;
          setEntityLoading(true);
          try {
            let data: Company | Asset | Trial | null = null;
            if (selectedNode.type === 'company') data = await getCompany(selectedNode.id);
            else if (selectedNode.type === 'asset') data = await getAsset(selectedNode.id);
            else if (selectedNode.type === 'trial') data = await getTrial(selectedNode.id);
            setEntityData(data);
          } catch (err) {
            console.error('Refresh entity failed:', err);
          } finally {
            setEntityLoading(false);
          }
        }}
        onNavigateToNode={async (nodeId, nodeType) => {
          // Find the node in the full graph data
          let node = fullGraphData.nodes.find((n) => n.id === nodeId);

          if (node) {
            // Node exists in current data, navigate directly
            handleNodeClick(node);
          } else if (nodeType === 'trial' && trialFilter === 'none') {
            // Trial not loaded because "Include Trials" is off
            // Enable trials and set pending focus
            setPendingFocusNodeId(nodeId);
            setIncludeTrials(true);
          } else {
            // Node not in graph (filtered out or not returned) - still open drawer and show entity
            const syntheticNode: GraphNode = {
              id: nodeId,
              type: nodeType as GraphNode['type'],
              label: nodeId,
            };
            setSelectedNodes([]);
            setFocusedNodeId(nodeId);
            setHighlightedNodeId(nodeId);
            setSelectedNode(syntheticNode);
            setSelectedEdge(null);
            setDrawerOpen(true);
            setEntityLoading(true);
            setEntityData(null);
            try {
              let data: Company | Asset | Trial | null = null;
              if (nodeType === 'company') data = await getCompany(nodeId);
              else if (nodeType === 'asset') data = await getAsset(nodeId);
              else if (nodeType === 'trial') {
                try {
                  data = await getTrial(nodeId);
                } catch {
                  data = null;
                }
              }
              setEntityData(data);
              if (data && 'title' in data && data.title) {
                setSelectedNode((prev) => (prev ? { ...prev, label: (data as Trial).title?.slice(0, 50) ?? prev.label } : prev));
              } else if (data && 'name' in data && data.name) {
                setSelectedNode((prev) => (prev ? { ...prev, label: (data as Company | Asset).name ?? prev.label } : prev));
              }
            } catch (err) {
              console.error('Failed to load entity for navigate:', err);
            } finally {
              setEntityLoading(false);
            }
          }
        }}
      />
    </div>
  );
}
