import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useTitle } from "../hooks/useTitle";
import { jobFilterParams } from "../hooks/useJobFilters";
import JobFilters from "../components/JobFilters";

interface WebApplyItem {
  id: number;
  job_title?: string;
  company_name?: string;
  applied_on?: string;
  sent_at?: string;
  application_method?: string;
  status?: string;
  job?: { id: number; title: string; company?: string; company_name?: string };
  skill_match_pct?: number;
  skills_highlighted?: string[];
  skills_in_job_desc?: string[];
  error_message?: string;
}

function StatusIcon({ status }: { status: string }) {
  if (status === "web_apply") {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
        <polyline points="22 4 12 14.01 9 11.01" />
      </svg>
    );
  }
  if (status === "failed") {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="15" y1="9" x2="9" y2="15" />
        <line x1="9" y1="9" x2="15" y2="15" />
      </svg>
    );
  }
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function MatchBadge({ pct }: { pct: number }) {
  if (pct >= 80) {
    return <span className="wa-match wa-match-high">{pct}%</span>;
  }
  if (pct >= 50) {
    return <span className="wa-match wa-match-med">{pct}%</span>;
  }
  return <span className="wa-match wa-match-low">{pct}%</span>;
}

export default function WebApply() {
  useTitle("Web Apply", "Jobs applied directly through company websites and career pages.");
  const [items, setItems] = useState<WebApplyItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    setLoading(true);
    api.webApply.list(jobFilterParams(searchParams)).then((d: any) => {
      setItems(d.applications || []);
      setTotalCount(d.total_count || 0);
      setLoading(false);
    }).catch((err: Error) => {
      setError(err.message || "Failed to load web applications");
      setLoading(false);
    });
  }, [searchParams]);

  if (loading) {
    return (
      <>
        <div className="page-header"><h2>Web Apply</h2></div>
        <div className="st-loading">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="pf-skeleton pf-skeleton-line" style={{ height: 80, width: "100%" }} />
          ))}
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <div className="page-header"><h2>Web Apply</h2></div>
        <div className="st-empty">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <h3>Failed to load</h3>
          <p>{error}</p>
        </div>
      </>
    );
  }

  if (items.length === 0) {
    return (
      <>
        <div className="page-header"><h2>Web Apply</h2></div>
        <JobFilters />
        <div className="st-empty">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
            <polyline points="22,6 12,13 2,6" />
          </svg>
          <h3>No web applications found</h3>
          <p>Jobs applied via the browser will appear here.</p>
        </div>
      </>
    );
  }

  const today = new Date().toDateString();
  const thisWeek = items.filter(app => {
    if (!app.sent_at) return false;
    const d = new Date(app.sent_at);
    const now = new Date();
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    return d >= weekAgo;
  }).length;

  const withErrors = items.filter(app => app.error_message).length;
  const avgMatch = items.reduce((sum, app) => sum + (app.skill_match_pct || 0), 0) / (items.length || 1);

  return (
    <>
      <div className="page-header">
        <h2>Web Apply <span className="count">({totalCount})</span></h2>
      </div>

      <JobFilters />

      {/* Summary */}
      <div className="st-summary-row">
        <div className="st-summary-card">
          <span className="st-summary-value">{totalCount}</span>
          <span className="st-summary-label">Total Sent</span>
        </div>
        <div className="st-summary-card">
          <span className="st-summary-value">{thisWeek}</span>
          <span className="st-summary-label">This Week</span>
        </div>
        <div className="st-summary-card">
          <span className="st-summary-value">{Math.round(avgMatch)}%</span>
          <span className="st-summary-label">Avg Match</span>
        </div>
        <div className="st-summary-card">
          <span className="st-summary-value">{withErrors}</span>
          <span className="st-summary-label">With Errors</span>
        </div>
      </div>

      {/* Pipeline */}
      <div className="st-card">
        <h3 className="st-card-title">Application Pipeline</h3>
        <div className="wa-pipeline">
          <div className="wa-pipeline-stage">
            <div className="wa-pipeline-count">{totalCount}</div>
            <div className="wa-pipeline-label">Total</div>
          </div>
          <div className="wa-pipeline-arrow">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </div>
          <div className="wa-pipeline-stage">
            <div className="wa-pipeline-count">{totalCount - withErrors}</div>
            <div className="wa-pipeline-label">Sent</div>
          </div>
          <div className="wa-pipeline-arrow">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </div>
          <div className="wa-pipeline-stage">
            <div className="wa-pipeline-count">{withErrors}</div>
            <div className="wa-pipeline-label">Errors</div>
          </div>
        </div>
      </div>

      {/* Applications List */}
      <div className="st-card">
        <h3 className="st-card-title">Applications</h3>
        <div className="wa-list">
          {items.map((app) => (
            <div key={app.id} className="wa-row">
              <div className="wa-row-icon">
                <StatusIcon status={app.status || "web_apply"} />
              </div>

              <div className="wa-row-info">
                <div className="wa-row-title">
                  {app.job ? (
                    <Link to={`/jobs/${app.job.id}`} className="wa-row-link">
                      {app.job.title}
                    </Link>
                  ) : (
                    <span className="wa-row-text">{app.job_title || "Unknown Job"}</span>
                  )}
                </div>
                <div className="wa-row-meta">
                  <span>{app.company_name || app.job?.company || app.job?.company_name || "—"}</span>
                  {app.application_method && (
                    <>
                      <span className="wa-row-dot">·</span>
                      <span>{app.application_method}</span>
                    </>
                  )}
                </div>
              </div>

              <div className="wa-row-skills">
                {app.skill_match_pct != null && <MatchBadge pct={app.skill_match_pct} />}
                {app.skills_highlighted && app.skills_highlighted.length > 0 && (
                  <div className="wa-row-tags">
                    {app.skills_highlighted.slice(0, 3).map((s, i) => (
                      <span key={i} className="skill-tag small">{s}</span>
                    ))}
                    {app.skills_highlighted.length > 3 && (
                      <span className="wa-row-more">+{app.skills_highlighted.length - 3}</span>
                    )}
                  </div>
                )}
              </div>

              <div className="wa-row-time">
                {app.sent_at
                  ? new Date(app.sent_at).toLocaleDateString("en-IN", {
                      month: "short",
                      day: "numeric",
                    })
                  : app.applied_on || "—"}
              </div>

              {app.error_message && (
                <div className="wa-row-error" title={app.error_message}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
