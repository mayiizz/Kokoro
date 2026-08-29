import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import ReactFlow, { Background, Controls, MiniMap, ReactFlowProvider, type Node, type Edge } from "reactflow";
import "reactflow/dist/style.css";
import { useLearner } from "@/context/LearnerContext";
import { api, type GraphPayload } from "@/lib/api";

const statusFill: Record<string, string> = {
  proficient: "#d1fae5",
  learning: "#fef3c7",
  weak: "#ffedd5",
  not_assessed: "#fee2e2",
};

const SkillGraph = () => {
  const { learnerId, learner } = useLearner();
  const navigate = useNavigate();
  const [graph, setGraph] = useState<GraphPayload | null>(null);
  const [selected, setSelected] = useState<GraphPayload["nodes"][0] | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!learnerId) return;
    api.graph(learnerId).then((g) => {
      setGraph(g);
      setExpanded(new Set());
      setSelected(null);
    }).catch((e) => setError(e.message));
  }, [learnerId, learner?.active_skill_id]);

  const visibleIds = useMemo(() => {
    if (!graph) return new Set<string>();
    const ids = new Set<string>();
    for (const n of graph.nodes) {
      if (n.kind === "skill" || n.kind === "major" || !n.parent_id) {
        ids.add(n.id);
        continue;
      }
      const parent = graph.nodes.find((p) => p.id === n.parent_id);
      if (parent?.kind === "skill") ids.add(n.id);
      else if (expanded.has(n.parent_id || "")) ids.add(n.id);
    }
    const skill = graph.nodes.find((n) => n.kind === "skill");
    if (skill) ids.add(skill.id);
    return ids;
  }, [graph, expanded]);

  const { nodes, edges } = useMemo(() => {
    if (!graph) return { nodes: [] as Node[], edges: [] as Edge[] };
    const shown = graph.nodes.filter((n) => visibleIds.has(n.id));
    const ns: Node[] = shown.map((n, i) => {
      const bg = statusFill[n.status || ""] || "#e2e8f0";
      const majors = shown.filter((x) => x.kind === "major" || (x.kind === "topic" && graph.nodes.find((p) => p.id === x.parent_id)?.kind === "skill"));
      const isMajor = n.kind === "major" || n.kind === "skill";
      const col = n.kind === "skill" ? 0 : isMajor ? 1 : 2;
      const row = n.kind === "skill" ? 0 : majors.findIndex((m) => m.id === (n.kind === "major" ? n.id : n.parent_id));
      return {
        id: n.id,
        data: { label: `${n.name}\n${n.status || "not assessed"} · ${n.proficiency}%` },
        position: n.kind === "skill"
          ? { x: 40, y: 40 }
          : { x: col * 240, y: 40 + Math.max(row, 0) * 130 + (n.kind === "topic" ? 40 : 0) + (i % 3) * 10 },
        style: { background: bg, borderRadius: 12, padding: 10, width: 180, fontSize: 12, whiteSpace: "pre-line", fontWeight: isMajor ? 600 : 400 },
      };
    });
    const es: Edge[] = graph.edges
      .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
      .map((e, i) => ({
        id: `e-${i}`,
        source: e.source,
        target: e.target,
        animated: e.relation !== "PARENT_OF",
      }));
    return { nodes: ns, edges: es };
  }, [graph, visibleIds]);

  const onNodeClick = useCallback(
    (_: unknown, node: Node) => {
      const found = graph?.nodes.find((n) => n.id === node.id);
      setSelected(found || null);
      if (found?.kind === "major" || found?.kind === "skill") {
        setExpanded((prev) => {
          const next = new Set(prev);
          if (next.has(found.id)) next.delete(found.id);
          else next.add(found.id);
          return next;
        });
      }
    },
    [graph]
  );

  const children = (graph?.nodes || []).filter((n) => selected && n.parent_id === selected.id);

  return (
    <div>
      <h1 className="text-2xl font-bold">{graph?.skill?.name ? `${graph.skill.name} topics` : "Skill graph"}</h1>
      <p className="text-muted-foreground mb-4">
        Click a major topic to reveal subtopics. Green = proficient, amber = learning, orange = weak, red = not assessed.
      </p>
      {error && <div className="bg-red-50 text-red-700 p-4 rounded-xl mb-4">{error}</div>}
      <div className="h-[520px] bg-card border rounded-2xl overflow-hidden">
        <ReactFlowProvider>
          <ReactFlow nodes={nodes} edges={edges} onNodeClick={onNodeClick} fitView>
            <Background />
            <MiniMap />
            <Controls />
          </ReactFlow>
        </ReactFlowProvider>
      </div>
      {selected && (
        <div className="mt-4 bg-card border rounded-2xl p-5">
          <h2 className="font-semibold">{selected.name}</h2>
          <p className="text-sm text-muted-foreground mt-1 capitalize">
            {selected.kind || "topic"} · {(selected.status || "not_assessed").replaceAll("_", " ")} · proficiency {selected.proficiency}%
          </p>
          {children.length > 0 && (
            <div className="mt-3">
              <p className="text-xs font-semibold uppercase text-muted-foreground mb-1">Subtopics</p>
              <ul className="text-sm space-y-1">
                {children.map((c) => (
                  <li key={c.id}>
                    {c.name} · {(c.status || "not_assessed").replaceAll("_", " ")}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {selected.kind === "topic" && (
            <button
              onClick={() => navigate("/home/path")}
              className="mt-4 bg-primary text-primary-foreground px-4 py-2 rounded-xl text-sm"
            >
              Go to learn
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default SkillGraph;
