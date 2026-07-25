import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import Markdown from "react-markdown";
import { api } from "../api/client";
import { useTitle } from "../hooks/useTitle";
import type { JobDetail as JobDetailType } from "../types";

function ScoreBadge({ score, size = "md" }: { score: number; size?: "sm" | "md" }) {
  const cls = score >= 50 ? "high" : score >= 30 ? "med" : "low";
  return <span className={"jd-score jd-score-" + cls + (size === "sm" ? " sm" : "")}>{score}%</span>;
}

function StatusChip({ status }: { status: string }) {
  return <span className={"jd-chip jd-chip-" + status}>{status.replace("_", " ")}</span>;
}

function TabButton({ active, onClick, children, count }: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  count?: number;
  countVariant?: "default" | "warn";
}) {
  return (
    <button className={"jd-tab" + (active ? " active" : "")} onClick={onClick}>
      {children}
      {count != null && count > 0 && (
        <span className="jd-tab-count">{count}</span>
      )}
    </button>
  );
}

function InfoRow({ label, children, accent }: { label: string; children: React.ReactNode; accent?: boolean }) {
  return (
    <div className="jd-info-row">
      <span className="jd-info-label">{label}</span>
      <span className={"jd-info-value" + (accent ? " accent" : "")}>{children}</span>
    </div>
  );
}

export default function JobDetail() {
  const { id } = useParams();
  const [job, setJob] = useState<JobDetailType | null>(null);
  useTitle(job?.title ?? "Job Details", job ? `${job.company} — ${job.location}` : undefined);
  const [loading, setLoading] = useState(true);
  const [showDesc, setShowDesc] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<"matched" | "gaps" | "analysis">("matched");
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  useEffect(() => {
    if (!id) return;
    api.jobs.detail(Number(id)).then((d) => {
      setJob(d);
      setLoading(false);
    });
  }, [id]);

  function copyCoverLetter() {
    if (!job?.application?.cover_letter_text) return;
    navigator.clipboard.writeText(job.application.cover_letter_text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  async function handleGenerateCoverLetter() {
    if (!job) return;
    setGenerating(true);
    setGenerateError(null);
    try {
      const res = await api.jobs.generateCoverLetter(job.id);
      setJob((prev) => prev ? {
        ...prev,
        application: prev.application
          ? { ...prev.application, cover_letter_text: res.cover_letter }
          : { id: 0, job: prev, sent_at: "", status: "draft", email_subject: "", cover_letter_text: res.cover_letter, error_message: "", skills_highlighted: [], skills_in_job_desc: [], skill_match_pct: 0, criteria_data: {}, skill_gaps: [], match_explanation: "" },
      } : prev);
    } catch (e: any) {
      setGenerateError(e.message || "Failed to generate cover letter");
    }
    setGenerating(false);
  }

  const canApply = job && job.apply_email && (!job.application || job.application.status === "failed");

  async function handleApply() {
    if (!job) return;
    setApplying(true);
    setApplyResult(null);
    try {
      const res = await api.jobs.apply(job.id) as any;
      if (res.success) {
        setApplyResult({ type: "success", msg: res.message || "Application sent!" });
        setJob((prev) => prev ? {
          ...prev,
          status: "applied",
          application: prev.application
            ? { ...prev.application, status: "sent" }
            : { id: 0, job: prev, sent_at: new Date().toISOString(), status: "sent", email_subject: "", cover_letter_text: "", error_message: "", skills_highlighted: [], skills_in_job_desc: [], skill_match_pct: 0, criteria_data: {}, skill_gaps: [], match_explanation: "" },
        } : prev);
      } else {
        setApplyResult({ type: "error", msg: res.message || "Failed to send application." });
        if (job.status !== "failed") {
          setJob((prev) => prev ? { ...prev, status: "failed" } : prev);
        }
      }
    } catch (e: any) {
      setApplyResult({ type: "error", msg: e.message || "Failed to apply." });
    }
    setApplying(false);
  }

  if (loading) {
    return (
      <>
        <div className="page-header">
          <div>
            <Link to="/jobs" className="jd-back">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="15 18 9 12 15 6" />
              </svg>
              Jobs
            </Link>
            <div className="jd-skeleton-title" />
            <div className="jd-skeleton-meta" />
          </div>
        </div>
        <div className="jd-loading-grid">
          <div className="jd-card skeleton"><div className="jd-skeleton-block" /></div>
          <div className="jd-card skeleton"><div className="jd-skeleton-block" /></div>
        </div>
      </>
    );
  }

  if (!job) {
    return (
      <>
        <div className="page-header">
          <Link to="/jobs" className="jd-back">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Jobs
          </Link>
        </div>
        <div className="jd-empty">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <h3>Job not found</h3>
          <p>This job may have been removed or the link is invalid.</p>
        </div>
      </>
    );
  }

  const app = job.application;
  const maxWeight = job.skill_score_breakdown
    ? Math.max(...Object.values(job.skill_score_breakdown), 1)
    : 1;

  const descPreview = job.description?.slice(0, 400) || "";
  const descTruncated = (job.description?.length || 0) > 400;

  function getDescText(): string {
    if (showDesc || !descTruncated) return job.description || "";
    let text = descPreview;
    const lastNewline = text.lastIndexOf("\n");
    if (lastNewline > 200) text = text.slice(0, lastNewline);
    if (text.endsWith("**") || text.endsWith("*")) {
      const prevNewline = text.lastIndexOf("\n", text.length - 2);
      if (prevNewline > 200) text = text.slice(0, prevNewline);
    }
    return text + "\n\n…";
  }

  return (
    <>
      {/* Header */}
      <div className="page-header">
        <div>
          <Link to="/jobs" className="jd-back">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Jobs
          </Link>
          <h2 className="jd-title">{job.title}</h2>
          <div className="jd-meta">
            <ScoreBadge score={job.match_score} />
            <span className="jd-meta-text">{job.company}</span>
            <span className="jd-dot">·</span>
            <span className="jd-meta-text">{job.location}</span>
            <span className="jd-dot">·</span>
            <span className="jd-meta-text">{job.source}</span>
            {job.salary_display && (
              <>
                <span className="jd-dot">·</span>
                <span className="jd-meta-salary">{job.salary_display}</span>
              </>
            )}
            <span className="jd-dot">·</span>
            <StatusChip status={job.status} />
          </div>
        </div>
        <div className="jd-actions-top">
          {canApply && (
            <button
              className={"jd-btn jd-btn-apply" + (applying ? " loading" : "")}
              onClick={handleApply}
              disabled={applying}
            >
              {applying ? (
                <>
                  <span className="spinner" /> Applying...
                </>
              ) : (
                <>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                  Auto Apply
                </>
              )}
            </button>
          )}
          {job.application && job.application.status === "sent" && (
            <span className="jd-btn jd-btn-applied">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Applied
            </span>
          )}
          {job.apply_url && (
            <a href={job.apply_url} target="_blank" rel="noopener noreferrer" className="jd-btn jd-btn-primary">
              Apply Now
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7 17L17 7M17 7H7M17 7v10" />
              </svg>
            </a>
          )}
          {job.job_url && (
            <a href={job.job_url} target="_blank" rel="noopener noreferrer" className="jd-btn jd-btn-secondary">
              Original
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
            </a>
          )}
        </div>
      </div>

      {job.filter_reason && (
        <div className="jd-alert jd-alert-warn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01" />
          </svg>
          Filtered: {job.filter_reason}
        </div>
      )}

      {applyResult && (
        <div className={"jd-alert " + (applyResult.type === "success" ? "jd-alert-success" : "jd-alert-error")}>
          {applyResult.type === "success" ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          )}
          {applyResult.msg}
        </div>
      )}

      {/* Two-column layout */}
      <div className="jd-grid">
        {/* Left: Job Details */}
        <div className="jd-card">
          <div className="jd-card-header">
            <h3 className="jd-card-title">Details</h3>
          </div>
          <div className="jd-info">
            <InfoRow label="Posted">{job.posted_date || "N/A"}</InfoRow>
            <InfoRow label="Fetched">
              {job.fetched_date ? new Date(job.fetched_date).toLocaleDateString("en-IN", { month: "short", day: "numeric", year: "numeric" }) : "N/A"}
            </InfoRow>
            {job.salary_display && (
              <InfoRow label="Salary" accent>
                {job.salary_display}
                {job.salary && <span className="jd-salary-raw">₹{job.salary.toLocaleString("en-IN")}/yr</span>}
              </InfoRow>
            )}
            {job.search_query && (
              <InfoRow label="Query">
                <span className="jd-query">{job.search_query}</span>
              </InfoRow>
            )}
            {job.apply_email && (
              <InfoRow label="Email">{job.apply_email}</InfoRow>
            )}
            {job.apply_url && (
              <InfoRow label="Apply URL">
                <a href={job.apply_url} target="_blank" rel="noopener noreferrer" className="jd-link">
                  {job.apply_url.length > 50 ? job.apply_url.slice(0, 50) + "…" : job.apply_url}
                </a>
              </InfoRow>
            )}
          </div>

          {/* Description */}
          {job.description && (
            <div className="jd-desc-section">
              <div className="jd-card-header">
                <h3 className="jd-card-title">Description</h3>
              </div>
              <div className="jd-desc">
                <Markdown>{getDescText()}</Markdown>
              </div>
              {descTruncated && (
                <button className="jd-desc-toggle" onClick={() => setShowDesc(!showDesc)}>
                  {showDesc ? "Show less" : "Show full description"}
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: showDesc ? "rotate(180deg)" : "none" }}>
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Right: Skills / Gaps / Analysis */}
        <div className="jd-card">
          <div className="jd-tabs">
            <TabButton active={activeTab === "matched"} onClick={() => setActiveTab("matched")} count={job.matched_skills?.length}>
              Matched
            </TabButton>
            <TabButton active={activeTab === "gaps"} onClick={() => setActiveTab("gaps")} count={job.skill_gaps?.length}>
              Gaps
            </TabButton>
            <TabButton active={activeTab === "analysis"} onClick={() => setActiveTab("analysis")}>
              Analysis
            </TabButton>
          </div>

          <div className="jd-tab-content">
            {/* Matched Skills */}
            {activeTab === "matched" && (
              <>
                {job.matched_skills?.length > 0 ? (
                  <div className="jd-skills">
                    {job.matched_skills.map((skill) => {
                      const weight = job.skill_score_breakdown?.[skill] ?? 0;
                      const pct = maxWeight > 0 ? (weight / maxWeight) * 100 : 0;
                      return (
                        <div key={skill} className="jd-skill-row">
                          <div className="jd-skill-info">
                            <span className="jd-skill-name">{skill}</span>
                            {weight > 0 && <span className="jd-skill-pts">+{weight}</span>}
                          </div>
                          <div className="jd-skill-bar">
                            <div className="jd-skill-bar-fill" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="jd-tab-empty">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="11" cy="11" r="8" />
                      <path d="m21 21-4.35-4.35" />
                    </svg>
                    <p>No skills matched.</p>
                  </div>
                )}
              </>
            )}

            {/* Skill Gaps */}
            {activeTab === "gaps" && (
              <>
                {job.skill_gaps?.length > 0 ? (
                  <div className="jd-gaps">
                    {job.skill_gaps.map((gap, i) => (
                      <div key={gap} className="jd-gap">
                        <span className="jd-gap-num">{i + 1}</span>
                        <span className="jd-gap-name">{gap}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="jd-tab-empty jd-tab-empty-good">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                      <polyline points="22 4 12 14.01 9 11.01" />
                    </svg>
                    <p>No skill gaps — you match all required skills.</p>
                  </div>
                )}
              </>
            )}

            {/* Analysis */}
            {activeTab === "analysis" && (
              <>
                {job.match_explanation ? (
                  <div className="jd-analysis">
                    <p className="jd-analysis-text">{job.match_explanation}</p>
                    {job.skill_score_breakdown && Object.keys(job.skill_score_breakdown).length > 0 && (
                      <div className="jd-breakdown">
                        <h4 className="jd-breakdown-title">Score Breakdown</h4>
                        <div className="jd-breakdown-list">
                          {Object.entries(job.skill_score_breakdown)
                            .sort(([, a], [, b]) => b - a)
                            .map(([skill, pts]) => (
                              <div key={skill} className="jd-breakdown-item">
                                <span className="jd-breakdown-skill">{skill}</span>
                                <span className="jd-breakdown-pts">+{pts}</span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="jd-tab-empty">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="16" x2="12" y2="12" />
                      <line x1="12" y1="8" x2="12.01" y2="8" />
                    </svg>
                    <p>No analysis available.</p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Application Section */}
      {app && (
        <div className="jd-card jd-app-card">
          <div className="jd-card-header">
            <h3 className="jd-card-title">Application</h3>
            <div className="jd-app-header-right">
              <StatusChip status={app.status} />
              <span className="jd-app-date">
                {app.sent_at ? new Date(app.sent_at).toLocaleDateString("en-IN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "N/A"}
              </span>
            </div>
          </div>

          {app.error_message && (
            <div className="jd-alert jd-alert-error">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
              {app.error_message}
            </div>
          )}

          {app.email_subject && (
            <div className="jd-info-inline">
              <span className="jd-info-label">Subject:</span>
              <span className="jd-info-value">{app.email_subject}</span>
            </div>
          )}

          {/* Criteria */}
          {app.criteria_data && Object.keys(app.criteria_data).length > 0 && (
            <div className="jd-criteria">
              <h4 className="jd-criteria-title">Criteria Sent</h4>
              <div className="jd-criteria-grid">
                {app.criteria_data.role_level && (
                  <div className="jd-criteria-item">
                    <span className="jd-criteria-label">Role</span>
                    <span className="jd-criteria-value">{String(app.criteria_data.role_level)}</span>
                  </div>
                )}
                {app.criteria_data.min_years_required && (
                  <div className="jd-criteria-item">
                    <span className="jd-criteria-label">Experience</span>
                    <span className="jd-criteria-value">{String(app.criteria_data.min_years_required)}yr</span>
                  </div>
                )}
                {app.criteria_data.sections_included && (
                  <div className="jd-criteria-item">
                    <span className="jd-criteria-label">Sections</span>
                    <span className="jd-criteria-value">{String(app.criteria_data.sections_included)}</span>
                  </div>
                )}
                {app.criteria_data.project_mentioned && (
                  <div className="jd-criteria-item">
                    <span className="jd-criteria-label">Project</span>
                    <span className="jd-criteria-value">{String(app.criteria_data.project_mentioned)}</span>
                  </div>
                )}
                {app.criteria_data.email_used && (
                  <div className="jd-criteria-item">
                    <span className="jd-criteria-label">Email</span>
                    <span className="jd-criteria-value">{String(app.criteria_data.email_used)}</span>
                  </div>
                )}
                <div className="jd-criteria-item">
                  <span className="jd-criteria-label">Resume</span>
                  <span className={"jd-criteria-value " + (app.criteria_data.resume_attached ? "good" : "bad")}>
                    {app.criteria_data.resume_attached ? "Attached" : "Missing"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Cover Letter Section — always visible */}
      <div className="jd-card jd-app-card">
        <div className="jd-card-header">
          <h3 className="jd-card-title">Cover Letter</h3>
        </div>

        {generateError && (
          <div className="jd-alert jd-alert-error">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            {generateError}
          </div>
        )}

        {app?.cover_letter_text ? (
          <div className="jd-cover">
            <div className="jd-cover-actions">
              <button className="jd-cover-toggle" onClick={copyCoverLetter}>
                {copied ? (
                  <>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    Copied!
                  </>
                ) : (
                  <>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </svg>
                    Copy
                  </>
                )}
              </button>
              <button
                className="jd-btn jd-btn-secondary jd-btn-sm"
                onClick={handleGenerateCoverLetter}
                disabled={generating}
              >
                {generating ? (
                  <>
                    <span className="spinner" /> Generating...
                  </>
                ) : (
                  <>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="23 4 23 10 17 10" />
                      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                    </svg>
                    Regenerate with AI
                  </>
                )}
              </button>
            </div>
            <pre className="jd-cover-text">{app.cover_letter_text}</pre>
          </div>
        ) : (
          <div className="jd-cover-empty">
            <div className="jd-cover-fallback-info">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <span>No cover letter yet. Generate an AI-tailored one for this position.</span>
            </div>
            <button
              className="jd-btn jd-btn-primary"
              onClick={handleGenerateCoverLetter}
              disabled={generating}
            >
              {generating ? (
                <>
                  <span className="spinner" /> Generating cover letter...
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                  </svg>
                  Generate Cover Letter
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </>
  );
}
