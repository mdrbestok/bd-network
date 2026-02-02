'use client';

import { useCallback, useRef, useEffect, useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import * as d3Force from 'd3-force';
import type { GraphNode, GraphEdge, GraphData, NodeType } from '@/types';
import { nodeColors, edgeStyles } from '@/lib/utils';

// Dynamic import to avoid SSR issues with canvas
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
    </div>
  ),
});

interface NetworkGraphProps {
  data: GraphData;
  onNodeClick?: (node: GraphNode, event?: MouseEvent) => void;
  onEdgeClick?: (edge: GraphEdge) => void;
  highlightNodeId?: string | null;
  selectedNodeIds?: string[]; // For multi-select highlighting
  pinOnDrag?: boolean;
  refreshKey?: number; // Change this to force graph remount
  width?: number;
  height?: number;
}

export default function NetworkGraph({
  data,
  onNodeClick,
  onEdgeClick,
  highlightNodeId,
  selectedNodeIds = [],
  pinOnDrag = false,
  refreshKey = 0,
  width = 800,
  height = 600,
}: NetworkGraphProps) {
  const graphRef = useRef<any>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [isStabilized, setIsStabilized] = useState(false);

  // Transform data for react-force-graph
  const graphData = useMemo(() => ({
    nodes: data.nodes.map(node => {
      // Don't copy fx/fy from source - let them be set fresh by pinOnDrag
      const { fx, fy, ...rest } = node as any;
      return { ...rest };
    }),
    links: data.edges.map((edge) => ({
      ...edge,
      source: typeof edge.source === 'string' ? edge.source : edge.source.id,
      target: typeof edge.target === 'string' ? edge.target : edge.target.id,
    })),
  }), [data]);

  // Reset stabilization state when refreshKey changes
  useEffect(() => {
    setIsStabilized(false);
  }, [refreshKey]);

  // Configure force simulation for better layout
  useEffect(() => {
    if (graphRef.current) {
      const fg = graphRef.current;
      
      // Much larger link distance for more spread
      fg.d3Force('link')?.distance(() => 200);
      
      // Strong charge repulsion to prevent clustering
      fg.d3Force('charge')?.strength(-1500).distanceMax(800);
      
      // Add collision detection to prevent node overlap
      fg.d3Force('collide', d3Force.forceCollide((node: any) => {
        // Collision radius based on node type - larger = more spacing
        const baseSize = node.type === 'company' ? 35 : node.type === 'asset' ? 30 : 20;
        return baseSize;
      }).strength(1).iterations(3));
      
      // Weaker center force so nodes can spread out more
      fg.d3Force('center')?.strength(0.01);
      
      // Add x and y forces to spread horizontally/vertically
      fg.d3Force('x', d3Force.forceX(0).strength(0.015));
      fg.d3Force('y', d3Force.forceY(0).strength(0.015));
    }
  }, [graphData]);

  // Zoom to fit after stabilization
  useEffect(() => {
    if (graphRef.current && data.nodes.length > 0 && isStabilized) {
      setTimeout(() => {
        graphRef.current.zoomToFit(400, 80);
      }, 100);
    }
  }, [data, isStabilized]);

  // Handle engine stop (stabilization complete)
  const handleEngineStop = useCallback(() => {
    setIsStabilized(true);
  }, []);

  // Highlight a specific node (from search)
  useEffect(() => {
    if (highlightNodeId && graphRef.current) {
      const node = data.nodes.find(n => n.id === highlightNodeId);
      if (node && (node as any).x !== undefined) {
        graphRef.current.centerAt((node as any).x, (node as any).y, 500);
        graphRef.current.zoom(2, 500);
      }
    }
  }, [highlightNodeId, data.nodes]);

  // Check if node should be highlighted
  const isHighlighted = useCallback((nodeId: string) => {
    return nodeId === highlightNodeId || nodeId === hoveredNode;
  }, [highlightNodeId, hoveredNode]);

  // Check if node is multi-selected
  const isMultiSelected = useCallback((nodeId: string) => {
    return selectedNodeIds.includes(nodeId);
  }, [selectedNodeIds]);

  // Node rendering
  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.label || node.id;
      const fontSize = 11 / globalScale;
      const nodeType = node.type as NodeType;
      const highlighted = isHighlighted(node.id);
      const multiSelected = isMultiSelected(node.id);
      
      // Get company type for differentiated coloring
      const companyType = node.data?.company_type;
      const isIndustry = companyType === 'industry';
      
      // Use different colors for industry vs non-industry companies
      let color = nodeColors[nodeType] || '#666';
      let alpha = 1.0;
      
      if (nodeType === 'company' && !isIndustry && companyType) {
        // Non-industry companies: lighter, more transparent
        color = '#94a3b8'; // slate-400 - gray-blue
        alpha = 0.7;
      }

      // Node size based on type (industry sponsors slightly larger)
      let baseSize = nodeType === 'company' ? 10 : nodeType === 'asset' ? 8 : 5;
      if (nodeType === 'company' && !isIndustry && companyType) {
        baseSize = 7; // Smaller for non-industry
      }
      const size = highlighted ? baseSize * 1.4 : baseSize;

      // Draw multi-select ring (orange/yellow border)
      if (multiSelected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, size + 5, 0, 2 * Math.PI);
        ctx.strokeStyle = '#f59e0b'; // amber-500
        ctx.lineWidth = 3 / globalScale;
        ctx.stroke();
      }

      // Draw glow for highlighted nodes
      if (highlighted) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI);
        ctx.fillStyle = `${color}40`;
        ctx.fill();
      }

      // Draw node
      ctx.beginPath();
      if (nodeType === 'company') {
        // Circle for companies
        ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
      } else if (nodeType === 'asset') {
        // Diamond for assets
        ctx.moveTo(node.x, node.y - size);
        ctx.lineTo(node.x + size, node.y);
        ctx.lineTo(node.x, node.y + size);
        ctx.lineTo(node.x - size, node.y);
        ctx.closePath();
      } else if (nodeType === 'trial') {
        // Square for trials
        ctx.rect(node.x - size, node.y - size, size * 2, size * 2);
      } else {
        // Pentagon for deals
        const sides = 5;
        for (let i = 0; i < sides; i++) {
          const angle = (i * 2 * Math.PI) / sides - Math.PI / 2;
          const x = node.x + size * Math.cos(angle);
          const y = node.y + size * Math.sin(angle);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.closePath();
      }

      // Fill and stroke
      ctx.globalAlpha = alpha;
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = highlighted ? '#fff' : 'rgba(255,255,255,0.6)';
      ctx.lineWidth = highlighted ? 3 / globalScale : 1.5 / globalScale;
      ctx.stroke();
      ctx.globalAlpha = 1.0; // Reset alpha

      // Label - show when zoomed in enough or highlighted
      if (globalScale > 0.6 || highlighted) {
        ctx.font = `${highlighted ? 'bold ' : ''}${fontSize}px Inter, system-ui, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        
        // Truncate label
        const maxLen = highlighted ? 50 : 25;
        const displayLabel = label.length > maxLen ? label.slice(0, maxLen) + '...' : label;
        
        // Background for readability
        const textWidth = ctx.measureText(displayLabel).width;
        const padding = 3;
        ctx.fillStyle = highlighted ? 'rgba(255,255,255,0.95)' : 'rgba(255,255,255,0.85)';
        ctx.fillRect(
          node.x - textWidth / 2 - padding,
          node.y + size + 3,
          textWidth + padding * 2,
          fontSize + 4
        );
        
        ctx.fillStyle = highlighted ? '#000' : '#374151';
        ctx.fillText(displayLabel, node.x, node.y + size + 5);
      }
    },
    [isHighlighted, isMultiSelected]
  );

  // Link rendering
  const linkCanvasObject = useCallback(
    (link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const style = edgeStyles[link.type] || { color: '#999', dashed: false };
      
      const start = link.source;
      const end = link.target;
      
      if (!start.x || !end.x) return;

      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      
      ctx.strokeStyle = style.color;
      ctx.lineWidth = 1.5 / globalScale;
      
      if (style.dashed) {
        ctx.setLineDash([6 / globalScale, 4 / globalScale]);
      } else {
        ctx.setLineDash([]);
      }
      
      ctx.stroke();
      ctx.setLineDash([]);
    },
    []
  );

  return (
    <div className="graph-container border border-gray-200 rounded-xl overflow-hidden bg-gradient-to-br from-slate-50 to-gray-100">
      <ForceGraph2D
        key={refreshKey}
        ref={graphRef}
        graphData={graphData}
        width={width}
        height={height}
        nodeCanvasObject={nodeCanvasObject}
        linkCanvasObject={linkCanvasObject}
        nodePointerAreaPaint={(node, color, ctx) => {
          const size = node.type === 'company' ? 12 : node.type === 'asset' ? 10 : 6;
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI);
          ctx.fill();
        }}
        onNodeClick={(node, event) => onNodeClick?.(node as GraphNode, event)}
        onLinkClick={(link) => {
          const edge = data.edges.find(
            (e) =>
              (e.source === link.source?.id || e.source === link.source) &&
              (e.target === link.target?.id || e.target === link.target)
          );
          if (edge) onEdgeClick?.(edge);
        }}
        onNodeHover={(node) => setHoveredNode(node?.id || null)}
        onEngineStop={handleEngineStop}
        // Physics settings - more time to spread out
        cooldownTicks={300}
        cooldownTime={5000}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        warmupTicks={200}
        // Interactions
        linkDirectionalArrowLength={0}
        enableNodeDrag={true}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        minZoom={0.2}
        maxZoom={5}
        // Pin nodes on drag if enabled
        onNodeDragEnd={(node: any) => {
          if (pinOnDrag) {
            // Fix the node position so it won't move
            node.fx = node.x;
            node.fy = node.y;
          }
        }}
      />
    </div>
  );
}
