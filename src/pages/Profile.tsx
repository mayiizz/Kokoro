import { useEffect, useState } from "react";
import { Plus, Flame } from "lucide-react";
import { useLearner } from "@/context/LearnerContext";
import { api, type Learner } from "@/lib/api";

function gapLabels(gaps: Learner["skill_gaps"]): string {
  return (gaps || [])
    .map((g) => (typeof g === "string" ? g : g.name || g.skill_id || ""))
    .filter(Boolean)
    .join(", ");
}

const Profile = () => {
  const { learner, learnerId, setLearner } = useLearner();
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [courseTitle, setCourseTitle] = useState("");
  const [courseSkills, setCourseSkills] = useState("");
  const [form, setForm] = useState({
    name: learner?.name || "",
    experience_level: learner?.experience_level || "Student",
    interests: (learner?.interests || []).join(", "),
    goal: learner?.goal || "",
    learning_preference: learner?.learning_preference || "hands-on",
    hours_per_week: String(learner?.hours_per_week || 10),
    hours_per_day: String(learner?.hours_per_day || 2),
    budget: learner?.budget || "free",
    target_role: learner?.target_role || "",
    skill_gaps: gapLabels(learner?.skill_gaps || []),
    skills: (learner?.skills || []).map((s) => s.name).join(", "),
  });

  useEffect(() => {
    if (!learner) return;
    setForm({
      name: learner.name || "",
      experience_level: learner.experience_level || "Student",
      interests: (learner.interests || []).join(", "),
      goal: learner.goal || "",
      learning_preference: learner.learning_preference || "hands-on",
      hours_per_week: String(learner.hours_per_week || 10),
      hours_per_day: String(learner.hours_per_day || 2),
      budget: learner.budget || "free",
      target_role: learner.target_role || "",
      skill_gaps: gapLabels(learner.skill_gaps || []),
      skills: (learner.skills || []).map((s) => s.name).join(", "),
    });
  }, [learner]);

  if (!learner || !learnerId) return <p className="text-muted-foreground">Sign in to edit your profile.</p>;

  const splitList = (value: string) =>
    value.split(",").map((v) => v.trim()).filter(Boolean);

  const save = async () => {
    setError(null);
    setSaved(false);
    try {
      const updated = await api.updateLearner(learnerId, {
        name: form.name,
        experience_level: form.experience_level,
        interests: splitList(form.interests),
        goal: form.goal,
        learning_preference: form.learning_preference,
        hours_per_week: Number(form.hours_per_week) || 10,
        hours_per_day: Number(form.hours_per_day) || 2,
        budget: form.budget,
        target_role: form.target_role,
        skill_gaps: splitList(form.skill_gaps),
        skills: splitList(form.skills).map((name) => ({ name, source: "manual", level: "beginner" })),
      });
      setLearner(updated);
      setSaved(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const addCourse = async () => {
    if (!courseTitle.trim()) return;
    try {
      const updated = await api.addCourse(learnerId, courseTitle.trim(), splitList(courseSkills));
      setLearner(updated);
      setCourseTitle("");
      setCourseSkills("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not add course");
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-foreground">My Profile</h1>
      <p className="text-muted-foreground mb-6">Interests, experience, completed courses, and objectives drive your path.</p>

      {error && <div className="bg-red-50 text-red-700 p-4 rounded-xl mb-4">{error}</div>}
      {saved && <div className="bg-emerald-50 text-emerald-700 p-4 rounded-xl mb-4">Profile saved.</div>}

      <div className="bg-orange-50 border border-orange-200 rounded-2xl p-5 mb-6 flex items-center gap-4">
        <div className="w-12 h-12 rounded-2xl bg-orange-100 flex items-center justify-center">
          <Flame className="w-7 h-7 text-orange-500" />
        </div>
        <div>
          <p className="text-2xl font-bold text-orange-700">{learner.streak_days || 0}-day streak</p>
          <p className="text-sm text-orange-800/80">
            {(learner.last_active_date || "") === new Date().toISOString().slice(0, 10)
              ? "You're on a roll. Come back tomorrow to keep it going."
              : "Learn today to keep your streak."}
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
          <h3 className="font-bold">Learner details</h3>
          <label className="block text-sm">
            Name
            <input className="mt-1 w-full p-3 border rounded-xl" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </label>
          <label className="block text-sm">
            Experience level
            <select className="mt-1 w-full p-3 border rounded-xl" value={form.experience_level} onChange={(e) => setForm({ ...form, experience_level: e.target.value })}>
              <option>Student</option>
              <option>Fresher</option>
              <option>Experienced</option>
            </select>
          </label>
          <label className="block text-sm">
            Learning preference
            <select className="mt-1 w-full p-3 border rounded-xl" value={form.learning_preference} onChange={(e) => setForm({ ...form, learning_preference: e.target.value })}>
              <option value="hands-on">Hands-on</option>
              <option value="visual">Visual</option>
              <option value="reading">Reading</option>
            </select>
          </label>
          <label className="block text-sm">
            Hours per week
            <input type="number" className="mt-1 w-full p-3 border rounded-xl" value={form.hours_per_week} onChange={(e) => setForm({ ...form, hours_per_week: e.target.value })} />
          </label>
          <label className="block text-sm">
            Hours per day
            <input type="number" className="mt-1 w-full p-3 border rounded-xl" value={form.hours_per_day} onChange={(e) => setForm({ ...form, hours_per_day: e.target.value })} />
          </label>
          <label className="block text-sm">
            Budget
            <select className="mt-1 w-full p-3 border rounded-xl" value={form.budget} onChange={(e) => setForm({ ...form, budget: e.target.value })}>
              <option value="free">Free preferred</option>
              <option value="any">Any</option>
            </select>
          </label>
          <label className="block text-sm">
            Goal
            <textarea className="mt-1 w-full p-3 border rounded-xl" value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })} />
          </label>
          <label className="block text-sm">
            Target role
            <input className="mt-1 w-full p-3 border rounded-xl" value={form.target_role} onChange={(e) => setForm({ ...form, target_role: e.target.value })} />
          </label>
        </div>

        <div className="space-y-6">
          <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
            <h3 className="font-bold">Interests, skills, gaps</h3>
            <label className="block text-sm">
              Interests (comma separated)
              <input className="mt-1 w-full p-3 border rounded-xl" value={form.interests} onChange={(e) => setForm({ ...form, interests: e.target.value })} />
            </label>
            <label className="block text-sm">
              Skills
              <input className="mt-1 w-full p-3 border rounded-xl" value={form.skills} onChange={(e) => setForm({ ...form, skills: e.target.value })} />
            </label>
            <label className="block text-sm">
              Skill gaps
              <input className="mt-1 w-full p-3 border rounded-xl" value={form.skill_gaps} onChange={(e) => setForm({ ...form, skill_gaps: e.target.value })} />
            </label>
            <button onClick={save} className="bg-primary text-primary-foreground px-4 py-2 rounded-xl text-sm">Save profile</button>
            <div className="pt-2 space-y-2">
              <p className="text-sm font-medium">Proficiency</p>
              {(learner.skills || []).map((s) => (
                <div key={s.skill_id || s.name} className="text-xs">
                  <div className="flex justify-between mb-1">
                    <span>{s.name}</span>
                    <span>{s.proficiency ?? 0}% / {s.required ?? 70}%</span>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-primary" style={{ width: `${s.proficiency ?? 0}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-card border border-border rounded-2xl p-6">
            <h3 className="font-bold mb-3">Completed courses</h3>
            <ul className="space-y-2 mb-4">
              {(learner.completed_courses || []).map((c) => (
                <li key={c.id} className="text-sm">
                  <span className="font-medium">{c.title}</span>
                  {c.skills.length > 0 && <span className="text-muted-foreground"> — {c.skills.join(", ")}</span>}
                </li>
              ))}
              {(learner.completed_courses || []).length === 0 && (
                <li className="text-sm text-muted-foreground">None yet.</li>
              )}
            </ul>
            <div className="space-y-2">
              <input className="w-full p-3 border rounded-xl" placeholder="Course title" value={courseTitle} onChange={(e) => setCourseTitle(e.target.value)} />
              <input className="w-full p-3 border rounded-xl" placeholder="Skills gained (comma separated)" value={courseSkills} onChange={(e) => setCourseSkills(e.target.value)} />
              <button onClick={addCourse} className="border px-4 py-2 rounded-xl text-sm flex items-center gap-1">
                <Plus className="w-4 h-4" /> Add completed course
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
