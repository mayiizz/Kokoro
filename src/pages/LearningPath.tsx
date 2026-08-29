import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle, ExternalLink, Flag, RefreshCw, Search, Star } from "lucide-react";
import { useLearner } from "@/context/LearnerContext";
import { api, type LearningPath, type PathItem } from "@/lib/api";

const typeStyles: Record<string, string> = {
  course: "bg-blue-50 text-blue-700",
  project: "bg-purple-50 text-purple-700",
  assessment: "bg-amber-50 text-amber-700",
  video: "bg-red-50 text-red-700",
  textbook: "bg-emerald-50 text-emerald-700",
  website: "bg-slate-100 text-slate-700",
};

const LearningPathPage = () => {
  const { learnerId, learner, refresh } = useLearner();
  const navigate = useNavigate();
  const [path, setPath] = useState<LearningPath | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skillName, setSkillName] = useState("");

  const load = async () => {
    if (!learnerId) return;
    setPath(await api.getPath(learnerId));
    const skills = await api.learnerSkills(learnerId).catch(() => ({ skills: [], active_skill_id: "" }));
    const active = skills.skills.find((s) => s.id === skills.active_skill_id || s.active);
    setSkillName(active?.name || "");
  };

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [learnerId, learner?.active_skill_id]);

  const generate = async () => {
    if (!learnerId) return;
    setLoading(true);
    setError(null);
    try {
      setPath(await api.generatePath(learnerId));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to generate path");
    } finally {
      setLoading(false);
    }
  };

  const moreForTopic = async (topicId: string) => {
    if (!learnerId) return;
    setLoading(true);
    try {
      setPath(await api.morePathResources(learnerId, topicId));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not load more resources");
    } finally {
      setLoading(false);
    }
  };

  const act = async (item: PathItem, payload: { status?: string; feedback?: string }) => {
    setLoading(true);
    try {
      setPath(await api.patchItem(item.id, payload));
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Update failed");
    } finally {
      setLoading(false);
    }
  };

  const groups = useMemo(() => {
    const items = path?.items || [];
    if (path?.phases && path.phases.length) return path.phases;
    const map = new Map<string, PathItem[]>();
    for (const item of items) {
      const key = item.phase || `Week ${item.week || 1}`;
      map.set(key, [...(map.get(key) || []), item]);
    }
    return Array.from(map.entries()).map(([name, groupItems]) => ({ name, items: groupItems }));
  }, [path]);

  const items = path?.items || [];

  return (
    <div>
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold">Learning path{skillName ? ` · ${skillName}` : ""}</h1>
          <p className="text-muted-foreground">Learn → practice → build → assess. Each step is ranked for your gaps, budget, and time.</p>
        </div>
        <div className="flex gap-2">
          {items.length > 0 && (
            <button onClick={async () => learnerId && setPath(await api.adaptPath(learnerId))} className="border px-4 py-2 rounded-xl text-sm flex items-center gap-2">
              <RefreshCw className="w-4 h-4" /> Replan remaining
            </button>
          )}
          <button onClick={generate} disabled={loading} className="bg-primary text-primary-foreground px-4 py-2 rounded-xl text-sm flex items-center gap-2 disabled:opacity-50">
            <Search className="w-4 h-4" />
            {loading ? "Working..." : items.length ? "Regenerate" : "Generate path"}
          </button>
        </div>
      </div>

      {error && <div className="bg-red-50 text-red-700 p-4 rounded-xl mb-6">{error}</div>}

      {path?.next_action && (
        <div className="bg-primary/5 border border-primary/20 rounded-2xl p-5 mb-6">
          <p className="text-xs font-semibold uppercase text-primary mb-1">Up next · Week {path.next_action.week}</p>
          <p className="font-semibold">{path.next_action.title}</p>
          <p className="text-sm text-muted-foreground mt-1">{path.next_action.why}</p>
        </div>
      )}

      {items.length === 0 ? (
        <div className="bg-card border rounded-2xl p-10 text-center text-muted-foreground">
          Set a goal, select this skill on the dashboard, then generate a catalog-backed path.
        </div>
      ) : (
        groups.map((phase) => (
          <section key={phase.name} className="mb-8">
            <h2 className="text-lg font-bold mb-3">Module — {phase.name}</h2>
            <div className="space-y-4">
              {phase.items.map((item) => (
                <div key={item.id} className={`bg-card border rounded-2xl p-6 ${item.status === "done" ? "opacity-80" : ""}`}>
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${typeStyles[item.item_type] || "bg-muted"}`}>{item.item_type}</span>
                    <span className="text-xs text-muted-foreground">Week {item.week} · {item.level} · {item.hours}h · {item.cost}</span>
                    {item.locked && <span className="text-xs text-amber-700">Locked — finish prerequisites</span>}
                  </div>
                  {item.milestone_title && (
                    <p className="text-xs font-semibold text-primary mb-1 flex items-center gap-1">
                      <Flag className="w-3 h-3" /> {item.milestone_title}
                    </p>
                  )}
                  <h3 className="font-bold text-lg">{item.title}</h3>
                  {item.topic_id && <p className="text-xs text-muted-foreground mt-1">Topic module</p>}
                  <p className="text-sm mt-2"><span className="font-semibold">Why this: </span>{item.why}</p>
                  {(item.resources || []).length > 0 && (
                    <div className="grid sm:grid-cols-2 gap-2 mt-4">
                      {item.resources!.map((r, idx) => {
                        const href = r.url || item.url || "";
                        const host = (() => {
                          try {
                            return href ? new URL(href).hostname.replace(/^www\./, "") : "";
                          } catch {
                            return "";
                          }
                        })();
                        return (
                          <a
                            key={`${href || r.title}-${idx}`}
                            href={href || undefined}
                            target="_blank"
                            rel="noreferrer"
                            className="border rounded-xl p-3 text-sm hover:border-primary block"
                          >
                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                              {r.rank != null && <span className="text-[10px] font-bold text-primary">#{r.rank}</span>}
                              <span className={`text-[10px] px-1.5 py-0.5 rounded capitalize ${typeStyles[r.type || ""] || "bg-muted"}`}>{r.type || "resource"}</span>
                              {r.rating && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 flex items-center gap-0.5">
                                  <Star className="w-3 h-3 fill-amber-500 text-amber-500" />
                                  {r.rating}
                                </span>
                              )}
                            </div>
                            <p className="font-medium">{r.title}</p>
                            <p className="text-xs text-muted-foreground mt-1">{r.about || r.why || ""}</p>
                            {host && (
                              <p className="text-xs text-primary mt-2 flex items-center gap-1">
                                <ExternalLink className="w-3 h-3" /> Open on {host}
                              </p>
                            )}
                          </a>
                        );
                      })}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-2 mt-4">
                    {item.url && (item.resources || []).length === 0 && (
                      <a href={item.url} target="_blank" rel="noreferrer" className="text-sm border px-3 py-2 rounded-xl flex items-center gap-1">
                        Open resource <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                    {item.status === "todo" && !item.locked && (
                      <button onClick={() => act(item, { status: "done" })} className="text-sm bg-emerald-600 text-white px-3 py-2 rounded-xl flex items-center gap-1">
                        <CheckCircle className="w-4 h-4" /> Mark complete
                      </button>
                    )}
                    {item.topic_id && (
                      <>
                        <button onClick={() => moreForTopic(item.topic_id!)} className="text-sm border px-3 py-2 rounded-xl">
                          More resources for this topic
                        </button>
                        <button onClick={() => navigate("/home/assessment")} className="text-sm border px-3 py-2 rounded-xl">
                          Reassess this topic
                        </button>
                      </>
                    )}
                    {item.status === "todo" && (
                      <>
                        <button onClick={() => act(item, { feedback: "too_hard" })} className="text-sm border px-3 py-2 rounded-xl">Too hard</button>
                        <button onClick={() => act(item, { feedback: "not_relevant" })} className="text-sm border px-3 py-2 rounded-xl">Not relevant</button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
};

export default LearningPathPage;
