import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { api } from "../api/client";
import { JobCardSkeleton } from "../components/Skeleton";
import type { Job, PaginatedResponse } from "../types";

const STATUSES = ["all", "new", "matched", "applied", "web_apply", "ignored"];
const LOCATIONS = ["all", "kerala", "india", "remote"];
const SALARIES = [
  { value: "all", label: "All" },
  { value: "has", label: "Has Salary" },
  { value: "3l", label: "₹3L+ PA" },
  { value: "6l", label: "₹6L+ PA" },
  { value: "10l", label: "₹10L+ PA" },
];
const SORT_OPTIONS = [
  { value: "-match_score", label: "Score (High to Low)" },
  { value: "match_score", label: "Score (Low to High)" },
  { value: "-fetched_date", label: "Date (Newest First)" },
  { value: "company", label: "Company (A → Z)" },
  { value: "title", label: "Title (A → Z)" },
  { value: "-salary", label: "Salary (High to Low)" },
  { value: "salary", label: "Salary (Low to High)" },
];

function Dropdown({ label, value, options, open, onToggle, onSelect }: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  open: boolean;
  onToggle: () => void;
  onSelect: (v: string) => void;
}) {
  return (
    <div className="jb-filter">
      <button className={"jb-filter-btn" + (value !== "all" ? " active" : "")} onClick={onToggle}>
        {value === "all" ? label : options.find(o => o.value === value)?.label || label}
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      <div className={"jb-dropdown" + (open ? " open" : "")}>
        {options.map((o) => (
          <button key={o.value} className={"jb-dropdown-item" + (value === o.value ? " active" : "")} onClick={() => onSelect(o.value)}>
            <svg className="jb-dropdown-check" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function ScoreBadge({ score }: { score: number }) {
  if (score >= 50) return <span className="jb-score jb-score-high">{score}%</span>;
  if (score >= 30) return <span className="jb-score jb-score-med">{score}%</span>;
  return <span className="jb-score jb-score-low">{score}%</span>;
}

function StatusChip({ status }: { status: string }) {
  return <span className={"jb-chip jb-chip-" + status}>{status.replace("_", " ")}</span>;
}

export default function Jobs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const status = searchParams.get("status") || "all";
  const location = searchParams.get("location") || "all";
  const salary = searchParams.get("salary") || "all";
  const sort = searchParams.get("sort") || "-match_score";
  const page = searchParams.get("page") || "1";
  const searchQuery = searchParams.get("search") || "";
  const [searchInput, setSearchInput] = useState(searchQuery);

  const [data, setData] = useState<PaginatedResponse<Job> | null>(null);
  const [loading, setLoading] = useState(true);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api.jobs.list({ status, location, salary, sort, page, search: searchQuery }).then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [status, location, salary, sort, page, searchQuery]);

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    next.set(key, value);
    if (key !== "page") next.set("page", "1");
    setSearchParams(next);
    setOpenDropdown(null);
  }

  function clearAll() {
    setSearchParams({});
    setSearchInput("");
    setOpenDropdown(null);
  }

  function handleSearch() {
    setParam("search", searchInput);
  }

  const hasFilters = status !== "all" || location !== "all" || salary !== "all" || searchQuery !== "";

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Jobs</h2>
          <p className="page-subtitle">{data?.count?.toLocaleString() ?? "..."} jobs found</p>
        </div>
      </div>

      {/* Search + Filters */}
      <div className="jb-toolbar">
        <div className="jb-search">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            type="text"
            placeholder="Search by title, company, or skill..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
          />
          {searchInput && (
            <button className="jb-search-clear" onClick={() => { setSearchInput(""); setParam("search", ""); }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>

        <div className="jb-filters">
          <Dropdown
            label="Status"
            value={status}
            options={STATUSES.map(s => ({ value: s, label: s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1).replace("_", " ") }))}
            open={openDropdown === "status"}
            onToggle={() => setOpenDropdown(openDropdown === "status" ? null : "status")}
            onSelect={(v) => setParam("status", v)}
          />
          <Dropdown
            label="Location"
            value={location}
            options={LOCATIONS.map(l => ({ value: l, label: l === "all" ? "All" : l.charAt(0).toUpperCase() + l.slice(1) }))}
            open={openDropdown === "location"}
            onToggle={() => setOpenDropdown(openDropdown === "location" ? null : "location")}
            onSelect={(v) => setParam("location", v)}
          />
          <Dropdown
            label="Salary"
            value={salary}
            options={SALARIES}
            open={openDropdown === "salary"}
            onToggle={() => setOpenDropdown(openDropdown === "salary" ? null : "salary")}
            onSelect={(v) => setParam("salary", v)}
          />

          {hasFilters && (
            <button className="jb-clear" onClick={clearAll}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
              Clear
            </button>
          )}

          <div className="jb-filter-spacer" />

          <Dropdown
            label="Sort"
            value={sort}
            options={SORT_OPTIONS}
            open={openDropdown === "sort"}
            onToggle={() => setOpenDropdown(openDropdown === "sort" ? null : "sort")}
            onSelect={(v) => setParam("sort", v)}
          />
        </div>
      </div>

      {/* Job List */}
      <div className="jb-list">
        {loading && (
          <>
            {[...Array(6)].map((_, i) => (
              <JobCardSkeleton key={i} />
            ))}
          </>
        )}

        {!loading && data?.results.length === 0 && (
          <div className="jb-empty">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            <h3>No jobs found</h3>
            <p>Try adjusting your filters or search query.</p>
          </div>
        )}

        {!loading && data?.results.map((job) => (
          <Link key={job.id} to={`/jobs/${job.id}`} className="jb-card">
            <div className="jb-card-top">
              <ScoreBadge score={job.match_score} />
              <div className="jb-card-info">
                <span className="jb-card-title">{job.title}</span>
                <span className="jb-card-meta">
                  {job.company}
                  {job.location && <><span className="jb-dot">·</span>{job.location}</>}
                  {job.source && <><span className="jb-dot">·</span>{job.source}</>}
                </span>
              </div>
              <StatusChip status={job.status} />
            </div>

            {job.matched_skills?.length > 0 && (
              <div className="jb-card-skills">
                {job.matched_skills.slice(0, 6).map((skill) => (
                  <span key={skill} className="jb-skill">{skill}</span>
                ))}
                {job.matched_skills.length > 6 && (
                  <span className="jb-skill-more">+{job.matched_skills.length - 6}</span>
                )}
              </div>
            )}

            <div className="jb-card-bottom">
              <span className="jb-card-date">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
                {job.posted_date || "N/A"}
              </span>
              {job.salary_display && (
                <span className="jb-card-salary">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="1" x2="12" y2="23" />
                    <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                  </svg>
                  {job.salary_display}
                </span>
              )}
              <span className="jb-card-fetched">
                Fetched {new Date(job.fetched_date).toLocaleDateString("en-IN", { month: "short", day: "numeric" })}
              </span>
            </div>
          </Link>
        ))}
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="jb-pagination">
          <button
            className="jb-page-btn"
            disabled={!data.previous}
            onClick={() => setParam("page", String(Number(page) - 1))}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Previous
          </button>
          <span className="jb-page-info">Page {data.page} of {data.total_pages}</span>
          <button
            className="jb-page-btn"
            disabled={!data.next}
            onClick={() => setParam("page", String(Number(page) + 1))}
          >
            Next
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        </div>
      )}

      {/* Click-outside close */}
      {openDropdown && (
        <div className="jb-overlay" onClick={() => setOpenDropdown(null)} />
      )}
    </>
  );
}
