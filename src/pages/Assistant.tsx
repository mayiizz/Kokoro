import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Send, Sparkles, Plus } from "lucide-react";
import { useLearner } from "@/context/LearnerContext";
import { api, type ChatMessage, type ChatSession } from "@/lib/api";

const Assistant = () => {
  const { learnerId, learner, setLearner } = useLearner();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const skillFromUrl = searchParams.get("skill") || "";
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [actions, setActions] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skills, setSkills] = useState<{ id: string; name: string }[]>([]);
  const [threadSkill, setThreadSkill] = useState<string>(skillFromUrl);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const skillName = (id: string) => (id ? skills.find((s) => s.id === id)?.name || id : "General");

  const loadSessions = async (skillId: string, preferId?: string) => {
    if (!learnerId) return;
    const res = await api.chatSessions(learnerId, skillId || undefined);
    const list = res.sessions || [];
    setSessions(list);
    const nextId = preferId && list.some((s) => s.id === preferId) ? preferId : list[0]?.id || "";
    setActiveSessionId(nextId);
    if (!nextId) setMessages([]);
  };

  useEffect(() => {
    if (!learnerId) return;
    api.learnerSkills(learnerId).then((res) => {
      setSkills(res.skills || []);
      const nextSkill = skillFromUrl || res.active_skill_id || learner?.active_skill_id || "";
      setThreadSkill(nextSkill);
    }).catch(() => setSkills([]));
  }, [learnerId, learner?.active_skill_id, skillFromUrl]);

  useEffect(() => {
    if (!learnerId) return;
    loadSessions(threadSkill).catch((e) => setError(e.message));
  }, [learnerId, threadSkill]);

  useEffect(() => {
    if (!learnerId || !activeSessionId) return;
    api.chatHistory(learnerId, undefined, activeSessionId)
      .then((res) => setMessages(res.messages || []))
      .catch((e) => setError(e.message));
  }, [learnerId, activeSessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const switchSkill = async (skillId: string) => {
    setThreadSkill(skillId);
    setActiveSessionId("");
    setMessages([]);
    if (skillId) setSearchParams({ skill: skillId });
    else setSearchParams({});
    if (learnerId && skillId) {
      const res = await api.setActiveSkill(learnerId, skillId).catch(() => undefined);
      if (res?.learner) setLearner(res.learner);
    }
  };

  const newChat = async () => {
    if (!learnerId) return;
    const created = await api.createChatSession(learnerId, threadSkill);
    setSessions((prev) => [created, ...prev.filter((s) => s.id !== created.id)]);
    setActiveSessionId(created.id);
    setMessages([]);
    setActions([]);
  };

  const send = async () => {
    if (!learnerId || !input.trim() || loading) return;
    const text = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { id: `local-${Date.now()}`, role: "user", content: text }]);
    setLoading(true);
    setError(null);
    try {
      const res = await api.chat(learnerId, text, threadSkill, activeSessionId || undefined);
      setMessages(res.messages);
      if (res.learner) setLearner(res.learner);
      setActions(res.actions || []);
      if (res.session_id) setActiveSessionId(res.session_id);
      if (res.session) {
        setSessions((prev) => {
          const rest = prev.filter((s) => s.id !== res.session!.id);
          return [res.session!, ...rest];
        });
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  };

  const threadName = skillName(threadSkill);

  return (
    <div className="flex gap-4 h-[calc(100vh-8rem)] min-h-[480px]">
      <aside className="w-64 shrink-0 bg-card border rounded-2xl p-3 flex flex-col">
        <button
          onClick={newChat}
          className="flex items-center justify-center gap-2 bg-primary text-primary-foreground rounded-xl px-3 py-2 text-sm font-medium mb-3"
        >
          <Plus className="w-4 h-4" /> New chat
        </button>
        <div className="flex flex-wrap gap-1 mb-3">
          <button
            onClick={() => switchSkill("")}
            className={`text-[11px] px-2 py-1 rounded-full border ${!threadSkill ? "bg-primary text-primary-foreground border-primary" : "bg-background"}`}
          >
            All
          </button>
          {skills.map((s) => (
            <button
              key={s.id}
              onClick={() => switchSkill(s.id)}
              className={`text-[11px] px-2 py-1 rounded-full border ${
                threadSkill === s.id ? "bg-primary text-primary-foreground border-primary" : "bg-background"
              }`}
            >
              {s.name}
            </button>
          ))}
        </div>
        <p className="text-[11px] uppercase tracking-wide text-muted-foreground mb-2 px-1">Chats</p>
        <div className="flex-1 overflow-auto space-y-1">
          {sessions.length === 0 && (
            <p className="text-xs text-muted-foreground px-2">No chats yet for {threadName}.</p>
          )}
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => setActiveSessionId(s.id)}
              className={`w-full text-left rounded-xl px-3 py-2 ${
                s.id === activeSessionId ? "bg-primary/10 border border-primary" : "hover:bg-muted"
              }`}
            >
              <p className="text-sm font-medium truncate">{s.title || "New chat"}</p>
              <p className="text-[11px] text-muted-foreground truncate">
                {skillName(s.skill_id || "")}
                {s.preview ? ` · ${s.preview}` : ""}
              </p>
            </button>
          ))}
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <div className="mb-3">
          <h1 className="text-2xl font-bold">Learning assistant</h1>
          <p className="text-muted-foreground">
            {threadName === "General" ? "Ask anything, or start a chat for a skill." : `Chatting about ${threadName}. Start a new chat anytime — like ChatGPT.`}
          </p>
        </div>

        <div className="flex-1 overflow-auto bg-card border border-border rounded-2xl p-6 space-y-4 mb-4">
          {messages.length === 0 && !loading && (
            <div className="text-sm text-muted-foreground space-y-2">
              <p className="flex items-center gap-2 font-medium text-foreground">
                <Sparkles className="w-4 h-4 text-primary" /> Try asking
              </p>
              <p>“I want to become a data analyst in 4 months, 8 hours a week.”</p>
              <p>“What should I practice next in this skill?”</p>
              <p>“I prefer hands-on projects over long courses.”</p>
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                  m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {loading && <p className="text-sm text-muted-foreground">Thinking...</p>}
          <div ref={bottomRef} />
        </div>

        {actions.length > 0 && (
          <div className="flex gap-2 mb-3">
            {actions.includes("assessment") && (
              <button onClick={() => navigate("/home/assessment")} className="text-sm bg-primary text-primary-foreground px-3 py-2 rounded-xl">
                Take assessment
              </button>
            )}
            {actions.includes("path") && (
              <button onClick={() => navigate("/home/path")} className="text-sm border px-3 py-2 rounded-xl">
                Open learning path
              </button>
            )}
          </div>
        )}

        {error && <div className="bg-red-50 text-red-700 text-sm p-3 rounded-xl mb-3">{error}</div>}

        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
            placeholder={activeSessionId ? "Ask about this skill..." : "Start a new chat..."}
            className="flex-1 p-3 border border-border rounded-xl bg-background"
          />
          <button
            onClick={send}
            disabled={loading}
            className="bg-primary text-primary-foreground px-4 rounded-xl disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Assistant;
