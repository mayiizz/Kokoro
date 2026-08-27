import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom";
import { LearnerProvider } from "@/context/LearnerContext";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import HomeLayout from "./components/HomeLayout";
import Dashboard from "./pages/Dashboard";
import SemesterMapping from "./pages/SemesterMapping";
import ATSResume from "./pages/ATSResume";
import RoleFit from "./pages/RoleFit";
import LearningPath from "./pages/LearningPath";
import Profile from "./pages/Profile";
import Assistant from "./pages/Assistant";
import Assessment from "./pages/Assessment";
import SkillGraph from "./pages/SkillGraph";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <LearnerProvider>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/home" element={<HomeLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="assistant" element={<Assistant />} />
              <Route path="assessment" element={<Assessment />} />
              <Route path="graph" element={<SkillGraph />} />
              <Route path="path" element={<LearningPath />} />
              <Route path="roadmap" element={<Navigate to="/home/path" replace />} />
              <Route path="semester" element={<SemesterMapping />} />
              <Route path="resume" element={<ATSResume />} />
              <Route path="role-fit" element={<RoleFit />} />
              <Route path="profile" element={<Profile />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </LearnerProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
