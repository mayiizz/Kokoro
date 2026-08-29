import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLearner } from "@/context/LearnerContext";
import { api, type Assessment, type QuizItem } from "@/lib/api";

const AssessmentPage = () => {
  const { learnerId, learner, setLearner } = useLearner();
  const navigate = useNavigate();
  const [quiz, setQuiz] = useState<Assessment | null>(null);
  const [current, setCurrent] = useState<QuizItem | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<
    { id: string; skill_id: string; skill_name?: string; goal: string; status: string; created_at?: string | null; answered: number; total: number }[]
  >([]);

  useEffect(() => {
    if (!learnerId) return;
    api.assessmentHistory(learnerId).then((res) => setHistory(res.assessments || [])).catch(() => setHistory([]));
  }, [learnerId, result]);

  const start = async () => {
    if (!learnerId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.generateAssessment(learnerId, learner?.active_skill_id);
      setQuiz(data);
      setCurrent(data.current_item || data.items[0] || null);
      setSelected("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not generate assessment");
    } finally {
      setLoading(false);
    }
  };

  const choose = (option: string) => setSelected(option);

  const next = async () => {
    if (!quiz || !current || !selected) return;
    setLoading(true);
    setError(null);
    try {
      let res = await api.answerAssessment(quiz.id, current.id, selected);
      if (res.done || res.status === "completed" || res.explanation) {
        if (res.learner) setLearner(res.learner);
        setResult(res.explanation || "Your skill profile was updated from this assessment.");
        setQuiz(res);
        setCurrent(null);
      } else {
        setQuiz(res);
        setCurrent(res.next_item || res.current_item || null);
        setSelected("");
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Could not score that answer";
      if (/429|rate.?limit/i.test(message)) {
        try {
          await new Promise((r) => setTimeout(r, 2000));
          const res = await api.answerAssessment(quiz.id, current.id, selected);
          if (res.done || res.status === "completed" || res.explanation) {
            if (res.learner) setLearner(res.learner);
            setResult(res.explanation || "Your skill profile was updated from this assessment.");
            setQuiz(res);
            setCurrent(null);
          } else {
            setQuiz(res);
            setCurrent(res.next_item || res.current_item || null);
            setSelected("");
          }
          return;
        } catch (retryErr: unknown) {
          setError(retryErr instanceof Error ? retryErr.message : message);
          return;
        }
      }
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const answered = quiz?.answered || 0;
  const total = quiz?.total || 10;
  const isLast = answered + 1 >= total;
  const topicLabel = current?.skill_name || current?.topic_id || current?.skill_id || "";

  return (
    <div>
      <h1 className="text-2xl font-bold">Skill assessment</h1>
      <p className="text-muted-foreground mb-6">
        Adaptive quiz on topics in your active skill. Difficulty shifts after each answer. Completing a course is not treated as mastery.
      </p>
      {history.length > 0 && !quiz && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
          {history.slice(0, 9).map((h) => {
            const title = h.skill_name || (h.goal && h.goal.length < 48 ? h.goal : "Skill assessment");
            const when = h.created_at ? new Date(h.created_at).toLocaleDateString() : "";
            return (
              <div key={h.id} className="border rounded-2xl p-4 bg-card">
                <p className="font-semibold truncate">{title}</p>
                <p className="text-xs text-muted-foreground mt-1 capitalize">
                  {h.status.replaceAll("_", " ")} · {h.answered}/{h.total} answered
                </p>
                {when && <p className="text-xs text-muted-foreground mt-1">{when}</p>}
              </div>
            );
          })}
        </div>
      )}
      {error && <div className="bg-red-50 text-red-700 p-4 rounded-xl mb-4">{error}</div>}
      {result && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5 mb-6">
          <p className="font-medium mb-3">{result}</p>
          <div className="flex gap-2">
            <button onClick={() => navigate("/home/path")} className="bg-primary text-primary-foreground px-4 py-2 rounded-xl text-sm">
              View adapted path
            </button>
            <button onClick={() => navigate("/home/graph")} className="border px-4 py-2 rounded-xl text-sm">
              Skill graph
            </button>
          </div>
        </div>
      )}
      {!quiz && !result && (
        <button onClick={start} disabled={loading} className="bg-primary text-primary-foreground px-5 py-3 rounded-xl disabled:opacity-50">
          {loading ? "Generating..." : "Start assessment"}
        </button>
      )}
      {quiz && current && !result && (
        <div className="bg-card border rounded-2xl p-6 max-w-2xl">
          <p className="text-xs text-muted-foreground mb-2">
            Question {answered + 1} of {total} · {topicLabel} · {current.difficulty}
          </p>
          <h2 className="text-lg font-semibold mb-4">{current.question}</h2>
          <div className="space-y-2">
            {current.options.map((opt) => (
              <button
                key={opt}
                onClick={() => choose(opt)}
                className={`w-full text-left p-3 rounded-xl border ${
                  selected === opt ? "border-primary bg-primary/5" : "border-border"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
          <div className="flex justify-end mt-6">
            <button
              onClick={next}
              disabled={loading || !selected}
              className="bg-primary text-primary-foreground px-4 py-2 rounded-xl text-sm disabled:opacity-50"
            >
              {loading ? "Scoring..." : isLast ? "Submit assessment" : "Next"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AssessmentPage;
