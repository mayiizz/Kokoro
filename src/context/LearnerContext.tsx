import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type Learner } from "@/lib/api";

const STORAGE_KEY = "acadbridge_learner_id";

type LearnerContextValue = {
  learnerId: string | null;
  learner: Learner | null;
  loading: boolean;
  login: (email: string, name?: string) => Promise<Learner>;
  logout: () => void;
  refresh: () => Promise<void>;
  setLearner: (learner: Learner | null) => void;
};

const LearnerContext = createContext<LearnerContextValue | undefined>(undefined);

export function LearnerProvider({ children }: { children: ReactNode }) {
  const [learnerId, setLearnerId] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [learner, setLearner] = useState<Learner | null>(null);
  const [loading, setLoading] = useState(Boolean(localStorage.getItem(STORAGE_KEY)));

  const refresh = useCallback(async () => {
    if (!learnerId) {
      setLearner(null);
      return;
    }
    const data = await api.getLearner(learnerId);
    setLearner(data);
  }, [learnerId]);

  useEffect(() => {
    if (!learnerId) {
      setLoading(false);
      setLearner(null);
      return;
    }
    setLoading(true);
    refresh()
      .catch(() => {
        localStorage.removeItem(STORAGE_KEY);
        setLearnerId(null);
        setLearner(null);
      })
      .finally(() => setLoading(false));
  }, [learnerId, refresh]);

  const login = useCallback(async (email: string, name?: string) => {
    const data = await api.login(email, name);
    localStorage.setItem(STORAGE_KEY, data.id);
    setLearnerId(data.id);
    setLearner(data);
    return data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setLearnerId(null);
    setLearner(null);
  }, []);

  const value = useMemo(
    () => ({ learnerId, learner, loading, login, logout, refresh, setLearner }),
    [learnerId, learner, loading, login, logout, refresh]
  );

  return <LearnerContext.Provider value={value}>{children}</LearnerContext.Provider>;
}

export function useLearner() {
  const ctx = useContext(LearnerContext);
  if (!ctx) throw new Error("useLearner must be used within LearnerProvider");
  return ctx;
}
