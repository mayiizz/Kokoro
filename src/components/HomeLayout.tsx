import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { LayoutDashboard, MessageSquare, Map, User, BookOpen, Target, LogOut, ClipboardCheck, Share2 } from "lucide-react";
import { useLearner } from "@/context/LearnerContext";
import SkillSwitcher from "@/components/SkillSwitcher";
import BrandMark from "@/components/BrandMark";
import KokoroBackdrop from "@/components/KokoroBackdrop";

const navItems = [
  { to: "/home", icon: LayoutDashboard, label: "Dashboard", end: true },
  { to: "/home/assistant", icon: MessageSquare, label: "Assistant" },
  { to: "/home/assessment", icon: ClipboardCheck, label: "Assessment" },
  { to: "/home/graph", icon: Share2, label: "Skill Graph" },
  { to: "/home/path", icon: Map, label: "Learning Path" },
  { to: "/home/profile", icon: User, label: "Profile" },
  { to: "/home/semester", icon: BookOpen, label: "Semester Mapping" },
  { to: "/home/role-fit", icon: Target, label: "Role Fit & Gap" },
];

const HomeLayout = () => {
  const navigate = useNavigate();
  const { learnerId, learner, loading, logout } = useLearner();

  useEffect(() => {
    if (!loading && !learnerId) navigate("/login");
  }, [loading, learnerId, navigate]);

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="w-[250px] bg-card border-r border-border flex flex-col fixed h-full z-10">
        <div className="p-5">
          <BrandMark size="md" />
        </div>

        <p className="px-5 pt-4 pb-2 text-[11px] font-semibold tracking-wider text-muted-foreground uppercase">Navigation</p>

        <nav className="flex-1 px-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? "bg-primary text-primary-foreground shadow-md"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`
              }
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 mt-auto">
          <button
            onClick={() => {
              logout();
              navigate("/");
            }}
            className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-all w-full"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
        </div>
      </aside>

      <div className="flex-1 ml-[250px] flex flex-col">
        <header className="h-16 border-b border-border bg-card flex items-center justify-end px-6 gap-4 sticky top-0 z-20">
          <SkillSwitcher />
          <div className="text-right">
            <p className="text-sm font-medium text-foreground">{learner?.name || "Learner"}</p>
            <p className="text-xs text-muted-foreground">{learner?.email}</p>
          </div>
          <button
            onClick={() => navigate("/home/profile")}
            className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center text-primary hover:bg-primary/20 transition-colors"
          >
            <User className="w-5 h-5" />
          </button>
        </header>

        <main className="relative flex-1 p-6 overflow-auto">
          <KokoroBackdrop className="opacity-[0.08]" />
          <div className="relative z-10">
            {loading ? (
              <p className="text-muted-foreground">Loading profile...</p>
            ) : (
              <Outlet />
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default HomeLayout;
