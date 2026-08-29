import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  CheckCircle,
  AlertTriangle,
  Target,
  BookOpen,
} from "lucide-react";
import { useLearner } from "@/context/LearnerContext";
import { api, API_BASE } from "@/lib/api";

const API_URL = `${API_BASE}/api/role-fit/analyze`;

/* ================= TYPES ================= */

type LearningPlanItem = {
  skill: string;
  topics: string[];
};

type RecommendedJob = {
  title: string;
  seniority?: string;
  match_percent?: number;
  why?: string;
  missing_skills?: string[];
};

type RoleFitResponse = {
  role_fit_percentage: number;
  strengths: string[];
  missing_skills: string[];
  in_progress_skills: string[];
  learning_plan: LearningPlanItem[];
  recommended_jobs?: RecommendedJob[];
};

/* ================= COMPONENT ================= */

const RoleFit = () => {
  const navigate = useNavigate();
  const { learnerId, learner, setLearner } = useLearner();
  const [targetRole, setTargetRole] = useState("");
  const [skills, setSkills] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [data, setData] = useState<RoleFitResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedToProfile, setSavedToProfile] = useState(false);
  const [registryGaps, setRegistryGaps] = useState<
    { skill_id: string; name: string; current: number; required: number; priority: string }[]
  >([]);

  /* ================= HANDLER ================= */

  const handleAnalyze = async () => {
    if (!targetRole.trim() && !jobDescription.trim()) {
      setError("Please enter a target role or paste a job description.");
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);
    setSavedToProfile(false);
    setRegistryGaps([]);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_role: targetRole || "from job description",
          current_skills: (skills || (learner?.skills || []).map((s) => s.name).join(", "))
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          job_description: jobDescription,
          resume_text: resumeText,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Role fit analysis failed");
      }

      const result: RoleFitResponse = await res.json();

      // 🛡️ Frontend safety (extra protection)
      setData({
        role_fit_percentage: result.role_fit_percentage ?? 0,
        strengths: result.strengths ?? [],
        missing_skills: result.missing_skills ?? [],
        in_progress_skills: result.in_progress_skills ?? [],
        learning_plan: result.learning_plan ?? [],
        recommended_jobs: result.recommended_jobs ?? [],
      });

      if (learnerId) {
        const updated = await api.fromRoleFit(learnerId, {
          target_role: targetRole,
          missing_skills: result.missing_skills ?? [],
          strengths: result.strengths ?? [],
          role_fit_percentage: result.role_fit_percentage,
        });
        setLearner(updated);
        setSavedToProfile(true);
        try {
          const mapped = await api.roleFitGaps(learnerId, targetRole, result.missing_skills ?? []);
          setRegistryGaps(mapped.gaps || []);
        } catch {
          setRegistryGaps([]);
        }
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  /* ================= UI ================= */

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Role Fit & Skill Gap</h1>
      <p className="text-muted-foreground mb-6">
        Understand how well you match a role and what to learn next
      </p>

      {/* INPUT */}
      <div className="bg-card p-6 rounded-2xl mb-6 border">
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium block mb-1">
              Target Role *
            </label>
            <input
              className="w-full p-3 border rounded-xl"
              placeholder="e.g. Data Analyst, ML Engineer"
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value)}
            />
          </div>

          <div>
            <label className="text-sm font-medium block mb-1">
              Current Skills (comma separated)
            </label>
            <input
              className="w-full p-3 border rounded-xl"
              placeholder={learner?.skills?.length ? learner.skills.map((s) => s.name).join(", ") : "SQL, Excel, Python"}
              value={skills}
              onChange={(e) => setSkills(e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium block mb-1">Job description (paste or upload .txt)</label>
            <textarea
              className="w-full p-3 border rounded-xl h-28"
              placeholder="Paste the JD here"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
            />
            <input
              type="file"
              accept=".txt,.md,.pdf"
              className="mt-2 text-sm"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const text = await file.text().catch(() => "");
                if (text) setJobDescription(text.slice(0, 12000));
              }}
            />
          </div>
          <div>
            <label className="text-sm font-medium block mb-1">Resume text (optional)</label>
            <textarea
              className="w-full p-3 border rounded-xl h-28"
              placeholder="Paste your resume to compare against the JD"
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
            />
          </div>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="mt-5 bg-primary text-primary-foreground px-6 py-3 rounded-xl flex items-center gap-2 disabled:opacity-50"
        >
          <Search size={16} />
          {loading ? "Analyzing..." : "Analyze Role Fit"}
        </button>
      </div>

      {/* ERROR */}
      {error && (
        <div className="bg-red-100 text-red-700 p-4 rounded-xl mb-6">
          {error}
        </div>
      )}

      {/* EMPTY */}
      {!data && !loading && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
            <Target className="w-8 h-8 text-primary" />
          </div>
          <p className="font-bold text-lg">No Analysis Yet</p>
          <p className="text-sm text-muted-foreground mt-1">
            Enter a role and your skills to see your fit.
          </p>
        </div>
      )}

      {/* RESULTS */}
      {data && !loading && (
        <div className="space-y-6">
          {savedToProfile && (
            <div className="bg-emerald-50 text-emerald-800 p-4 rounded-xl text-sm flex flex-wrap items-center justify-between gap-3">
              <span>Target role and skill gaps were saved to your profile.</span>
              <button
                onClick={() => navigate("/home/path")}
                className="bg-primary text-primary-foreground px-4 py-2 rounded-xl text-sm"
              >
                Generate learning path
              </button>
            </div>
          )}

          {/* SCORE */}
          <div className="bg-card p-6 rounded-2xl border">
            <h3 className="font-bold mb-2">Role Fit Score</h3>
            <p className="text-3xl font-bold text-primary mb-2">
              {data.role_fit_percentage}%
            </p>
            <div className="w-full h-3 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary"
                style={{ width: `${data.role_fit_percentage}%` }}
              />
            </div>
          </div>

          {/* STRENGTHS */}
          <div className="bg-card p-6 rounded-2xl border">
            <h3 className="font-bold mb-3">Strengths</h3>
            {(data.strengths ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No strong matches yet.
              </p>
            ) : (
              <ul className="space-y-2">
                {data.strengths.map((s) => (
                  <li key={s} className="flex items-center gap-2 text-sm">
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                    {s}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* MISSING SKILLS */}
          <div className="bg-card p-6 rounded-2xl border">
            <h3 className="font-bold mb-3">Missing Skills</h3>
            <div className="flex flex-wrap gap-2">
              {(data.missing_skills ?? []).map((s) => (
                <span
                  key={s}
                  className="bg-red-50 text-red-700 px-3 py-1 rounded-lg text-xs font-medium flex items-center gap-1"
                >
                  <AlertTriangle className="w-3 h-3" />
                  {s}
                </span>
              ))}
            </div>
          </div>

          {registryGaps.length > 0 && (
            <div className="bg-card p-6 rounded-2xl border">
              <h3 className="font-bold mb-3">Gaps vs your learner model</h3>
              <div className="space-y-3">
                {registryGaps.map((g) => (
                  <div key={g.skill_id} className="flex flex-wrap items-center justify-between gap-2 border rounded-xl p-3">
                    <div>
                      <p className="font-medium">{g.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {g.skill_id} · {g.current}% now · {g.required}% needed · {g.priority}
                      </p>
                    </div>
                    <button
                      onClick={async () => {
                        if (!learnerId) return;
                        await api.setActiveSkill(learnerId, g.skill_id).catch(() => api.resolveSkill(g.name, learnerId));
                        navigate("/home/path");
                      }}
                      className="text-sm bg-primary text-primary-foreground px-3 py-2 rounded-xl"
                    >
                      Generate path for this skill
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(data.recommended_jobs || []).length > 0 && (
            <div className="bg-card p-6 rounded-2xl border">
              <h3 className="font-bold mb-3">Recommended jobs</h3>
              <div className="space-y-3">
                {data.recommended_jobs!.map((j) => (
                  <div key={j.title} className="border rounded-xl p-4">
                    <div className="flex justify-between gap-2">
                      <p className="font-semibold">{j.title}</p>
                      <span className="text-sm text-primary">{j.match_percent ?? 0}% match</span>
                    </div>
                    <p className="text-xs text-muted-foreground capitalize mt-1">{j.seniority || "mid"}</p>
                    <p className="text-sm mt-2">{j.why}</p>
                    {(j.missing_skills || []).length > 0 && (
                      <p className="text-xs text-muted-foreground mt-2">Gaps: {(j.missing_skills || []).join(", ")}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* LEARNING PLAN */}
          <div className="bg-card p-6 rounded-2xl border">
            <h3 className="font-bold mb-4 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-primary" />
              What to Learn
            </h3>

            {(data.learning_plan ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No learning recommendations available.
              </p>
            ) : (
              <table className="w-full text-sm border rounded-lg overflow-hidden">
                <thead className="bg-muted">
                  <tr>
                    <th className="p-3 text-left">Skill</th>
                    <th className="p-3 text-left">Important Topics to Cover</th>
                  </tr>
                </thead>
                <tbody>
                  {data.learning_plan.map((lp) => (
                    <tr key={lp.skill} className="border-t">
                      <td className="p-3 font-semibold">
                        {lp.skill}
                      </td>
                      <td className="p-3">
                        {lp.topics.join(", ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default RoleFit;
