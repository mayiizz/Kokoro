import { useState } from "react";
import { Search, CheckCircle, AlertTriangle } from "lucide-react";

const API_URL = "http://localhost:8000/api/roadmap/generate";

type WeeklyRoadmap = {
  week: number;
  focus: string;
  topics: string[];
  practice: string;
  estimated_hours: number;
};

type RoadmapResponse = {
  feasible: boolean;
  recommendation: string;
  roadmap: WeeklyRoadmap[];
};

const CareerRoadmap = () => {
  const [role, setRole] = useState("");
  const [experience, setExperience] = useState("Student");
  const [months, setMonths] = useState("");
  const [hours, setHours] = useState("");
  const [data, setData] = useState<RoadmapResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_role: role,
          experience_level: experience,
          months_available: months ? Number(months) : null,
          hours_per_day: hours ? Number(hours) : null
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to generate roadmap");
      }

      const result = await res.json();

      // 🛡️ Normalize response defensively
      setData({
        feasible: Boolean(result.feasible),
        recommendation: result.recommendation || "",
        roadmap: Array.isArray(result.roadmap) ? result.roadmap : []
      });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Career Roadmap</h1>

      {/* INPUT */}
      <div className="bg-card p-6 rounded-2xl mb-6 space-y-4">
        <input
          className="w-full p-3 border rounded-xl"
          placeholder="Target Role (e.g. Data Analyst)"
          onChange={e => setRole(e.target.value)}
        />

        <select
          className="w-full p-3 border rounded-xl"
          onChange={e => setExperience(e.target.value)}
        >
          <option>Student</option>
          <option>Fresher</option>
          <option>Experienced</option>
        </select>

        <input
          className="w-full p-3 border rounded-xl"
          placeholder="Months available (optional)"
          onChange={e => setMonths(e.target.value)}
        />

        <input
          className="w-full p-3 border rounded-xl"
          placeholder="Hours per day (optional)"
          onChange={e => setHours(e.target.value)}
        />

        <button
          onClick={generate}
          disabled={loading}
          className="bg-primary text-white px-6 py-3 rounded-xl flex gap-2 disabled:opacity-50"
        >
          <Search />
          {loading ? "Generating..." : "Generate Roadmap"}
        </button>
      </div>

      {/* ERROR */}
      {error && (
        <div className="bg-red-100 text-red-700 p-4 rounded-xl mb-6">
          {error}
        </div>
      )}

      {/* RESULTS */}
      {data && (
        <div className="space-y-6">

          {/* FEASIBILITY */}
          <div
            className={`p-4 rounded-xl flex items-start gap-2 ${data.feasible ? "bg-green-50" : "bg-amber-50"
              }`}
          >
            {data.feasible ? (
              <CheckCircle className="text-green-600 mt-0.5" />
            ) : (
              <AlertTriangle className="text-amber-600 mt-0.5" />
            )}
            <p>{data.recommendation}</p>
          </div>

          {/* WEEKLY ROADMAP */}
          {data.roadmap.length === 0 ? (
            <p className="text-muted-foreground">
              No roadmap generated.
            </p>
          ) : (
            data.roadmap.map((week) => (
              <div
                key={week.week}
                className="bg-card p-6 rounded-2xl"
              >
                <h3 className="font-bold text-lg mb-1">
                  Week {week.week}: {week.focus}
                </h3>

                <p className="text-sm font-semibold mb-2">
                  Topics
                </p>
                <ul className="list-disc ml-5 text-sm mb-3">
                  {(week.topics || []).map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>

                <p className="text-sm">
                  <strong>Practice:</strong> {week.practice}
                </p>

                <p className="text-xs text-muted-foreground mt-2">
                  ⏱ Estimated {week.estimated_hours} hours
                </p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default CareerRoadmap;
