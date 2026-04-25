"use client";

import { useEffect, useMemo } from "react";
import dagre from "dagre";
import { motion, AnimatePresence } from "framer-motion";
import { X, TreeStructure } from "@phosphor-icons/react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  Handle,
  Position,
  MarkerType,
  type Node,
  type Edge,
  type NodeTypes,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";

type GraphNode = {
  id: string;
  type?: string;
  label?: string;
  [key: string]: unknown;
};

type GraphEdge = {
  source: string;
  target: string;
  type?: string;
};

type CertNodeData = {
  typeStr: string;
  detail: string;
  stroke: string;
};

const NODE_W = 240;
const NODE_H = 96;

function nodeStroke(type: string): string {
  const t = type.toLowerCase();
  if (t.includes("decision")) return "#34d399";
  if (t.includes("certificate")) return "#a78bfa";
  if (t.includes("risk") || t.includes("fraud")) return "#f87171";
  if (t.includes("policy")) return "#38bdf8";
  if (t.includes("evidence") || t.includes("artifact")) return "#fbbf24";
  if (t.includes("vendor") || t.includes("invoice")) return "#94a3b8";
  if (t.includes("case")) return "#e4e4e7";
  return "#71717a";
}

function layoutWithDagre(
  rfNodes: Node<CertNodeData>[],
  rfEdges: Edge[],
): { nodes: Node<CertNodeData>[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir: "TB",
    align: "UL",
    nodesep: 56,
    ranksep: 72,
    marginx: 48,
    marginy: 48,
    acyclicer: "greedy",
    ranker: "network-simplex",
  });

  rfNodes.forEach((n) => {
    g.setNode(n.id, { width: NODE_W, height: NODE_H });
  });

  rfEdges.forEach((e) => {
    if (g.hasNode(e.source) && g.hasNode(e.target)) {
      g.setEdge(e.source, e.target);
    }
  });

  dagre.layout(g);

  const nodes = rfNodes.map((node) => {
    const pos = g.node(node.id);
    if (!pos || typeof pos.x !== "number") {
      return { ...node, position: { x: 0, y: 0 } };
    }
    return {
      ...node,
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
      position: {
        x: pos.x - NODE_W / 2,
        y: pos.y - NODE_H / 2,
      },
    };
  });

  return { nodes, edges: rfEdges };
}

function CertNode({
  data,
}: {
  data: CertNodeData;
}) {
  return (
    <div
      className="rounded-xl px-3 py-2.5 shadow-lg select-none"
      style={{
        width: NODE_W,
        minHeight: NODE_H,
        background: "rgba(24, 24, 27, 0.96)",
        borderWidth: 2,
        borderStyle: "solid",
        borderColor: data.stroke,
        boxSizing: "border-box",
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!size-2.5 !border !border-zinc-600 !bg-zinc-800"
      />
      <p className="text-[11px] font-semibold leading-tight text-zinc-100 pr-1">
        {data.typeStr}
      </p>
      <p className="mt-1.5 text-[10px] font-mono leading-snug text-zinc-400 break-words whitespace-normal max-h-[52px] overflow-y-auto">
        {data.detail}
      </p>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!size-2.5 !border !border-zinc-600 !bg-zinc-800"
      />
    </div>
  );
}

const nodeTypes: NodeTypes = {
  cert: CertNode,
};

function GraphCanvas({
  initialNodes,
  initialEdges,
}: {
  initialNodes: Node<CertNodeData>[];
  initialEdges: Edge[];
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const { fitView } = useReactFlow();

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      fitView({ padding: 0.2, duration: 280, maxZoom: 1.25 });
    });
    return () => cancelAnimationFrame(id);
  }, [nodes, edges, fitView]);

  return (
    <div className="h-[min(72vh,720px)] w-full rounded-xl border border-white/10 bg-zinc-950/80 overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        panOnScroll
        zoomOnScroll
        zoomOnPinch
        minZoom={0.15}
        maxZoom={1.6}
        defaultEdgeOptions={{
          type: "smoothstep",
          style: { stroke: "rgba(161,161,170,0.45)", strokeWidth: 1.5 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 14,
            height: 14,
            color: "rgba(161,161,170,0.55)",
          },
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={20} size={1} color="rgba(255,255,255,0.06)" />
        <Controls className="!bg-zinc-900/95 !border-white/10 !shadow-xl [&_button]:!fill-zinc-300" />
        <MiniMap
          className="!bg-zinc-900/90 !border !border-white/10"
          nodeColor={(n) => {
            const d = n.data as CertNodeData | undefined;
            return d?.stroke ?? "#52525b";
          }}
          maskColor="rgba(0,0,0,0.55)"
        />
      </ReactFlow>
    </div>
  );
}

function buildFlowElements(
  rawNodes: GraphNode[],
  rawEdges: GraphEdge[],
): { nodes: Node<CertNodeData>[]; edges: Edge[] } {
  const nodeIds = new Set(rawNodes.map((n) => String(n.id)));
  const edgesIn = rawEdges.filter(
    (e) => nodeIds.has(String(e.source)) && nodeIds.has(String(e.target)),
  );

  const rfNodes: Node<CertNodeData>[] = rawNodes.map((n) => {
    const typeStr = String(n.type || "node");
    const detail = String(n.label ?? n.id ?? typeStr);
    return {
      id: String(n.id),
      type: "cert",
      position: { x: 0, y: 0 },
      data: {
        typeStr,
        detail,
        stroke: nodeStroke(typeStr),
      },
    };
  });

  const rfEdges: Edge[] = edgesIn.map((e, i) => ({
    id: `e-${String(e.source)}-${String(e.target)}-${i}`,
    source: String(e.source),
    target: String(e.target),
    label: String(e.type || "link"),
    labelStyle: { fill: "#d4d4d8", fontSize: 10, fontWeight: 500 },
    labelBgStyle: { fill: "#18181b", fillOpacity: 0.92 },
    labelBgPadding: [6, 4] as [number, number],
    labelBgBorderRadius: 4,
  }));

  return layoutWithDagre(rfNodes, rfEdges);
}

export function CertificateGraphModal({
  open,
  onClose,
  graph,
}: {
  open: boolean;
  onClose: () => void;
  graph: Record<string, unknown> | null;
}) {
  const { nodes, edges, title } = useMemo(() => {
    if (!graph || typeof graph !== "object") {
      return { nodes: [] as GraphNode[], edges: [] as GraphEdge[], title: "" };
    }
    const rawNodes = graph.nodes;
    const rawEdges = graph.edges;
    const n = Array.isArray(rawNodes) ? (rawNodes as GraphNode[]) : [];
    const e = Array.isArray(rawEdges) ? (rawEdges as GraphEdge[]) : [];
    const t =
      (typeof graph.certificate_version === "string" &&
        graph.certificate_version) ||
      "Trust / certificate graph";
    return { nodes: n.slice(0, 96), edges: e, title: t };
  }, [graph]);

  const flow = useMemo(
    () => (nodes.length ? buildFlowElements(nodes, edges) : null),
    [nodes, edges],
  );

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="cert-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            key="cert-panel"
            initial={{ scale: 0.96, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.96, opacity: 0 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
            className="relative w-full max-w-6xl max-h-[92vh] rounded-2xl border border-white/15 bg-zinc-950 shadow-2xl overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/10 shrink-0">
              <div className="flex items-center gap-2 min-w-0">
                <TreeStructure size={22} className="text-violet-400 shrink-0" />
                <div className="min-w-0">
                  <h2 className="text-sm font-semibold text-white truncate">
                    Decision certificate graph
                  </h2>
                  <p className="text-[10px] font-mono text-zinc-500 truncate">
                    {title} · {nodes.length} nodes · {edges.length} edges · drag
                    to pan, scroll to zoom
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-white/10 text-zinc-400 transition-colors"
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-4 flex-1 min-h-0 overflow-hidden">
              {nodes.length === 0 ? (
                <p className="text-sm text-zinc-500 text-center py-12">
                  No graph payload on this run. It appears after a graded{" "}
                  <code className="font-mono text-zinc-400">submit_decision</code>{" "}
                  from the LedgerShield backend.
                </p>
              ) : flow ? (
                <ReactFlowProvider>
                  <GraphCanvas
                    key={`${nodes.length}-${edges.length}`}
                    initialNodes={flow.nodes}
                    initialEdges={flow.edges}
                  />
                </ReactFlowProvider>
              ) : null}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
