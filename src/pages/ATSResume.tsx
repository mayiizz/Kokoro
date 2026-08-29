import { useState } from "react";
import { Search, FileText, Copy, CheckCircle, AlertTriangle, Download } from "lucide-react";

type ResumeResponse = {
  ats_optimized_resume_text: string;
  ats_match_percentage: number;
  missing_keywords: string[];
};

const ATSResume = () => {

  // ===== NEW FIELDS ADDED =====
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [linkedin, setLinkedin] = useState("");
  const [github, setGithub] = useState("");
  const [education, setEducation] = useState("");
  const [skills, setSkills] = useState("");

  // ===== EXISTING =====
  const [targetRole, setTargetRole] = useState("");
  const [academicDetails, setAcademicDetails] = useState("");
  const [projects, setProjects] = useState("");
  const [tools, setTools] = useState("");
  const [certifications, setCertifications] = useState("");

  const [result, setResult] = useState<ResumeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // remove "none"
  const clean = (arr: string[]) =>
    arr.map(v => v.trim()).filter(v => v && v.toLowerCase() !== "none");

  // payload builder
  const payload = () => ({
    name,
    email,
    phone,
    linkedin,
    github,
    target_role: targetRole,
    education,
    skills: clean(skills.split(",")),
    tools: clean(tools.split(",")),
    projects: clean(projects.split("\n")),
    achievements: clean(certifications.split("\n")),
    academic_details: academicDetails
  });

  // generate
  const handleGenerate = async () => {
    if (!targetRole.trim()) {
      alert("Please enter a target role");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const response = await fetch("http://localhost:8000/api/resume/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload())
      });

      if (!response.ok) throw new Error();

      const data = await response.json();
      setResult(data);

    } catch {
      alert("Backend error — check server");
    } finally {
      setLoading(false);
    }
  };

  // copy
  const handleCopy = () => {
    if (!result?.ats_optimized_resume_text) return;
    navigator.clipboard.writeText(result.ats_optimized_resume_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // download pdf
  const handleDownload = async () => {
    const res = await fetch("http://localhost:8000/api/resume/download-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload())
    });

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "resume.pdf";
    a.click();
  };

  return (
    <div>
      <h1 className="text-2xl font-bold">ATS Resume Generator</h1>
      <p className="text-muted-foreground mb-6">
        Generate a professional ATS-optimized resume from your academic profile
      </p>

      {/* INPUT CARD */}
      <div className="bg-card border rounded-2xl p-6 space-y-5 mb-6">

        {/* NEW FIELDS */}
        <input value={name} onChange={e => setName(e.target.value)} placeholder="Full Name" className="w-full p-3 border rounded-xl" />
        <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" className="w-full p-3 border rounded-xl" />
        <input value={phone} onChange={e => setPhone(e.target.value)} placeholder="Phone" className="w-full p-3 border rounded-xl" />
        <input value={linkedin} onChange={e => setLinkedin(e.target.value)} placeholder="LinkedIn URL" className="w-full p-3 border rounded-xl" />
        <input value={github} onChange={e => setGithub(e.target.value)} placeholder="GitHub URL" className="w-full p-3 border rounded-xl" />
        <textarea value={education} onChange={e => setEducation(e.target.value)} placeholder="Education details" className="w-full h-20 p-3 border rounded-xl" />
        <input value={skills} onChange={e => setSkills(e.target.value)} placeholder="Skills (comma separated)" className="w-full p-3 border rounded-xl" />

        {/* ORIGINAL FIELDS */}
        <input
          value={targetRole}
          onChange={(e) => setTargetRole(e.target.value)}
          placeholder="Target Role (e.g. Frontend Developer)"
          className="w-full p-3 border rounded-xl"
        />

        <textarea
          value={academicDetails}
          onChange={(e) => setAcademicDetails(e.target.value)}
          placeholder="Subjects studied (DBMS, OS, ML...)"
          className="w-full h-24 p-3 border rounded-xl"
        />

        <textarea
          value={projects}
          onChange={(e) => setProjects(e.target.value)}
          placeholder="Projects you built"
          className="w-full h-24 p-3 border rounded-xl"
        />

        <input
          value={tools}
          onChange={(e) => setTools(e.target.value)}
          placeholder="Tools (React, Python, SQL...)"
          className="w-full p-3 border rounded-xl"
        />

        <textarea
          value={certifications}
          onChange={(e) => setCertifications(e.target.value)}
          placeholder="Certifications (one per line)"
          className="w-full h-20 p-3 border rounded-xl"
        />

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="bg-primary text-white px-6 py-3 rounded-xl flex gap-2 items-center"
        >
          <Search size={16} />
          {loading ? "Generating..." : "Generate Resume"}
        </button>
      </div>

      {/* EMPTY */}
      {!result && !loading && (
        <div className="text-center py-20 opacity-60">
          <FileText size={40} className="mx-auto mb-4" />
          Enter your details and generate your resume
        </div>
      )}

      {/* RESULT */}
      {result && (
        <div className="space-y-6">

          {/* PREVIEW */}
          <div className="bg-card border rounded-2xl p-6">
            <div className="flex justify-between mb-4">
              <h3 className="font-bold">Resume Preview</h3>

              <div className="flex gap-2">
                <button onClick={handleDownload} className="border px-4 py-2 rounded-lg flex gap-2">
                  <Download size={16} /> PDF
                </button>

                <button onClick={handleCopy} className="border px-4 py-2 rounded-lg flex gap-2">
                  {copied ? <CheckCircle size={16} /> : <Copy size={16} />}
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>
            </div>

            <pre className="bg-muted p-5 rounded-xl whitespace-pre-wrap text-sm">
              {result.ats_optimized_resume_text}
            </pre>
          </div>

          {/* SCORE */}
          <div className="bg-card border rounded-2xl p-6">
            <p className="font-bold mb-2">ATS Match Score</p>
            <p className="text-3xl font-bold text-primary">
              {result.ats_match_percentage}%
            </p>
          </div>

          {/* KEYWORDS */}
          <div className="bg-card border rounded-2xl p-6">
            <p className="font-bold mb-3 flex items-center gap-2">
              <AlertTriangle size={16} /> Missing Keywords
            </p>

            <div className="flex flex-wrap gap-2">
              {result?.missing_keywords?.map((k) => (
                <span key={k} className="bg-amber-50 text-amber-700 px-3 py-1 rounded">
                  {k}
                </span>
              ))}
            </div>
          </div>

        </div>
      )}
    </div>
  );
};

export default ATSResume;
