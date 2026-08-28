import { useNavigate } from "react-router-dom";
import { ArrowRight, Zap, MessageSquare, User, Map, LayoutDashboard, BookOpen, Target } from "lucide-react";
import BrandMark from "@/components/BrandMark";
import KokoroBackdrop from "@/components/KokoroBackdrop";

const features = [
  {
    icon: MessageSquare,
    title: "Conversational goals",
    desc: "Tell the assistant what you want to learn in plain language.",
  },
  {
    icon: User,
    title: "Learner profile",
    desc: "Interests, skill level, completed courses, and objectives stay saved.",
  },
  {
    icon: Map,
    title: "Personalized path",
    desc: "A sequenced roadmap of real courses, projects, and assessments.",
  },
  {
    icon: LayoutDashboard,
    title: "Live progress",
    desc: "Track skills, milestones, and the next recommended action.",
  },
];

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="relative min-h-screen bg-background">
      <KokoroBackdrop />
      <nav className="relative z-10 flex items-center justify-between px-8 py-4 border-b border-border bg-background/70 backdrop-blur-sm">
        <BrandMark size="md" />
        <div className="hidden md:flex items-center gap-8">
          <a href="#features" className="text-muted-foreground hover:text-foreground transition-colors">Features</a>
          <button onClick={() => navigate("/login")} className="text-primary font-medium hover:underline">Sign In</button>
          <button
            onClick={() => navigate("/login")}
            className="bg-primary text-primary-foreground px-5 py-2.5 rounded-lg font-medium hover:opacity-90 transition-opacity"
          >
            Get Started
          </button>
        </div>
      </nav>

      <section className="relative z-10 flex flex-col items-center text-center pt-20 pb-16 px-4">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-card mb-8">
          <Zap className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium text-muted-foreground">AI-Powered Personalized Learning Paths</span>
        </div>
        <h1 className="text-5xl md:text-7xl font-black text-foreground leading-tight max-w-4xl">
          Learn the <span className="text-primary">right sequence</span> for your goal
        </h1>
        <p className="mt-6 text-lg text-muted-foreground max-w-2xl">
          Kokoro profiles your skills, finds the gaps, and recommends a structured path of courses, projects, and assessments — then adapts as you progress.
        </p>
        <div className="flex gap-4 mt-10">
          <button
            onClick={() => navigate("/login")}
            className="bg-primary text-primary-foreground px-8 py-3.5 rounded-xl font-semibold flex items-center gap-2 hover:opacity-90 transition-opacity"
          >
            Get Started Free <ArrowRight className="w-5 h-5" />
          </button>
          <a
            href="#features"
            className="border border-border bg-card text-foreground px-8 py-3.5 rounded-xl font-semibold flex items-center gap-2 hover:bg-muted transition-colors"
          >
            Explore Features <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </section>

      <section id="features" className="relative z-10 py-20 px-4">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-foreground mb-4">
          Built around <span className="text-primary">your</span> learning path
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto mt-12">
          {features.map((f) => (
            <div key={f.title} className="bg-card border border-border rounded-2xl p-6 hover:shadow-lg transition-shadow">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                <f.icon className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-bold text-foreground text-lg mb-2">{f.title}</h3>
              <p className="text-muted-foreground text-sm">{f.desc}</p>
            </div>
          ))}
        </div>
        <div className="max-w-3xl mx-auto mt-12 grid sm:grid-cols-2 gap-4 text-sm text-muted-foreground">
          <div className="border border-border rounded-2xl p-5 flex gap-3">
            <BookOpen className="w-5 h-5 text-primary shrink-0" />
            Semester Mapping still feeds skills from your syllabus into the profile.
          </div>
          <div className="border border-border rounded-2xl p-5 flex gap-3">
            <Target className="w-5 h-5 text-primary shrink-0" />
            Role Fit still finds skill gaps that the path generator uses.
          </div>
        </div>
      </section>

      <section className="relative z-10 px-4 pb-20">
        <div className="max-w-4xl mx-auto bg-primary rounded-3xl p-12 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-primary-foreground mb-4">
            Ready to get a path that fits you?
          </h2>
          <p className="text-primary-foreground/80 mb-8 max-w-lg mx-auto">
            Describe a goal, import your skills, and follow a roadmap that updates with your feedback.
          </p>
          <button
            onClick={() => navigate("/login")}
            className="bg-card text-primary px-8 py-3.5 rounded-xl font-semibold inline-flex items-center gap-2 hover:opacity-90 transition-opacity"
          >
            Start Now — It's Free <ArrowRight className="w-5 h-5" />
          </button>
        </div>
      </section>

      <footer className="relative z-10 border-t border-border py-6 px-8 flex justify-between items-center">
        <BrandMark size="sm" />
        <p className="text-sm text-muted-foreground">© 2026 Kokoro. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default Landing;
