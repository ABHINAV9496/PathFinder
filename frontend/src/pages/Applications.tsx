import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useTitle } from "../hooks/useTitle";
import { jobFilterParams } from "../hooks/useJobFilters";
import JobFilters from "../components/JobFilters";
import { ListItemSkeleton } from "../components/Skeleton";
import type { Application, PaginatedResponse } from "../types";

type StatusFilter = "all" | "sent" | "failed";

interface StatusMeta {
  label: string;
  color: string;
  bg: string;
}

const STATUS_MAP: Record<string, StatusMeta> = {
  sent: { label: "Sent", color: "var(--green)", bg: "var(--green-bg)" },
  failed: { label: "Failed", color: "var(--red)", bg: "var(--red-bg)" },
};

function MatchRing({ pct }: { pct: number }) {
  const r = 18;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  const color = pct >= 70 ? "var(--green)" : pct >= 50 ? "var(--accent)" : "var(--amber)";
  return (
    <svg width="44" height="44" viewBox="0 0 44 44" className="ap-ring">
      <circle cx="22" cy="22" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="3" />
      <circle cx="22" cy="22" r={r} fill="none" stroke={color} strokeWidth="3"
        strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
        transform="rotate(-90 22 22)" />
      <text x="22" y="22" textAnchor="middle" dominantBaseline="central"
        className="ap-ring-text">{pct}</text>
    </svg>
  );
}

function SkillPill({ skill, gap }: { skill: string; gap?: boolean }) {
  return (
    <span className={"ap-skill" + (gap ? " ap-skill-gap" : "")}>
      {gap && <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>}
      {skill}
    </span>
  );
}

function AppCard({ app }: { app: Application }) {
  const meta = STATUS_MAP[app.status] || { label: app.status, color: "var(--muted)", bg: "var(--surface-2)" };
  const [expanded, setExpanded] = useState(false);
  const sentDate = new Date(app.sent_at);
  const now = new Date();
  const diffH = Math.floor((now.getTime() - sentDate.getTime()) / 3600000);
  const relative = diffH < 1 ? "Just now" : diffH < 24 ? `${diffH}h ago` : `${Math.floor(diffH / 24)}d ago`;

  return (
    <div className={"ap-card" + (expanded ? " ap-card-open" : "")}>
      <div className="ap-card-main" onClick={() => setExpanded(!expanded)}>
        <div className="ap-card-left">
          <MatchRing pct={app.job.match_score} />
        </div>

        <div className="ap-card-body">
          <div className="ap-card-title-row">
            <Link to={`/jobs/${app.job.id}`} className="ap-card-title" onClick={(e) => e.stopPropagation()}>
              {app.job.title}
            </Link>
            <span className="ap-status" style={{ color: meta.color, background: meta.bg }}>
              <span className="ap-status-dot" style={{ background: meta.color }} />
              {meta.label}
            </span>
          </div>

          <div className="ap-card-meta">
            <span className="ap-meta-item">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18zM6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/></svg>
              {app.job.company}
            </span>
            <span className="ap-meta-item">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
              {app.job.location}
            </span>
            <span className="ap-meta-item ap-meta-time">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              {relative}
            </span>
          </div>

          {app.skills_highlighted.length > 0 && (
            <div className="ap-skills-row">
              {app.skills_highlighted.slice(0, 6).map((s) => <SkillPill key={s} skill={s} />)}
              {app.skill_gaps.length > 0 && app.skill_gaps.slice(0, 2).map((s) => <SkillPill key={s} skill={s} gap />)}
              <span className="ap-match-badge">{app.skill_match_pct}% match</span>
            </div>
          )}
        </div>

        <div className="ap-card-chevron">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
        </div>
      </div>

      {expanded && (
        <div className="ap-card-detail">
          {app.match_explanation && (
            <div className="ap-detail-section">
              <span className="ap-detail-label">Why this match</span>
              <p className="ap-detail-text">{app.match_explanation}</p>
            </div>
          )}
          {app.cover_letter_text && (
            <div className="ap-detail-section">
              <span className="ap-detail-label">Cover letter</span>
              <p className="ap-detail-text ap-detail-letter">{app.cover_letter_text.slice(0, 400)}{app.cover_letter_text.length > 400 ? "..." : ""}</p>
            </div>
          )}
          {app.error_message && (
            <div className="ap-detail-section">
              <span className="ap-detail-label ap-detail-label-error">Error</span>
              <p className="ap-detail-text ap-detail-error">{app.error_message}</p>
            </div>
          )}
          {app.skill_gaps.length > 0 && (
            <div className="ap-detail-section">
              <span className="ap-detail-label">Skill gaps</span>
              <div className="ap-skills-row">
                {app.skill_gaps.map((s) => <SkillPill key={s} skill={s} gap />)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Applications() {
  useTitle("Applications", "Track sent email applications, match scores, and skill gaps.");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [data, setData] = useState<PaginatedResponse<Application> | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    setLoading(true);
    const params: Record<string, string> = { ...jobFilterParams(searchParams) };
    if (status !== "all") params.status = status;
    api.applications.list(params).then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [status, searchParams]);

  const totalCount = data?.count ?? 0;
  const sentCount = data?.results.filter((a) => a.status === "sent").length ?? 0;
  const failedCount = data?.results.filter((a) => a.status === "failed").length ?? 0;

  return (
    <>
      <div className="ap-page-header">
        <div>
          <h2 className="ap-title">Applications</h2>
          <p className="ap-subtitle">Track your sent emails and application status</p>
        </div>
        <div className="ap-summary">
          <div className="ap-summary-item">
            <span className="ap-summary-value">{totalCount}</span>
            <span className="ap-summary-label">Total</span>
          </div>
          <div className="ap-summary-divider" />
          <div className="ap-summary-item">
            <span className="ap-summary-value ap-summary-sent">{sentCount}</span>
            <span className="ap-summary-label">Sent</span>
          </div>
          <div className="ap-summary-divider" />
          <div className="ap-summary-item">
            <span className="ap-summary-value ap-summary-failed">{failedCount}</span>
            <span className="ap-summary-label">Failed</span>
          </div>
        </div>
      </div>

      <JobFilters />

      <div className="ap-filters">
        {(["all", "sent", "failed"] as StatusFilter[]).map((s) => {
          const count = s === "all" ? totalCount : s === "sent" ? sentCount : failedCount;
          return (
            <button key={s} className={"ap-filter-btn" + (status === s ? " active" : "")}
              onClick={() => setStatus(s)}>
              {s === "all" ? "All" : STATUS_MAP[s]?.label}
              <span className="ap-filter-count">{count}</span>
            </button>
          );
        })}
      </div>

      <div className="ap-list">
        {loading && (
          <>
            {[...Array(4)].map((_, i) => (
              <ListItemSkeleton key={i} />
            ))}
          </>
        )}

        {!loading && data?.results.map((app) => (
          <AppCard key={app.id} app={app} />
        ))}

        {!loading && data?.results.length === 0 && (
          <div className="ap-empty">
            <div className="ap-empty-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--border-h)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="4" width="20" height="16" rx="2" />
                <path d="M22 7l-10 7L2 7" />
              </svg>
            </div>
            <h3 className="ap-empty-title">No applications found</h3>
            <p className="ap-empty-text">No applications match the current filter. Run the fetcher to start matching jobs.</p>
            <Link to="/" className="ap-empty-link">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="23 4 23 10 17 10" />
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
              </svg>
              Go to Overview
            </Link>
          </div>
        )}
      </div>
    </>
  );
}
