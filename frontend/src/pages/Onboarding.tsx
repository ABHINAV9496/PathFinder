import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useTitle } from "../hooks/useTitle";
import type { ExperienceEntry } from "../types";

const KNOWN_PROFESSIONS = [
  "Administration / Operations",
  "Design / Creative",
  "Education",
  "Engineering (Non-Software)",
  "Finance / Accounting",
  "HR / People",
  "Healthcare",
  "Hospitality / Food Service",
  "IT / Software",
  "Legal",
  "Marketing / Sales",
  "Retail / Customer Service",
  "Science / Research",
  "Trades / Construction",
];

const CURRENCIES = ["USD", "INR", "EUR", "GBP"];

const STEPS = [
  "Personal info",
  "Profession & location",
  "Skills",
  "Experience",
  "Projects",
  "Resume",
  "Looking for",
];

interface Project {
  name: string;
  description: string;
  tech: string;
  link: string;
}

interface WizardProfile {
  name: string;
  email: string;
  phone: string;
  role: string;
  profession: string;
  location: string;
  country: string;
  currency: string;
  min_salary: number;
  timezone: string;
  experience_years: number;
  skills: Record<string, string[]>;
  experience: ExperienceEntry[];
  projects: Project[];
  looking_for: string[];
  languages: string[];
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="pf-field">
      <label className="pf-label">{label}</label>
      {hint && <span className="pf-hint">{hint}</span>}
      {children}
    </div>
  );
}

function StepNav({ step, onBack, onNext, nextLabel, canNext, saving }: {
  step: number;
  onBack: () => void;
  onNext: () => void;
  nextLabel?: string;
  canNext?: boolean;
  saving?: boolean;
}) {
  return (
    <div className="onb-nav">
      {step > 0 && (
        <button type="button" className="pf-btn-secondary" onClick={onBack} disabled={saving}>
          Back
        </button>
      )}
      <span className="onb-nav-spacer" />
      <button type="button" className="pf-btn-primary" onClick={onNext} disabled={canNext === false || saving}>
        {saving ? "Saving..." : (nextLabel || (step === STEPS.length - 1 ? "Finish" : "Continue"))}
      </button>
    </div>
  );
}

export default function Onboarding({ onComplete }: { onComplete?: () => void }) {
  useTitle("Welcome", "Set up your profile to start matching jobs.");
  const navigate = useNavigate();

  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const [profile, setProfile] = useState<WizardProfile>({
    name: "",
    email: "",
    phone: "",
    role: "",
    profession: "",
    location: "",
    country: "",
    currency: "USD",
    min_salary: 0,
    timezone: "",
    experience_years: 0,
    skills: {},
    experience: [],
    projects: [],
    looking_for: [],
    languages: [],
  });

  const [professionCustom, setProfessionCustom] = useState(false);
  const [customProfession, setCustomProfession] = useState("");
  const [newCatName, setNewCatName] = useState("");

  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.profile.get().then((d: any) => {
      const p = d.profile || d;
      setProfile((prev) => ({
        ...prev,
        name: p.name || "",
        email: p.email || "",
        phone: p.phone || "",
        role: p.role || "",
        profession: p.profession || "",
        location: p.location || "",
        country: p.country || "",
        currency: p.currency || "USD",
        min_salary: typeof p.min_salary === "number" ? p.min_salary : 0,
        timezone: p.timezone || "",
        experience_years: typeof p.experience_years === "number" ? p.experience_years : 0,
        skills: p.skills || {},
        experience: p.experience || [],
        projects: p.projects || [],
        looking_for: p.looking_for || [],
        languages: p.languages || [],
      }));
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const set = <K extends keyof WizardProfile>(field: K, value: WizardProfile[K]) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
  };

  const setSkill = (category: string, raw: string) => {
    setProfile((prev) => ({
      ...prev,
      skills: {
        ...prev.skills,
        [category]: raw.split(",").map((s) => s.trim()).filter(Boolean),
      },
    }));
  };

  const addSkillCategory = () => {
    const name = newCatName.trim().toLowerCase().replace(/\s+/g, "_");
    if (!name || profile.skills[name]) {
      setNewCatName("");
      return;
    }
    setProfile((prev) => ({ ...prev, skills: { ...prev.skills, [name]: [] } }));
    setNewCatName("");
  };

  const removeSkillCategory = (category: string) => {
    const skills = { ...profile.skills };
    delete skills[category];
    set("skills", skills);
  };

  const updateExp = (i: number, field: keyof ExperienceEntry, value: string | string[] | number) => {
    const experience = [...profile.experience];
    experience[i] = { ...experience[i], [field]: value };
    set("experience", experience);
  };

  const addExp = () => {
    set("experience", [...profile.experience, {
      id: Date.now(),
      role: "",
      company: "",
      location: "",
      duration: "",
      type: "full-time",
      highlights: [],
      tech: [],
    }]);
  };

  const removeExp = (i: number) => {
    set("experience", profile.experience.filter((_, idx) => idx !== i));
  };

  const updateProject = (i: number, field: keyof Project, value: string) => {
    const projects = [...profile.projects];
    projects[i] = { ...projects[i], [field]: value };
    set("projects", projects);
  };

  const addProject = () => {
    set("projects", [...profile.projects, { name: "", description: "", tech: "", link: "" }]);
  };

  const removeProject = (i: number) => {
    set("projects", profile.projects.filter((_, idx) => idx !== i));
  };

  const handleProfessionChange = (value: string) => {
    if (value === "__other__") {
      setProfessionCustom(true);
      set("profession", customProfession);
    } else {
      setProfessionCustom(false);
      set("profession", value);
    }
  };

  const handleSave = async () => {
    setError("");
    if (!profile.name.trim()) { setError("Please enter your name."); setStep(0); return; }
    if (!profile.email.trim()) { setError("Please enter your email."); setStep(0); return; }
    if (!profile.role.trim()) { setError("Please enter your role / job title."); setStep(0); return; }
    if (!profile.location.trim()) { setError("Please enter your location."); setStep(1); return; }

    const finalProfession = professionCustom ? customProfession : profile.profession;

    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        ...profile,
        profession: finalProfession,
        experience_years: Math.max(0, profile.experience_years || 0),
        min_salary: Math.max(0, profile.min_salary || 0),
        projects: profile.projects
          .filter((p) => p.name.trim())
          .map((p) => ({ name: p.name, description: p.description, tech: p.tech, link: p.link })),
      };
      await api.profile.update(payload);
      if (resumeFile) {
        await api.profile.uploadResume(resumeFile);
      }
      if (onComplete) {
        onComplete();
      } else {
        navigate("/profile", { replace: true });
      }
    } catch (e: any) {
      setError(e.message || "Failed to save profile. Please try again.");
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="onb-shell">
        <div className="onb-card">
          <div className="pf-skeleton pf-skeleton-line" style={{ width: "50%", margin: "24px auto" }} />
        </div>
      </div>
    );
  }

  return (
    <div className="onb-shell">
      <div className="onb-card">
        <header className="onb-header">
          <div className="onb-logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
              <path d="M2 12h20" />
            </svg>
            <span>JobbLoot</span>
          </div>
          <h1>Let&apos;s set up your profile</h1>
          <p>Answer a few quick questions — the job matcher, cover letters, and CV engine all use this. Any profession, any country.</p>
        </header>

        <div className="onb-progress">
          {STEPS.map((label, i) => (
            <div key={label} className={"onb-step" + (i === step ? " active" : i < step ? " done" : "")}>
              <span className="onb-step-dot">{i < step ? "✓" : i + 1}</span>
              <span className="onb-step-label">{label}</span>
            </div>
          ))}
        </div>

        <div className="onb-body">
          {step === 0 && (
            <>
              <h2 className="onb-title">Personal info</h2>
              <div className="pf-grid pf-grid-2">
                <Field label="Full name">
                  <input className="pf-input" type="text" value={profile.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Maya Nurse" autoFocus />
                </Field>
                <Field label="Email">
                  <input className="pf-input" type="email" value={profile.email} onChange={(e) => set("email", e.target.value)} placeholder="you@example.com" />
                </Field>
                <Field label="Phone">
                  <input className="pf-input" type="tel" value={profile.phone} onChange={(e) => set("phone", e.target.value)} placeholder="Optional" />
                </Field>
                <Field label="Role / Job title">
                  <input className="pf-input" type="text" value={profile.role} onChange={(e) => set("role", e.target.value)} placeholder="e.g. Registered Nurse" />
                </Field>
                <Field label="Years of experience" hint="0 if you are just starting out">
                  <input className="pf-input" type="number" min={0} value={profile.experience_years} onChange={(e) => set("experience_years", parseInt(e.target.value) || 0)} />
                </Field>
              </div>
            </>
          )}

          {step === 1 && (
            <>
              <h2 className="onb-title">Profession & location</h2>
              <div className="pf-grid pf-grid-2">
                <Field label="Profession">
                  <select className="pf-input pf-select" value={profile.profession} onChange={(e) => handleProfessionChange(e.target.value)}>
                    <option value="">Select or type your own…</option>
                    {KNOWN_PROFESSIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                    <option value="__other__">Other…</option>
                  </select>
                </Field>
                {professionCustom && (
                  <Field label="Your profession">
                    <input className="pf-input" type="text" value={customProfession} onChange={(e) => setCustomProfession(e.target.value)} placeholder="e.g. Professional Gardener" />
                  </Field>
                )}
                <Field label="Location">
                  <input className="pf-input" type="text" value={profile.location} onChange={(e) => set("location", e.target.value)} placeholder="e.g. Kochi, Kerala" />
                </Field>
                <Field label="Country">
                  <input className="pf-input" type="text" value={profile.country} onChange={(e) => set("country", e.target.value)} placeholder="e.g. India" />
                </Field>
                <Field label="Currency" hint="Job salaries are compared in this currency">
                  <select className="pf-input pf-select" value={profile.currency} onChange={(e) => set("currency", e.target.value)}>
                    {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </Field>
                <Field label="Minimum monthly salary" hint="Jobs below this are filtered out (0 = no minimum)">
                  <input className="pf-input" type="number" min={0} value={profile.min_salary} onChange={(e) => set("min_salary", parseInt(e.target.value) || 0)} />
                </Field>
                <Field label="Timezone" hint="e.g. Asia/Kolkata">
                  <input className="pf-input" type="text" value={profile.timezone} onChange={(e) => set("timezone", e.target.value)} placeholder="Asia/Kolkata" />
                </Field>
              </div>
            </>
          )}

          {step === 2 && (
            <>
              <h2 className="onb-title">Skills</h2>
              <p className="onb-sub">Group your skills into categories, e.g. <code>patient_care</code>: wound care, medication administration.</p>
              <div className="pf-grid pf-grid-2">
                {Object.entries(profile.skills).map(([category, skillList]) => (
                  <div key={category} className="pf-skill-cat">
                    <div className="pf-skill-cat-head">
                      <span className="pf-skill-cat-label">{category.replace(/_/g, " ")}</span>
                      <button type="button" className="pf-skill-cat-remove" onClick={() => removeSkillCategory(category)} title="Remove category">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="18" y1="6" x2="6" y2="18" />
                          <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                      </button>
                    </div>
                    <input className="pf-input" type="text" value={(skillList || []).join(", ")} onChange={(e) => setSkill(category, e.target.value)} placeholder="Comma-separated skills" />
                  </div>
                ))}
              </div>
              <div className="pf-skill-add">
                <input className="pf-input" type="text" value={newCatName} onChange={(e) => setNewCatName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addSkillCategory(); } }} placeholder="New category, e.g. patient_care" />
                <button type="button" className="pf-btn-add" onClick={addSkillCategory}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                  Add category
                </button>
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <h2 className="onb-title">Experience</h2>
              <p className="onb-sub">Optional — work history used for tailored resumes.</p>
              {profile.experience.length === 0 && (
                <div className="pf-empty-projects"><p>No work experience yet. Add your roles to get richer resumes.</p></div>
              )}
              {profile.experience.map((exp, i) => (
                <div key={exp.id ?? i} className="pf-project-card">
                  <div className="pf-project-header">
                    <span className="pf-project-num">Experience {i + 1}</span>
                    <button type="button" className="pf-project-remove" onClick={() => removeExp(i)} title="Remove entry">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </div>
                  <div className="pf-grid pf-grid-2">
                    <Field label="Role / Title">
                      <input className="pf-input" type="text" value={exp.role} onChange={(e) => updateExp(i, "role", e.target.value)} placeholder="e.g. Staff Nurse" />
                    </Field>
                    <Field label="Company">
                      <input className="pf-input" type="text" value={exp.company} onChange={(e) => updateExp(i, "company", e.target.value)} placeholder="e.g. City General Hospital" />
                    </Field>
                    <Field label="Duration">
                      <input className="pf-input" type="text" value={exp.duration} onChange={(e) => updateExp(i, "duration", e.target.value)} placeholder="e.g. Jan 2023 - Present" />
                    </Field>
                    <Field label="Type">
                      <select className="pf-input pf-select" value={exp.type} onChange={(e) => updateExp(i, "type", e.target.value)}>
                        <option value="full-time">Full-time</option>
                        <option value="part-time">Part-time</option>
                        <option value="internship">Internship</option>
                        <option value="freelance">Freelance</option>
                        <option value="contract">Contract</option>
                      </select>
                    </Field>
                    <Field label="Tools / techniques used" hint="Comma-separated">
                      <input className="pf-input" type="text" value={(exp.tech || []).join(", ")} onChange={(e) => updateExp(i, "tech", e.target.value.split(",").map(s => s.trim()).filter(Boolean))} placeholder="e.g. electronic health records, triage systems" />
                    </Field>
                  </div>
                  <Field label="Highlights" hint="One per line — key achievements">
                    <textarea className="pf-input pf-textarea" rows={3} value={(exp.highlights || []).join("\n")} onChange={(e) => updateExp(i, "highlights", e.target.value.split("\n").map(s => s.trim()).filter(Boolean).slice(0, 5))} placeholder={"Reduced wait times by 20%\nLed a team of 5"} />
                  </Field>
                </div>
              ))}
              <button type="button" className="pf-btn-add" onClick={addExp}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                Add experience
              </button>
            </>
          )}

          {step === 4 && (
            <>
              <h2 className="onb-title">Projects</h2>
              <p className="onb-sub">Optional — mentioned as evidence in cover letters.</p>
              {profile.projects.map((proj, i) => (
                <div key={i} className="pf-project-card">
                  <div className="pf-project-header">
                    <span className="pf-project-num">Project {i + 1}</span>
                    <button type="button" className="pf-project-remove" onClick={() => removeProject(i)} title="Remove project">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </div>
                  <div className="pf-grid pf-grid-2">
                    <Field label="Name">
                      <input className="pf-input" type="text" value={proj.name} onChange={(e) => updateProject(i, "name", e.target.value)} placeholder="e.g. Ward Handover Process" />
                    </Field>
                    <Field label="Tools / methods used">
                      <input className="pf-input" type="text" value={proj.tech} onChange={(e) => updateProject(i, "tech", e.target.value)} placeholder="Comma-separated" />
                    </Field>
                  </div>
                  <Field label="Description">
                    <textarea className="pf-input pf-textarea" rows={2} value={proj.description} onChange={(e) => updateProject(i, "description", e.target.value)} placeholder="What you did and the result, e.g. Cut triage wait times by 20%..." />
                  </Field>
                </div>
              ))}
              <button type="button" className="pf-btn-add" onClick={addProject}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                Add project
              </button>
            </>
          )}

          {step === 5 && (
            <>
              <h2 className="onb-title">Resume</h2>
              <p className="onb-sub">Optional — used when sending applications. Upload a PDF (max 5 MB).</p>
              <div className="pf-resume">
                {resumeFile ? (
                  <div className="pf-resume-info">
                    <div className="pf-resume-file">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      <div>
                        <span className="pf-resume-name">{resumeFile.name}</span>
                        <span className="pf-resume-size">{Math.round(resumeFile.size / 1024)} KB</span>
                      </div>
                    </div>
                    <div className="pf-resume-actions">
                      <button type="button" className="pf-btn-secondary" onClick={() => setResumeFile(null)}>Remove</button>
                    </div>
                  </div>
                ) : (
                  <div
                    className="pf-resume-drop"
                    onClick={() => fileInputRef.current?.click()}
                    onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add("pf-drop-active"); }}
                    onDragLeave={(e) => e.currentTarget.classList.remove("pf-drop-active")}
                    onDrop={(e) => {
                      e.preventDefault();
                      e.currentTarget.classList.remove("pf-drop-active");
                      const file = e.dataTransfer.files[0];
                      if (file && file.name.endsWith(".pdf")) setResumeFile(file);
                    }}
                  >
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    <span>Drop a PDF here or click to browse</span>
                    <span className="pf-hint">You can also skip this and upload later from the Profile page.</span>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) setResumeFile(file);
                    e.target.value = "";
                  }}
                />
              </div>
            </>
          )}

          {step === 6 && (
            <>
              <h2 className="onb-title">Looking for</h2>
              <div className="pf-grid pf-grid-2">
                <Field label="Roles you are looking for" hint="Comma-separated">
                  <input className="pf-input" type="text" value={profile.looking_for.join(", ")} onChange={(e) => set("looking_for", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} placeholder="e.g. staff nurse, charge nurse" />
                </Field>
                <Field label="Languages you speak" hint="Comma-separated">
                  <input className="pf-input" type="text" value={profile.languages.join(", ")} onChange={(e) => set("languages", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} placeholder="e.g. English, Malayalam" />
                </Field>
              </div>
              <div className="onb-summary">
                <h3>Almost done</h3>
                <ul>
                  <li><strong>Profile:</strong> {profile.name || "—"} · {profile.role || "—"}{profile.profession ? ` · ${profile.profession}` : ""}</li>
                  <li><strong>Location:</strong> {[profile.location, profile.country].filter(Boolean).join(", ") || "—"}</li>
                  <li><strong>Salary:</strong> {profile.currency}{profile.min_salary > 0 ? ` ${profile.min_salary.toLocaleString()} / month minimum` : " — no minimum"}</li>
                  <li><strong>Skill categories:</strong> {Object.keys(profile.skills).length > 0 ? Object.keys(profile.skills).join(", ") : "none yet (you can add these anytime)"}</li>
                </ul>
              </div>
            </>
          )}
        </div>

        {error && <div className="pf-toast error">{error}</div>}

        <StepNav
          step={step}
          onBack={() => setStep((s) => Math.max(0, s - 1))}
          onNext={() => step === STEPS.length - 1 ? handleSave() : setStep((s) => Math.min(STEPS.length - 1, s + 1))}
          saving={saving}
          nextLabel={step === STEPS.length - 1 ? "Save & start using JobbLoot" : undefined}
        />
      </div>
    </div>
  );
}
