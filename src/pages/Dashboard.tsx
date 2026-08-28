import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookOpen, Map, MessageSquare, Target, ArrowUpRight, Sparkles, Flame } from "lucide-react";
import { useLearner } from "@/context/LearnerContext";
import { api, type DashboardData } from "@/lib/api";

const Dashboard = () => {
  const navigate = useNavigate();
  const { learnerId, learner, setLearner } = useLearner();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    if (!learnerId) return;
    return api.dashboard(learnerId).then((dash) => {
      setData(dash);
      if (dash.learner) setLearner(dash.learner);
    }).catch((e) => setError(e.message));
  };

  useEffect(() => {
    load();
  }, [learnerId, learner?.active_skill_id]);

  if (error) return <div className="bg-red-50 text-red-700 p-4 rounded-xl">{error}</div>;
  if (!data) return <p className="text-muted-foreground">Loading dashboard...</p>;

  const skills = data.enrolled_skills || [];
  const active = skills.find((s) => s.id === data.active_skill_id) || data.active_skill;
  const today = new Date().toISOString().slice(0, 10);
  const streakLive = (data.last_active_date || "") === today;

  const stats = [
    { icon: BookOpen, value: `${data.skills_mastered}/${data.skills_total}`, label: "Skills at target", sub: `${data.skills_count} on profile`, color: "text-primary" },
    { icon: Map, value: `${data.path_progress_percent}%`, label: "Path progress", sub: `${data.items_done}/${data.items_total} items`, color: "text-emerald-500" },
    { icon: Flame, value: `${data.streak_days}`, label: "Day streak", sub: streakLive ? "Active today" : "Learn today to keep it going", color: "text-orange-500" },
    { icon: Target, value: data.next_skill ? `${data.next_skill.current}%` : "—", label: "Next topic", sub: data.next_skill?.name || "Set a goal", color: "text-purple-500" },
  ];

  const switchSkill = async (skillId: string) => {
    if (!learnerId || skillId === data.active_skill_id) return;
    const res = await api.setActiveSkill(learnerId, skillId);
    if (res.learner) setLearner(res.learner);
    await load();
  };

  const openPath = async (skillId: string) => {
    if (!learnerId) return;
    const res = await api.setActiveSkill(learnerId, skillId);
    if (res.learner) setLearner(res.learner);
    navigate("/home/path");
  };

  const openChat = async (skillId: string) => {
    if (!learnerId) return;
    const res = await api.setActiveSkill(learnerId, skillId);
    if (res.learner) setLearner(res.learner);
    navigate(`/home/assistant?skill=${encodeURIComponent(skillId)}`);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
      <p className="text-muted-foreground mb-6">
        {active ? `Progress for ${active.name}` : data.goal ? `Roadmap toward ${data.goal}` : "Set a goal in chat, then assess and generate a path."}
      </p>

      <div className="mb-8">
        <div className="flex items-center justify-between gap-3 mb-3">
          <h2 className="text-lg font-bold">Your skills</h2>
          <button onClick={() => navigate("/home/assessment")} className="text-sm text-primary font-medium">
            Reassess
          </button>
        </div>
        {skills.length === 0 ? (
          <div className="border rounded-2xl p-6 bg-card text-sm text-muted-foreground">
            No skills yet. Tell the assistant what you want to learn and a skill card will appear here.
            <button onClick={() => navigate("/home/assistant")} className="ml-2 text-primary font-medium">
              Open assistant
            </button>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {skills.map((s) => {
              const selected = s.active || s.id === data.active_skill_id;
              return (
                <div
                  key={s.id}
                  className={`border rounded-2xl p-5 bg-card text-left ${
                    selected ? "border-primary ring-2 ring-primary/20" : ""
                  }`}
                >
                  <button type="button" onClick={() => switchSkill(s.id)} className="w-full text-left">
                    <p className="font-semibold text-lg">{s.name}</p>
                    <p className="text-xs text-muted-foreground mt-1 capitalize">
                      {(s.status || "not_assessed").replaceAll("_", " ")} · {s.overall_proficiency}% mastery
                    </p>
                    <div className="h-1.5 bg-muted rounded-full overflow-hidden mt-3">
                      <div className="h-full bg-primary" style={{ width: `${Math.min(100, s.overall_proficiency || 0)}%` }} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      Path {s.path_progress_percent || 0}% · {s.items_done || 0}/{s.items_total || 0} items
                    </p>
                    {s.next_title ? (
                      <p className="text-xs text-primary mt-1 truncate">Next: {s.next_title}</p>
                    ) : (
                      <p className="text-xs text-muted-foreground mt-1">No path yet for this skill</p>
                    )}
                  </button>
                  <div className="flex gap-2 mt-4">
                    <button
                      type="button"
                      onClick={() => openPath(s.id)}
                      className="flex-1 text-sm bg-primary text-primary-foreground px-3 py-2 rounded-xl"
                    >
                      Open path
                    </button>
                    <button
                      type="button"
                      onClick={() => openChat(s.id)}
                      className="flex-1 text-sm border px-3 py-2 rounded-xl"
                    >
                      Open chat
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((s) => (
          <div key={s.label} className="bg-card border border-border rounded-2xl p-5">
            <div className={`w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mb-3 ${s.color}`}>
              <s.icon className="w-5 h-5" />
            </div>
            <p className="text-2xl font-bold text-foreground">{s.value}</p>
            <p className="text-sm font-medium text-foreground">{s.label}</p>
            <p className="text-xs text-muted-foreground">{s.sub}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-4 mb-8">
        <div className="lg:col-span-2 bg-card border rounded-2xl p-6">
          <h2 className="text-lg font-bold mb-3">{active ? `${active.name} topics` : "Topic progress"}</h2>
          {(data.gaps || []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No skills yet — chat your goal or run an assessment.</p>
          ) : (
            <div className="space-y-3">
              {data.gaps.slice(0, 8).map((g) => (
                <div key={g.skill_id} className="text-sm">
                  <div className="flex justify-between mb-1 gap-3">
                    <span className="truncate">{g.name}</span>
                    <span className="text-muted-foreground shrink-0">
                      {g.current}% / {g.required}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: `${Math.min(100, g.current)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="bg-card border rounded-2xl p-6">
          <h2 className="text-lg font-bold mb-3">Next recommended</h2>
          {data.next_action ? (
            <>
              <p className="text-xs uppercase text-muted-foreground">{data.next_action.item_type} · week {data.next_action.week}</p>
              <p className="font-semibold mt-1">{data.next_action.title}</p>
              <p className="text-sm text-muted-foreground mt-2">{data.next_action.why}</p>
              <button onClick={() => active && openPath(active.id)} className="mt-4 bg-primary text-primary-foreground px-4 py-2 rounded-xl text-sm">
                Open path
              </button>
            </>
          ) : (
            <>
              <p className="text-sm text-muted-foreground mb-3">No path yet for this skill.</p>
              <button onClick={() => (active ? openPath(active.id) : navigate("/home/path"))} className="bg-primary text-primary-foreground px-4 py-2 rounded-xl text-sm">
                Generate path for this skill
              </button>
            </>
          )}
        </div>
      </div>

      {(data.badges || []).length > 0 && (
        <div className="flex flex-wrap gap-2 mb-8">
          {data.badges.map((b) => (
            <span key={b} className="text-xs bg-amber-50 text-amber-800 px-3 py-1 rounded-full">{b}</span>
          ))}
        </div>
      )}

      <h2 className="text-lg font-bold mb-4">Quick actions</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { icon: MessageSquare, title: "Assistant", desc: "Describe your goal", to: "/home/assistant", gradient: "from-blue-500 to-blue-600" },
          { icon: Target, title: "Assessment", desc: "Measure current level", to: "/home/assessment", gradient: "from-purple-500 to-violet-600" },
          { icon: Map, title: "Learning Path", desc: "Phased roadmap", to: "/home/path", gradient: "from-teal-500 to-cyan-500" },
          { icon: BookOpen, title: "Skill graph", desc: "Prerequisites map", to: "/home/graph", gradient: "from-indigo-500 to-purple-500" },
        ].map((a) => (
          <button
            key={a.title}
            onClick={() => navigate(a.to)}
            className={`bg-gradient-to-br ${a.gradient} rounded-2xl p-5 text-left text-primary-foreground relative`}
          >
            <a.icon className="w-5 h-5 mb-3" />
            <ArrowUpRight className="w-4 h-4 absolute top-4 right-4 opacity-60" />
            <p className="font-bold">{a.title}</p>
            <p className="text-sm opacity-80 mt-1">{a.desc}</p>
          </button>
        ))}
      </div>

      <div className="bg-card border rounded-2xl p-6">
        <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" /> Recent activity
        </h2>
        {data.recent_completions.length === 0 ? (
          <p className="text-sm text-muted-foreground">Completions will appear here.</p>
        ) : (
          data.recent_completions.map((item) => (
            <div key={item.id} className="flex justify-between py-2 text-sm">
              <span>{item.title}</span>
              <span className="text-muted-foreground capitalize">{item.status}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Dashboard;
