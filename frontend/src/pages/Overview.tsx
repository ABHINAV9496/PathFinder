import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Chart, registerables } from "chart.js";
import { api } from "../api/client";
import { useFetcher } from "../FetcherProgress";
import { StatCardSkeleton } from "../components/Skeleton";
import { useTitle } from "../hooks/useTitle";

Chart.register(...registerables);

interface OverviewData {
  total_jobs: number;
  total_matched: number;
  total_applied: number;
  total_failed: number;
  total_ignored: number;
  total_web_apply: number;
  recent_jobs: { id: number; title: string; company: string; location: string; match_score: number; status: string; fetched_date: string }[];
  recent_apps: { id: number; job__id: number; job__title: string; job__company: string; job__match_score: number; status: string; sent_at: string }[];
  chart: { dates: string[]; fetched: number[]; matched: number[]; applied: number[] };
  top_skills: { skill_name: string; count: number }[];
}

function StatCard({ icon, value, label, trend }: { icon: React.ReactNode; value: string | number; label: string; trend?: { value: string; positive: boolean } }) {
  return (
    <div className="ov-stat">
      <div className="ov-stat-icon">{icon}</div>
      <div className="ov-stat-content">
        <span className="ov-stat-value">{value}</span>
        <span className="ov-stat-label">{label}</span>
      </div>
      {trend && (
        <span className={"ov-stat-trend " + (trend.positive ? "positive" : "negative")}>{trend.value}</span>
      )}
    </div>
  );
}

function ScoreBadge({ score }: { score: number }) {
  if (score >= 50) return <span className="ov-score ov-score-high">{score}%</span>;
  if (score >= 30) return <span className="ov-score ov-score-med">{score}%</span>;
  return <span className="ov-score ov-score-low">{score}%</span>;
}

function StatusChip({ status }: { status: string }) {
  return <span className={"ov-chip ov-chip-" + status}>{status.replace("_", " ")}</span>;
}

export default function Overview() {
  useTitle("Overview", "Your job search at a glance — jobs, matches, and applications dashboard.");
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetcherStatus, setFetcherStatus] = useState("");
  const { progress, running: fetcherRunning, startFetcher } = useFetcher();
  const timelineRef = useRef<HTMLCanvasElement>(null);
  const skillsRef = useRef<HTMLCanvasElement>(null);
  const timelineChartRef = useRef<Chart | null>(null);
  const skillsChartRef = useRef<Chart | null>(null);

  useEffect(() => {
    api.stats.overview().then((d) => {
      setData(d as unknown as OverviewData);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (!data || loading) return;

    if (timelineRef.current) {
      if (timelineChartRef.current) timelineChartRef.current.destroy();
      timelineChartRef.current = new Chart(timelineRef.current, {
        type: "line",
        data: {
          labels: data.chart.dates,
          datasets: [
            {
              label: "Fetched",
              data: data.chart.fetched,
              borderColor: "#2563EB",
              backgroundColor: "rgba(37,99,235,.04)",
              fill: true,
              tension: 0.4,
              pointRadius: 0,
              pointHoverRadius: 5,
              pointHoverBackgroundColor: "#2563EB",
              pointHoverBorderColor: "#fff",
              pointHoverBorderWidth: 2,
              borderWidth: 2,
            },
            {
              label: "Matched",
              data: data.chart.matched,
              borderColor: "#10B981",
              backgroundColor: "rgba(16,185,129,.04)",
              fill: true,
              tension: 0.4,
              pointRadius: 0,
              pointHoverRadius: 5,
              pointHoverBackgroundColor: "#10B981",
              pointHoverBorderColor: "#fff",
              pointHoverBorderWidth: 2,
              borderWidth: 2,
            },
            {
              label: "Applied",
              data: data.chart.applied,
              borderColor: "#F59E0B",
              backgroundColor: "rgba(245,158,11,.04)",
              fill: true,
              tension: 0.4,
              pointRadius: 0,
              pointHoverRadius: 5,
              pointHoverBackgroundColor: "#F59E0B",
              pointHoverBorderColor: "#fff",
              pointHoverBorderWidth: 2,
              borderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { intersect: false, mode: "index" },
          plugins: {
            legend: { position: "bottom", labels: { boxWidth: 12, padding: 16, color: "#64748B", font: { size: 12, family: "Inter" }, usePointStyle: true, pointStyle: "circle" } },
            tooltip: { backgroundColor: "#0F172A", titleFont: { size: 12, family: "Inter" }, bodyFont: { size: 12, family: "Inter" }, padding: 10, cornerRadius: 8, displayColors: true, boxWidth: 8, boxHeight: 8, boxPadding: 4 },
          },
          scales: {
            x: { grid: { display: false }, ticks: { color: "#94A3B8", font: { size: 11, family: "Inter" } }, border: { display: false } },
            y: { grid: { color: "#F1F5F9" }, ticks: { color: "#94A3B8", font: { size: 11, family: "Inter" } }, border: { display: false } },
          },
        },
      });
    }

    if (skillsRef.current && data.top_skills.length > 0) {
      if (skillsChartRef.current) skillsChartRef.current.destroy();
      const colors = ["#2563EB", "#10B981", "#F59E0B", "#8B5CF6", "#06B6D4", "#F97316", "#EC4899", "#6366F1", "#14B8A6", "#EF4444"];
      skillsChartRef.current = new Chart(skillsRef.current, {
        type: "bar",
        data: {
          labels: data.top_skills.slice(0, 8).map((s) => s.skill_name),
          datasets: [{
            label: "Matches",
            data: data.top_skills.slice(0, 8).map((s) => s.count),
            backgroundColor: colors.slice(0, data.top_skills.length),
            borderRadius: 6,
            barThickness: 24,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: "y",
          plugins: { legend: { display: false }, tooltip: { backgroundColor: "#0F172A", titleFont: { size: 12, family: "Inter" }, bodyFont: { size: 12, family: "Inter" }, padding: 10, cornerRadius: 8 } },
          scales: {
            x: { grid: { color: "#F1F5F9" }, ticks: { color: "#94A3B8", stepSize: 1, font: { size: 11, family: "Inter" } }, border: { display: false } },
            y: { grid: { display: false }, ticks: { color: "#0F172A", font: { size: 12, weight: 500, family: "Inter" } }, border: { display: false } },
          },
        },
      });
    }

    return () => {
      if (timelineChartRef.current) timelineChartRef.current.destroy();
      if (skillsChartRef.current) skillsChartRef.current.destroy();
    };
  }, [data, loading]);

  function handleRunFetcher() {
    setFetcherStatus("");
    startFetcher();
  }

  if (loading) {
    return (
      <>
        <div className="page-header">
          <div>
            <h2>Overview</h2>
            <p className="page-subtitle">Your job search at a glance</p>
          </div>
        </div>
        <div className="ov-stats">
          {[...Array(5)].map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
      </>
    );
  }

  if (!data) return <div className="ov-empty"><h3>No data available</h3></div>;

  const total = data.total_jobs || 1;
  const matchRate = total > 0 ? Math.round((data.total_matched / total) * 100) : 0;
  const applyRate = total > 0 ? Math.round((data.total_applied / total) * 100) : 0;

  return (
    <>
      <div className="page-header">
        <div>
          <h2>Overview</h2>
          <p className="page-subtitle">Your job search at a glance</p>
        </div>
        <button className="ov-fetcher-btn" onClick={handleRunFetcher} disabled={fetcherRunning}>
          {fetcherRunning ? (
            <span className="ov-fetcher-loading">
              <span className="ov-spinner" />
              Running...
            </span>
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="23 4 23 10 17 10" />
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
              </svg>
              Run Fetcher
            </>
          )}
        </button>
      </div>

      {fetcherStatus && (
        <div className={"ov-fetcher-status " + (fetcherStatus.includes("Error") ? "error" : "success")}>
          {fetcherStatus}
        </div>
      )}

      {/* Stats */}
      <div className="ov-stats">
        <StatCard
          icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2" /><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" /></svg>}
          value={data.total_jobs.toLocaleString()}
          label="Total Jobs"
        />
        <StatCard
          icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>}
          value={data.total_matched}
          label="Matched"
          trend={{ value: matchRate + "%", positive: true }}
        />
        <StatCard
          icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>}
          value={data.total_applied}
          label="Applied"
          trend={{ value: applyRate + "%", positive: true }}
        />
        <StatCard
          icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>}
          value={data.total_failed}
          label="Failed"
        />
        <StatCard
          icon={<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></svg>}
          value={data.total_web_apply}
          label="Web Apply"
        />
      </div>

      {/* Charts */}
      <div className="ov-charts">
        <div className="ov-card ov-chart-card">
          <div className="ov-card-header">
            <h3 className="ov-card-title">Jobs Over Time</h3>
            <span className="ov-card-badge">Last 30 days</span>
          </div>
          <div className="ov-chart-wrap">
            <canvas ref={timelineRef} />
          </div>
        </div>
        <div className="ov-card ov-chart-card">
          <div className="ov-card-header">
            <h3 className="ov-card-title">Top Skills</h3>
            <Link to="/stats/skills" className="ov-card-link">View all</Link>
          </div>
          <div className="ov-chart-wrap">
            <canvas ref={skillsRef} />
          </div>
        </div>
      </div>

      {/* Status Distribution */}
      <div className="ov-card">
        <div className="ov-card-header">
          <h3 className="ov-card-title">Jobs by Status</h3>
        </div>
        <div className="ov-status-grid">
          {[
            { key: "matched", label: "Matched", count: data.total_matched, color: "#10B981" },
            { key: "applied", label: "Applied", count: data.total_applied, color: "#2563EB" },
            { key: "web_apply", label: "Web Apply", count: data.total_web_apply, color: "#8B5CF6" },
            { key: "failed", label: "Failed", count: data.total_failed, color: "#EF4444" },
            { key: "ignored", label: "Ignored", count: data.total_ignored, color: "#94A3B8" },
          ].map((s) => (
            <div key={s.key} className="ov-status-item">
              <div className="ov-status-header">
                <span className="ov-status-dot" style={{ background: s.color }} />
                <span className="ov-status-label">{s.label}</span>
              </div>
              <span className="ov-status-count">{s.count}</span>
              <div className="ov-status-bar">
                <div className="ov-status-bar-fill" style={{ width: `${total > 0 ? (s.count / total) * 100 : 0}%`, background: s.color }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="ov-activity">
        {/* Recent Jobs */}
        <div className="ov-card">
          <div className="ov-card-header">
            <h3 className="ov-card-title">Recent Jobs</h3>
            <Link to="/jobs" className="ov-card-link">View all</Link>
          </div>
          {data.recent_jobs.length === 0 ? (
            <div className="ov-empty-inline">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
              </svg>
              <p>No jobs yet. Run the fetcher to get started.</p>
            </div>
          ) : (
            <div className="ov-list">
              {data.recent_jobs.slice(0, 5).map((j) => (
                <Link key={j.id} to={`/jobs/${j.id}`} className="ov-list-item">
                  <div className="ov-list-main">
                    <ScoreBadge score={j.match_score} />
                    <div className="ov-list-info">
                      <span className="ov-list-title">{j.title}</span>
                      <span className="ov-list-meta">{j.company} · {j.location}</span>
                    </div>
                  </div>
                  <StatusChip status={j.status} />
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recent Applications */}
        <div className="ov-card">
          <div className="ov-card-header">
            <h3 className="ov-card-title">Recent Applications</h3>
            <Link to="/applications" className="ov-card-link">View all</Link>
          </div>
          {data.recent_apps.length === 0 ? (
            <div className="ov-empty-inline">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
              <p>No applications sent yet.</p>
            </div>
          ) : (
            <div className="ov-list">
              {data.recent_apps.slice(0, 5).map((a) => (
                <Link key={a.id} to={`/jobs/${a.job__id}`} className="ov-list-item">
                  <div className="ov-list-main">
                    <StatusChip status={a.status} />
                    <div className="ov-list-info">
                      <span className="ov-list-title">{a.job__title}</span>
                      <span className="ov-list-meta">{a.job__company} · {new Date(a.sent_at).toLocaleDateString("en-IN", { month: "short", day: "numeric" })}</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Top Skills Cloud */}
      {data.top_skills.length > 0 && (
        <div className="ov-card">
          <div className="ov-card-header">
            <h3 className="ov-card-title">Top Skills</h3>
            <Link to="/stats/skills" className="ov-card-link">View all</Link>
          </div>
          <div className="ov-skills">
            {data.top_skills.slice(0, 12).map((s) => (
              <span key={s.skill_name} className="ov-skill" title={`${s.count} occurrences`}>
                {s.skill_name}
                <span className="ov-skill-count">{s.count}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
