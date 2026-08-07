import { useEffect, useState, useRef, useCallback } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useTitle } from "../hooks/useTitle";
import { jobFilterParams } from "../hooks/useJobFilters";
import JobFilters from "../components/JobFilters";
import { ListItemSkeleton } from "../components/Skeleton";
import type { Job, PaginatedResponse } from "../types";

function MatchRing({ pct }: { pct: number }) {
  const r = 18;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  const color = pct >= 70 ? "var(--green)" : pct >= 50 ? "var(--accent)" : "var(--amber)";
  return (
    <svg width="44" height="44" viewBox="0 0 44 44" className="aq-ring">
      <circle cx="22" cy="22" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="3" />
      <circle cx="22" cy="22" r={r} fill="none" stroke={color} strokeWidth="3"
        strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
        transform="rotate(-90 22 22)" />
      <text x="22" y="22" textAnchor="middle" dominantBaseline="central"
        className="aq-ring-text">{pct}</text>
    </svg>
  );
}

export default function ApplyQueue() {
  useTitle("Apply Queue", "Review matched jobs and apply with one click.");
  const [data, setData] = useState<PaginatedResponse<Job> | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ total: 0, done: 0, succeeded: 0, failed: 0, current: "" });
  const [applyingSingle, setApplyingSingle] = useState<number | null>(null);
  const [toast, setToast] = useState<{ type: "success" | "error"; msg: string } | null>(null);
  const [page, setPage] = useState(1);
  const [searchParams] = useSearchParams();
  const progressTimer = useRef<ReturnType<typeof setInterval>>();
  const toastTimer = useRef<ReturnType<typeof setTimeout>>();

  const loadData = useCallback(() => {
    setLoading(true);
    api.applyQueue.list({ page: String(page), ...jobFilterParams(searchParams) }).then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [page, searchParams]);

  useEffect(() => { loadData(); }, [loadData]);

  function showToast(type: "success" | "error", msg: string) {
    setToast({ type, msg });
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 4000);
  }

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (!data) return;
    if (selected.size === data.results.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(data.results.map((j) => j.id)));
    }
  };

  const handleApplySingle = async (jobId: number) => {
    setApplyingSingle(jobId);
    try {
      const res = await api.jobs.apply(jobId) as any;
      if (res.success) {
        showToast("success", res.message || "Application sent!");
        loadData();
      } else {
        showToast("error", res.message || "Failed to send application.");
      }
    } catch (e: any) {
      showToast("error", e.message || "Failed to apply.");
    }
    setApplyingSingle(null);
  };

  const handleBatchApply = async () => {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    setBatchRunning(true);
    try {
      await api.applyQueue.applyBatch(ids);
      pollProgress();
    } catch (e: any) {
      showToast("error", e.message || "Failed to start batch apply.");
      setBatchRunning(false);
    }
  };

  const pollProgress = useCallback(() => {
    clearInterval(progressTimer.current);
    progressTimer.current = setInterval(async () => {
      try {
        const p = await api.applyQueue.progress();
        setBatchProgress(p);
        if (!p.running) {
          clearInterval(progressTimer.current);
          setBatchRunning(false);
          setSelected(new Set());
          loadData();
          if (p.succeeded > 0) {
            showToast("success", `Applied to ${p.succeeded} job${p.succeeded > 1 ? "s" : ""}${p.failed > 0 ? `, ${p.failed} failed` : ""}`);
          } else if (p.failed > 0) {
            showToast("error", `All ${p.failed} applications failed.`);
          }
        }
      } catch {
        clearInterval(progressTimer.current);
        setBatchRunning(false);
      }
    }, 1500);
  }, [loadData]);

  useEffect(() => () => clearInterval(progressTimer.current), []);

  return (
    <>
      {toast && <div className={`aq-toast ${toast.type}`}>{toast.msg}</div>}

      {/* Batch progress bar */}
      {batchRunning && (
        <div className="aq-progress">
          <div className="aq-progress-inner">
            <div className="aq-progress-bar">
              <div className="aq-progress-fill" style={{ width: `${batchProgress.total > 0 ? (batchProgress.done / batchProgress.total) * 100 : 0}%` }} />
            </div>
            <div className="aq-progress-meta">
              <span>{batchProgress.done}/{batchProgress.total} processed</span>
              <span className="aq-progress-ok">{batchProgress.succeeded} sent</span>
              {batchProgress.failed > 0 && <span className="aq-progress-fail">{batchProgress.failed} failed</span>}
              {batchProgress.current && <span className="aq-progress-current">{batchProgress.current}</span>}
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="aq-header">
        <div>
          <h2 className="aq-title">Apply Queue</h2>
          <p className="aq-subtitle">Matched jobs with company emails. Select and apply with one click.</p>
        </div>
        <div className="aq-header-right">
          <span className="aq-count">{data?.count ?? 0} jobs ready</span>
          {selected.size > 0 && !batchRunning && (
            <button className="aq-btn-apply" onClick={handleBatchApply}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
              Apply Selected ({selected.size})
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <JobFilters />

      {/* Select all */}
      {!loading && data && data.results.length > 0 && (
        <div className="aq-select-all">
          <label className="aq-checkbox-label">
            <input
              type="checkbox"
              checked={selected.size === data.results.length && data.results.length > 0}
              onChange={toggleSelectAll}
              className="aq-checkbox"
            />
            Select all
          </label>
        </div>
      )}

      {/* Job list */}
      <div className="aq-list">
        {loading && (
          <>
            {[...Array(4)].map((_, i) => (
              <ListItemSkeleton key={i} hasAvatar={false} />
            ))}
          </>
        )}

        {!loading && data?.results.map((job) => (
          <div key={job.id} className={"aq-card" + (selected.has(job.id) ? " aq-card-selected" : "")}>
            <div className="aq-card-main">
              <input
                type="checkbox"
                checked={selected.has(job.id)}
                onChange={() => toggleSelect(job.id)}
                className="aq-checkbox"
              />
              <div className="aq-card-left">
                <MatchRing pct={job.match_score} />
              </div>
              <div className="aq-card-body">
                <div className="aq-card-title-row">
                  <Link to={`/jobs/${job.id}`} className="aq-card-title">{job.title}</Link>
                  {job.has_failed_app && (
                    <span className="aq-badge aq-badge-failed">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                      Retry
                    </span>
                  )}
                  <span className="aq-email-badge">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="2" y="4" width="20" height="16" rx="2" />
                      <path d="M22 7l-10 7L2 7" />
                    </svg>
                    {job.apply_email}
                  </span>
                </div>

                <div className="aq-card-meta">
                  <span className="aq-meta-item">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18zM6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/></svg>
                    {job.company}
                  </span>
                  <span className="aq-meta-item">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                    {job.location}
                  </span>
                  {job.salary_display && (
                    <span className="aq-meta-item aq-salary">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                      {job.salary_display}
                    </span>
                  )}
                  <span className="aq-meta-item aq-source">{job.source}</span>
                </div>

                {job.matched_skills.length > 0 && (
                  <div className="aq-skills-row">
                    {job.matched_skills.slice(0, 6).map((s) => (
                      <span key={s} className="aq-skill">{s}</span>
                    ))}
                    {job.matched_skills.length > 6 && (
                      <span className="aq-skill aq-skill-more">+{job.matched_skills.length - 6}</span>
                    )}
                  </div>
                )}
              </div>

              <button
                className={"aq-btn-send" + (applyingSingle === job.id ? " aq-btn-sending" : "")}
                onClick={() => handleApplySingle(job.id)}
                disabled={applyingSingle !== null || batchRunning}
                title="Send application"
              >
                {applyingSingle === job.id ? (
                  <span className="spinner" />
                ) : (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        ))}

        {!loading && data?.results.length === 0 && (
          <div className="aq-empty">
            <div className="aq-empty-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>
            <h3 className="aq-empty-title">All caught up</h3>
            <p className="aq-empty-text">No more jobs in the queue. Run the fetcher to find new matches.</p>
            <Link to="/" className="aq-empty-link">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="23 4 23 10 17 10" />
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
              </svg>
              Go to Overview
            </Link>
          </div>
        )}
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="aq-pagination">
          <button className="aq-page-btn" disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>Previous</button>
          <span className="aq-page-info">Page {data.page} of {data.total_pages}</span>
          <button className="aq-page-btn" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      )}
    </>
  );
}
