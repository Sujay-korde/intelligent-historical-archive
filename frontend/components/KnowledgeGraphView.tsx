'use client';

import React, { useEffect, useRef, useState } from 'react';
import Link from 'next/navigation';
import { ZoomIn, ZoomOut, RotateCcw, Filter, User, MapPin, Calendar, BookOpen, Layers, ArrowRight, X, ExternalLink } from 'lucide-react';
import { GraphEdge, GraphNode, GraphResponse } from '../lib/api';

interface KnowledgeGraphViewProps {
  initialData: GraphResponse;
  initialFocus?: string;
}

interface SimNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
}

export default function KnowledgeGraphView({ initialData, initialFocus = '' }: KnowledgeGraphViewProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [nodes, setNodes] = useState<SimNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<SimNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null);
  const [zoom, setZoom] = useState<number>(1.0);
  const [offset, setOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Filter types
  const [filterTypes, setFilterTypes] = useState<Record<string, boolean>>({
    PERSON: true,
    LOCATION: true,
    EVENT: true,
    ORGANIZATION: true,
    document: true,
  });

  // Layout simulation
  useEffect(() => {
    if (!initialData || !initialData.nodes) return;

    const width = 800;
    const height = 600;

    const simNodes: SimNode[] = initialData.nodes.map((n, i) => {
      const angle = (i / initialData.nodes.length) * 2 * Math.PI;
      const dist = 140 + (i % 3) * 60;
      return {
        ...n,
        x: width / 2 + Math.cos(angle) * dist + (Math.random() - 0.5) * 40,
        y: height / 2 + Math.sin(angle) * dist + (Math.random() - 0.5) * 40,
        vx: 0,
        vy: 0,
        radius: n.group === 'document' ? 24 : 18,
      };
    });

    setNodes(simNodes);
    setEdges(initialData.edges || []);

    // If initialFocus given, select that node
    if (initialFocus) {
      const match = simNodes.find((n) => n.label.toLowerCase() === initialFocus.toLowerCase());
      if (match) setSelectedNode(match);
    }
  }, [initialData, initialFocus]);

  // Canvas render loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      ctx.save();
      ctx.translate(canvas.width / 2 + offset.x, canvas.height / 2 + offset.y);
      ctx.scale(zoom, zoom);
      ctx.translate(-canvas.width / 2, -canvas.height / 2);

      const visibleNodes = nodes.filter((n) => filterTypes[n.group] !== false);
      const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));

      // Draw Edges
      edges.forEach((edge) => {
        if (!visibleNodeIds.has(edge.source) || !visibleNodeIds.has(edge.target)) return;
        const src = nodes.find((n) => n.id === edge.source);
        const tgt = nodes.find((n) => n.id === edge.target);
        if (!src || !tgt) return;

        const isHighlighted =
          (selectedNode && (selectedNode.id === src.id || selectedNode.id === tgt.id)) ||
          (hoveredNode && (hoveredNode.id === src.id || hoveredNode.id === tgt.id));

        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);
        ctx.strokeStyle = isHighlighted ? '#7A1C1C' : '#E2DACF';
        ctx.lineWidth = isHighlighted ? 2.5 : 1;
        ctx.stroke();

        // Edge label if highlighted
        if (isHighlighted && edge.relationship) {
          const midX = (src.x + tgt.x) / 2;
          const midY = (src.y + tgt.y) / 2;
          ctx.fillStyle = '#7A1C1C';
          ctx.font = '10px Inter, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(edge.relationship, midX, midY - 6);
        }
      });

      // Draw Nodes
      visibleNodes.forEach((node) => {
        const isSelected = selectedNode?.id === node.id;
        const isHovered = hoveredNode?.id === node.id;

        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);

        // Node fill color by group
        if (node.group === 'document') {
          ctx.fillStyle = isSelected ? '#7A1C1C' : '#1A1816';
        } else if (node.group === 'PERSON') {
          ctx.fillStyle = isSelected ? '#7A1C1C' : '#F4E8E8';
        } else if (node.group === 'LOCATION') {
          ctx.fillStyle = isSelected ? '#2F3E46' : '#EAEBED';
        } else if (node.group === 'EVENT') {
          ctx.fillStyle = isSelected ? '#997530' : '#F8F3E8';
        } else {
          ctx.fillStyle = isSelected ? '#2D5A3F' : '#EAF0EC';
        }
        ctx.fill();

        // Node border
        ctx.strokeStyle = isSelected ? '#7A1C1C' : isHovered ? '#1A1816' : '#C9BFB2';
        ctx.lineWidth = isSelected ? 3 : isHovered ? 2 : 1;
        ctx.stroke();

        // Node Label
        ctx.fillStyle = node.group === 'document' ? '#FFFFFF' : '#1A1816';
        ctx.font = node.group === 'document' ? 'bold 11px Inter, sans-serif' : '10px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const labelText = node.label.length > 14 ? node.label.substring(0, 12) + '…' : node.label;
        ctx.fillText(labelText, node.x, node.y);

        // Full label beneath if selected or hovered
        if (isSelected || isHovered) {
          ctx.fillStyle = '#1A1816';
          ctx.font = '12px Cormorant Garamond, serif';
          ctx.fillText(node.label, node.x, node.y + node.radius + 14);
        }
      });

      ctx.restore();
    };

    render();
  }, [nodes, edges, selectedNode, hoveredNode, zoom, offset, filterTypes]);

  // Mouse drag & select interactions
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (isDragging) {
      setOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
      return;
    }

    // Convert mouse coordinates into simulation space
    const simX = (mouseX - (canvas.width / 2 + offset.x)) / zoom + canvas.width / 2;
    const simY = (mouseY - (canvas.height / 2 + offset.y)) / zoom + canvas.height / 2;

    const found = nodes.find(
      (n) => Math.hypot(n.x - simX, n.y - simY) <= n.radius + 4
    );
    setHoveredNode(found || null);
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (hoveredNode) {
      setSelectedNode(hoveredNode);
    } else {
      setSelectedNode(null);
    }
  };

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.2, 2.5));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.2, 0.4));
  const handleReset = () => {
    setZoom(1.0);
    setOffset({ x: 0, y: 0 });
    setSelectedNode(null);
  };

  // Connected relationships for selected node
  const selectedEdges = selectedNode
    ? edges.filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
    : [];

  return (
    <div
      style={{
        display: 'flex',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--color-paper-border)',
        overflow: 'hidden',
        backgroundColor: '#FFFFFF',
        position: 'relative',
        height: '680px',
      }}
    >
      {/* Canvas Area */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        {/* Canvas Toolbar */}
        <div
          style={{
            position: 'absolute',
            top: '1rem',
            left: '1rem',
            zIndex: 10,
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            backgroundColor: 'rgba(251, 249, 245, 0.92)',
            backdropFilter: 'blur(6px)',
            padding: '0.4rem 0.6rem',
            borderRadius: 'var(--radius-xs)',
            border: '1px solid var(--color-paper-border)',
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <button
            type="button"
            onClick={handleZoomIn}
            title="Zoom in"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.2rem' }}
          >
            <ZoomIn size={16} color="var(--color-ink-secondary)" />
          </button>
          <button
            type="button"
            onClick={handleZoomOut}
            title="Zoom out"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.2rem' }}
          >
            <ZoomOut size={16} color="var(--color-ink-secondary)" />
          </button>
          <button
            type="button"
            onClick={handleReset}
            title="Reset canvas"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.2rem' }}
          >
            <RotateCcw size={16} color="var(--color-ink-secondary)" />
          </button>
          <span
            style={{
              fontSize: '0.75rem',
              color: 'var(--color-ink-muted)',
              borderLeft: '1px solid var(--color-paper-border)',
              paddingLeft: '0.5rem',
            }}
          >
            {nodes.length} Nodes • {edges.length} Edges
          </span>
        </div>

        {/* Legend / Category Toggles */}
        <div
          style={{
            position: 'absolute',
            bottom: '1rem',
            left: '1rem',
            zIndex: 10,
            display: 'flex',
            gap: '0.5rem',
            flexWrap: 'wrap',
            backgroundColor: 'rgba(251, 249, 245, 0.92)',
            backdropFilter: 'blur(6px)',
            padding: '0.4rem 0.8rem',
            borderRadius: 'var(--radius-xs)',
            border: '1px solid var(--color-paper-border)',
            fontSize: '0.75rem',
          }}
        >
          {[
            { key: 'PERSON', label: 'People', color: '#7A1C1C' },
            { key: 'LOCATION', label: 'Places', color: '#2F3E46' },
            { key: 'EVENT', label: 'Events', color: '#997530' },
            { key: 'document', label: 'Documents', color: '#1A1816' },
          ].map((cat) => (
            <label
              key={cat.key}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
                cursor: 'pointer',
                color: 'var(--color-ink-secondary)',
              }}
            >
              <input
                type="checkbox"
                checked={filterTypes[cat.key] !== false}
                onChange={(e) =>
                  setFilterTypes({ ...filterTypes, [cat.key]: e.target.checked })
                }
                style={{ accentColor: cat.color }}
              />
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: cat.color }} />
              {cat.label}
            </label>
          ))}
        </div>

        {/* HTML5 Canvas */}
        <canvas
          ref={canvasRef}
          width={860}
          height={680}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onClick={handleClick}
          style={{
            width: '100%',
            height: '100%',
            cursor: isDragging ? 'grabbing' : hoveredNode ? 'pointer' : 'grab',
            backgroundColor: 'var(--color-paper-base)',
          }}
        />
      </div>

      {/* Contextual Side Inspection Drawer */}
      {selectedNode && (
        <aside
          style={{
            width: '340px',
            borderLeft: '1px solid var(--color-paper-border)',
            backgroundColor: 'var(--color-paper-surface)',
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            overflowY: 'auto',
            boxShadow: 'var(--shadow-drawer)',
          }}
        >
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <span
                className={`entity-badge ${
                  selectedNode.group === 'PERSON'
                    ? 'entity-person'
                    : selectedNode.group === 'LOCATION'
                    ? 'entity-location'
                    : selectedNode.group === 'EVENT'
                    ? 'entity-event'
                    : 'entity-topic'
                }`}
              >
                {selectedNode.group}
              </span>
              <button
                type="button"
                onClick={() => setSelectedNode(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-ink-muted)' }}
              >
                <X size={16} />
              </button>
            </div>

            <h3
              className="font-display"
              style={{
                fontSize: '1.4rem',
                fontWeight: 600,
                color: 'var(--color-ink-primary)',
                marginTop: '0.6rem',
                lineHeight: 1.25,
              }}
            >
              {selectedNode.label}
            </h3>

            <p style={{ fontSize: '0.8rem', color: 'var(--color-ink-muted)', marginTop: '0.3rem' }}>
              Historical Entity in Archival Knowledge Graph
            </p>

            {/* Verified Relationships */}
            <div style={{ marginTop: '1.5rem' }}>
              <h4
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  color: 'var(--color-ink-muted)',
                  marginBottom: '0.6rem',
                }}
              >
                Verified Connections ({selectedEdges.length})
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {selectedEdges.map((edge, idx) => {
                  const otherId = edge.source === selectedNode.id ? edge.target : edge.source;
                  const otherNode = nodes.find((n) => n.id === otherId);
                  return (
                    <div
                      key={idx}
                      style={{
                        padding: '0.5rem 0.7rem',
                        backgroundColor: '#FFFFFF',
                        border: '1px solid var(--color-paper-border)',
                        borderRadius: 'var(--radius-xs)',
                        fontSize: '0.8rem',
                      }}
                    >
                      <div style={{ fontWeight: 600, color: 'var(--color-ink-primary)' }}>
                        {otherNode?.label || otherId}
                      </div>
                      <div
                        style={{
                          fontSize: '0.7rem',
                          color: 'var(--color-accent-oxblood)',
                          marginTop: '0.15rem',
                        }}
                      >
                        {edge.relationship} (Confidence: {Math.round(edge.confidence * 100)}%)
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div style={{ paddingTop: '1.5rem', borderTop: '1px solid var(--color-paper-border)' }}>
            <a
              href={`/explore?q=${encodeURIComponent(selectedNode.label)}`}
              className="btn-archival btn-oxblood"
              style={{ width: '100%' }}
            >
              <span>Explore Associated Documents</span>
              <ArrowRight size={14} />
            </a>
          </div>
        </aside>
      )}
    </div>
  );
}
