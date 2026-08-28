import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Plus } from "lucide-react";
import { useLearner } from "@/context/LearnerContext";
import { api } from "@/lib/api";

const SUGGESTED = ["Guitar", "Python", "Frontend", "Machine Learning", "Data Analyst", "DBMS"];

type EnrolledSkill = {
  id: string;
  name: string;
  overall_proficiency: number;
  status: string;
  active: boolean;
};

const SkillSwitcher = () => {
  const { learnerId, learner, setLearner } = useLearner();
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [skills, setSkills] = useState<EnrolledSkill[]>([]);
  const [activeId, setActiveId] = useState(learner?.active_skill_id || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const boxRef = useRef<HTMLDivElement | null>(null);

  const loadSkills = async () => {
    if (!learnerId) return;
    const res = await api.learnerSkills(learnerId);
    setSkills(res.skills || []);
    setActiveId(res.active_skill_id || learner?.active_skill_id || "");
  };

  useEffect(() => {
    loadSkills().catch(() => setSkills([]));
  }, [learnerId, learner?.active_skill_id]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
        setAdding(false);
        setError(null);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const active = skills.find((s) => s.id === activeId) || skills.find((s) => s.active);
  const suggestions = SUGGESTED.filter(
    (s) => !skills.some((e) => e.name.toLowerCase() === s.toLowerCase() || e.id === s.toLowerCase().replace(/\s+/g, "-"))
  );

  const switchTo = async (skillId: string) => {
    if (!learnerId || skillId === activeId) {
      setOpen(false);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.setActiveSkill(learnerId, skillId);
      if (res.learner) setLearner(res.learner);
      setActiveId(res.active_skill_id || skillId);
      await loadSkills();
      setOpen(false);
      setAdding(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not switch skill");
    } finally {
      setBusy(false);
    }
  };

  const addSkill = async (raw: string) => {
    const label = raw.trim();
    if (!learnerId || !label || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.resolveSkill(label, learnerId);
      if (res.learner) setLearner(res.learner);
      else if (res.skill?.id) {
        const active = await api.setActiveSkill(learnerId, res.skill.id);
        if (active.learner) setLearner(active.learner);
      }
      setName("");
      await loadSkills();
      setAdding(false);
      setOpen(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not add that skill");
    } finally {
      setBusy(false);
    }
  };

  if (!learnerId) return null;

  return (
    <div className="relative" ref={boxRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-xl border bg-background px-3 py-1.5 text-sm font-semibold hover:border-primary"
      >
        <span className="w-7 h-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center text-xs font-bold uppercase">
          {(active?.name || "Skill").slice(0, 2)}
        </span>
        <span className="max-w-[140px] truncate">{active?.name || "Choose a skill"}</span>
        <ChevronDown className={`w-4 h-4 text-muted-foreground transition ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-card border rounded-2xl shadow-lg z-30 p-2">
          <p className="px-2 py-1 text-[11px] uppercase tracking-wide text-muted-foreground">Your skills</p>
          <div className="max-h-56 overflow-auto">
            {skills.length === 0 && <p className="px-3 py-2 text-sm text-muted-foreground">No skills yet. Add one below.</p>}
            {skills.map((s) => {
              const selected = s.id === activeId || s.active;
              return (
                <button
                  key={s.id}
                  type="button"
                  disabled={busy}
                  onClick={() => switchTo(s.id)}
                  className={`w-full flex items-center justify-between gap-2 rounded-xl px-3 py-2 text-left ${
                    selected ? "bg-primary/10" : "hover:bg-muted"
                  }`}
                >
                  <span>
                    <span className="block text-sm font-medium">{s.name}</span>
                    <span className="block text-[11px] text-muted-foreground capitalize">
                      {(s.status || "not_assessed").replaceAll("_", " ")} · {s.overall_proficiency}%
                    </span>
                  </span>
                  {selected && <Check className="w-4 h-4 text-primary shrink-0" />}
                </button>
              );
            })}
          </div>

          <div className="border-t mt-2 pt-2">
            {!adding ? (
              <button
                type="button"
                onClick={() => setAdding(true)}
                className="w-full flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-primary hover:bg-primary/5"
              >
                <Plus className="w-4 h-4" /> Learn another skill
              </button>
            ) : (
              <div className="px-2 pb-2 space-y-2">
                <p className="text-xs text-muted-foreground">Add a skill to your profile, then we switch to it.</p>
                <div className="flex flex-wrap gap-1">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      type="button"
                      disabled={busy}
                      onClick={() => addSkill(s)}
                      className="text-xs border rounded-full px-2 py-1 hover:border-primary"
                    >
                      {s}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addSkill(name)}
                    placeholder="e.g. Piano, Java, Spanish"
                    className="flex-1 border rounded-xl px-3 py-2 text-sm bg-background"
                  />
                  <button
                    type="button"
                    disabled={busy || !name.trim()}
                    onClick={() => addSkill(name)}
                    className="bg-primary text-primary-foreground px-3 py-2 rounded-xl text-sm disabled:opacity-50"
                  >
                    {busy ? "..." : "Add"}
                  </button>
                </div>
              </div>
            )}
          </div>
          {error && <p className="px-3 py-2 text-xs text-red-600">{error}</p>}
        </div>
      )}
    </div>
  );
};

export default SkillSwitcher;
