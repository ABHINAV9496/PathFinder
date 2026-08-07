import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useTitle } from "../hooks/useTitle";
import { jobFilterParams } from "../hooks/useJobFilters";
import JobFilters from "../components/JobFilters";
import type { Job } from "../types";

function MatchRing({ pct }: { pct: number }) {
  const r = 16;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  const color = pct >= 70 ? "var(--green)" : pct >= 50 ? "var(--accent)" : "var(--amber)";
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" className="me-ring">
      <circle cx="20" cy="20" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="2.5" />
      <circle cx="20" cy="20" r={r} fill="none" stroke={color} strokeWidth="2.5"
        strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
        transform="rotate(-90 20 20)" />
      <text x="20" y="20" textAnchor="middle" dominantBaseline="central"
        className="me-ring-text">{pct}</text>
    </svg>
  );
}

export default function MissingEmails() {
  useTitle("Missing Emails", "High-score jobs that couldn't be matched with a company email address.");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    setLoading(true);
    api.missingEmails.list(jobFilterParams(searchParams)).then((d: any) => {
      setJobs(d.jobs || []);
      setTotalCount(d.total_count || 0);
      setLoading(false);
    });
  }, [searchParams]);

  return (
    <>
      <div className="me-page-header">
        <div>
          <h2 className="me-title">Missing Emails</h2>
          <p className="me-subtitle">Matched jobs with no discoverable company email</p>
        </div>
        <div className="me-count-badge">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {totalCount} jobs
        </div>
      </div>

      <JobFilters />

      <div className="me-info-banner">
        <div className="me-info-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" />
          </svg>
        </div>
        <div className="me-info-text">
          <span className="me-info-title">What does this mean?</span>
          These jobs scored above the match threshold but their company email could not be found automatically.
          You can apply to these jobs directly through their website using the <strong>Web Apply</strong> feature.
        </div>
      </div>

      {loading && (
        <div className="me-list">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="me-card me-card-skeleton">
              <div className="me-card-left"><div className="me-skel-ring" /></div>
              <div className="me-card-body">
                <div className="me-skel-title" />
                <div className="me-skel-meta" />
                <div className="me-skel-tags" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && jobs.length === 0 && (
        <div className="me-empty">
          <div className="me-empty-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
          <h3 className="me-empty-title">All caught up</h3>
          <p className="me-empty-text">No matched jobs are missing an apply email. Every matched job has a contact method ready.</p>
        </div>
      )}

      {!loading && jobs.length > 0 && (
        <div className="me-list">
          {jobs.map((job) => (
            <div key={job.id} className="me-card">
              <div className="me-card-left">
                <MatchRing pct={job.match_score} />
              </div>

              <div className="me-card-body">
                <div className="me-card-title-row">
                  <Link to={`/jobs/${job.id}`} className="me-card-title">{job.title}</Link>
                  <span className="me-card-status">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    Matched
                  </span>
                </div>

                <div className="me-card-meta">
                  <span className="me-meta-item">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18zM6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/></svg>
                    {job.company}
                  </span>
                  <span className="me-meta-item">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                    {job.location}
                  </span>
                  <span className="me-meta-item">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                    {job.posted_date || "Unknown date"}
                  </span>
                  {job.salary_display && (
                    <span className="me-meta-item me-salary">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                      {job.salary_display}
                    </span>
                  )}
                  <span className="me-meta-item me-source">{job.source}</span>
                </div>

                {job.matched_skills.length > 0 && (
                  <div className="me-skills-row">
                    {job.matched_skills.slice(0, 8).map((s) => (
                      <span key={s} className="me-skill">{s}</span>
                    ))}
                    {job.matched_skills.length > 8 && (
                      <span className="me-skill me-skill-more">+{job.matched_skills.length - 8}</span>
                    )}
                  </div>
                )}

                <div className="me-card-footer">
                  <div className="me-no-email">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="2" y="4" width="20" height="16" rx="2" />
                      <path d="M22 7l-10 7L2 7" />
                    </svg>
                    No apply email found
                  </div>
                  {job.apply_url && (
                    <a href={job.apply_url} target="_blank" rel="noopener noreferrer" className="me-apply-link" onClick={(e) => e.stopPropagation()}>
                      Apply on website
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
