import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { FetcherProvider, useFetcher } from "./FetcherProgress";
import Overview from "./pages/Overview";
import Jobs from "./pages/Jobs";
import JobDetail from "./pages/JobDetail";
import Applications from "./pages/Applications";
import WebApply from "./pages/WebApply";
import MissingEmails from "./pages/MissingEmails";
import SkillStats from "./pages/SkillStats";
import CompanyStats from "./pages/CompanyStats";
import LocationStats from "./pages/LocationStats";
import Profile from "./pages/Profile";
import ApplyQueue from "./pages/ApplyQueue";

function Icon({ d, size = 18 }: { d: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

const NAV_ITEMS = [
  { to: "/", label: "Overview", d: "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z" },
  { to: "/jobs", label: "Jobs", d: "M20 7H4a1 1 0 0 0-1 1v11a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8a1 1 0 0 0-1-1ZM16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" },
  { to: "/applications", label: "Applications", d: "M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" },
  { to: "/apply-queue", label: "Apply Queue", d: "M22 2L11 13M22 2l-7 20-4-9-9-4 20-7zM16 2l6 6-6 6" },
  { to: "/web-apply", label: "Web Apply", d: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" },
  { to: "/missing-emails", label: "Missing", d: "M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01" },
];

const STAT_ITEMS = [
  { to: "/stats/skills", label: "Skills", d: "M16 18l6-6-6-6M8 6l-6 6 6 6" },
  { to: "/stats/companies", label: "Companies", d: "M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18zM6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2M10 6h4M10 10h4M10 14h4M10 18h4" },
  { to: "/stats/locations", label: "Locations", d: "M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0zM12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" },
];

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
            <path d="M2 12h20" />
          </svg>
        </div>
        <div className="sidebar-brand">
          <span className="sidebar-brand-name">JobbLoot</span>
          <span className="sidebar-brand-version">v0.1</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-section">
          <div className="sidebar-section-label">Main</div>
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")} end={item.to === "/"}>
              <Icon d={item.d} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-label">Analytics</div>
          {STAT_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}>
              <Icon d={item.d} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      <div className="sidebar-footer">
        <NavLink to="/profile" className={({ isActive }) => "sidebar-link sidebar-link-profile" + (isActive ? " active" : "")}>
          <div className="sidebar-avatar">N</div>
          <div className="sidebar-profile-info">
            <span className="sidebar-profile-name">Profile</span>
            <span className="sidebar-profile-sub">Settings & Account</span>
          </div>
        </NavLink>
      </div>
    </aside>
  );
}

function FetcherBanner() {
  const { progress } = useFetcher();
  if (!progress) return null;

  return (
    <div className="fetcher-banner">
      <div className="fetcher-banner-inner">
        <div className="fetcher-banner-bar">
          <div className="fetcher-banner-bar-fill" style={{ width: (progress.running ? progress.percent : 100) + "%" }} />
        </div>
        <div className="fetcher-banner-meta">
          <span className="fetcher-banner-step">{progress.message}</span>
          <span className="fetcher-banner-pct">
            {progress.running ? progress.percent + "%" : "Done"}
            {progress.elapsed_seconds ? ` \u00b7 ${progress.elapsed_seconds}s` : ""}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <FetcherProvider>
        <Sidebar />
        <div className="app-content">
          <FetcherBanner />
          <main>
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/jobs" element={<Jobs />} />
              <Route path="/jobs/:id" element={<JobDetail />} />
              <Route path="/applications" element={<Applications />} />
              <Route path="/apply-queue" element={<ApplyQueue />} />
              <Route path="/web-apply" element={<WebApply />} />
              <Route path="/missing-emails" element={<MissingEmails />} />
              <Route path="/stats/skills" element={<SkillStats />} />
              <Route path="/stats/companies" element={<CompanyStats />} />
              <Route path="/stats/locations" element={<LocationStats />} />
              <Route path="/profile" element={<Profile />} />
            </Routes>
          </main>
        </div>
      </FetcherProvider>
    </BrowserRouter>
  );
}
