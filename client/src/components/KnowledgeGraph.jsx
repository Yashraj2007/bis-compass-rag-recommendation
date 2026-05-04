import React, { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import "./KnowledgeGraph.css";

// Simple mock graph layout generator based on results
const generateGraphNodes = (results) => {
  if (!results || results.length === 0) return { nodes: [], edges: [] };
  
  const nodes = [];
  const edges = [];
  const centerX = 150;
  const centerY = 150;
  
  // Create primary node (Query)
  nodes.push({ id: "query", label: "Query", x: centerX, y: centerY, baseX: centerX, baseY: centerY, type: "query", radius: 30 });

  const radiusDist = 90;
  const angleStep = (2 * Math.PI) / results.length;

  results.forEach((res, i) => {
    const angle = i * angleStep;
    const nx = centerX + radiusDist * Math.cos(angle);
    const ny = centerY + radiusDist * Math.sin(angle);
    
    // Primary Standard node
    const nodeId = res.id;
    nodes.push({ id: nodeId, label: res.id, x: nx, y: ny, baseX: nx, baseY: ny, type: "primary", radius: 25, title: res.title });
    
    // Connect to query
    edges.push({ source: "query", target: nodeId });

    // Add 1 or 2 related standards as secondary nodes
    res.related_standards.slice(0, 2).forEach((related, j) => {
      const subAngle = angle + (j === 0 ? 0.4 : -0.4);
      const subRadius = radiusDist + 60;
      const sx = centerX + subRadius * Math.cos(subAngle);
      const sy = centerY + subRadius * Math.sin(subAngle);
      
      const subId = `${nodeId}-${related}`;
      nodes.push({ id: subId, label: related, x: sx, y: sy, baseX: sx, baseY: sy, type: "secondary", radius: 18, title: related });
      edges.push({ source: nodeId, target: subId });
    });
  });

  return { nodes, edges };
};

const KnowledgeGraph = ({ results }) => {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [hoveredNode, setHoveredNode] = useState(null);
  const [draggingNode, setDraggingNode] = useState(null);
  const [dragStart, setDragStart] = useState(null);
  const svgRef = useRef(null);

  useEffect(() => {
    if (results && results.length > 0) {
      setGraphData(generateGraphNodes(results));
    } else {
      setGraphData({ nodes: [], edges: [] });
    }
  }, [results]);

  const handlePointerDown = (e, nodeId) => {
    e.target.setPointerCapture(e.pointerId);
    setDraggingNode(nodeId);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handlePointerMove = (e) => {
    if (draggingNode && dragStart) {
      const dx = (e.clientX - dragStart.x);
      const dy = (e.clientY - dragStart.y);
      
      setGraphData(prev => ({
        ...prev,
        nodes: prev.nodes.map(n => 
          n.id === draggingNode 
            ? { ...n, x: n.baseX + dx, y: n.baseY + dy }
            : n
        )
      }));
    }
  };

  const handlePointerUp = () => {
    if (draggingNode) {
      setDraggingNode(null);
      setDragStart(null);
      // Snap all nodes back to their original base positions like an elastic string
      setGraphData(prev => ({
        ...prev,
        nodes: prev.nodes.map(n => ({ ...n, x: n.baseX, y: n.baseY }))
      }));
    }
  };

  if (!results || results.length === 0) {
    return (
      <div className="knowledge-graph-container glass-panel empty">
        <p>Submit a query to generate the Knowledge Graph</p>
      </div>
    );
  }

  return (
    <div className="knowledge-graph-container glass-panel" style={{ overflow: "hidden" }}>
      <h3 className="panel-title">Knowledge Graph</h3>
      <div className="graph-svg-wrapper">
        <svg 
          ref={svgRef}
          width="100%" 
          height="300" 
          viewBox="0 0 300 300"
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
          style={{ touchAction: "none" }}
        >
          {/* Edges */}
          {graphData.edges.map((edge, i) => {
            const sourceNode = graphData.nodes.find(n => n.id === edge.source);
            const targetNode = graphData.nodes.find(n => n.id === edge.target);
            if (!sourceNode || !targetNode) return null;
            
            const isLineDragging = draggingNode === sourceNode.id || draggingNode === targetNode.id;
            
            return (
              <motion.line
                key={`edge-${i}`}
                animate={{ 
                  x1: sourceNode.x, 
                  y1: sourceNode.y, 
                  x2: targetNode.x, 
                  y2: targetNode.y 
                }}
                stroke="var(--bg-card-border)"
                strokeWidth="2"
                initial={{ opacity: 0 }}
                transition={
                  isLineDragging 
                    ? { type: "tween", duration: 0 } 
                    : { type: "spring", stiffness: 400, damping: 25 }
                }
              />
            );
          })}

          {/* Nodes */}
          {graphData.nodes.map((node, i) => {
            const isHovered = hoveredNode === node.id;
            const isDragging = draggingNode === node.id;
            
            return (
              <g 
                key={node.id}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onPointerDown={(e) => handlePointerDown(e, node.id)}
                style={{ cursor: isDragging ? "grabbing" : "grab" }}
              >
                <motion.circle
                  r={node.radius}
                  className={`node-circle node-${node.type} ${isHovered || isDragging ? "hovered" : ""}`}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ 
                    cx: node.x, 
                    cy: node.y, 
                    scale: isDragging ? 1.1 : 1, 
                    opacity: 1 
                  }}
                  transition={
                    isDragging 
                      ? { cx: { duration: 0 }, cy: { duration: 0 }, scale: { duration: 0.1 } } 
                      : { type: "spring", stiffness: 400, damping: 25 } 
                  }
                />
                <motion.text
                  animate={{ x: node.x, y: node.y, opacity: 1 }}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="node-text"
                  initial={{ opacity: 0 }}
                  transition={
                    isDragging 
                      ? { duration: 0 } 
                      : { type: "spring", stiffness: 400, damping: 25 }
                  }
                  style={{ pointerEvents: "none" }}
                >
                  {node.type === "query" ? "Q" : node.label.replace("IS ", "")}
                </motion.text>
              </g>
            );
          })}
        </svg>

        {/* Tooltip outside SVG for easier HTML styling */}
        {hoveredNode && (
          <div className="graph-tooltip" style={{ pointerEvents: "none" }}>
            {graphData.nodes.find(n => n.id === hoveredNode)?.title || "Query"}
          </div>
        )}
      </div>
    </div>
  );
};

export default KnowledgeGraph;
