import { useState } from "react";
import { useJobFilters } from "../hooks/useJobFilters";

interface MultiDropdownProps {
  label: string;
  options: string[];
  selected: string[];
  onChange: (values: string[]) => void;
  open: boolean;
  onToggle: () => void;
}

function MultiDropdown({ label, options, selected, onChange, open, onToggle }: MultiDropdownProps) {
  const [query, setQuery] = useState("");
  const filtered = query
    ? options.filter((o) => o.toLowerCase().includes(query.toLowerCase()))
    : options;

  const toggle = (value: string) => {
    onChange(selected.includes(value) ? selected.filter((s) => s !== value) : [...selected, value]);
  };

  return (
    <div className="jf-filter">
      <button className={"jf-btn" + (selected.length > 0 ? " active" : "")} onClick={onToggle}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="4" y1="21" x2="4" y2="14" /><line x1="4" y1="10" x2="4" y2="3" /><line x1="12" y1="21" x2="12" y2="12" /><line x1="12" y1="8" x2="12" y2="3" /><line x1="20" y1="21" x2="20" y2="16" /><line x1="20" y1="12" x2="20" y2="3" /><line x1="1" y1="14" x2="7" y2="14" /><line x1="9" y1="8" x2="15" y2="8" /><line x1="17" y1="16" x2="23" y2="16" /></svg>
        {label}
        {selected.length > 0 && <span className="jf-count">{selected.length}</span>}
        <svg className="jf-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9" /></svg>
      </button>
      {open && (
        <div className="jf-dropdown">
          <div className="jf-search">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Search ${label.toLowerCase()}...`}
              autoFocus
            />
          </div>
          <div className="jf-list">
            {filtered.map((o) => (
              <label key={o} className={"jf-item" + (selected.includes(o) ? " active" : "")}>
                <input type="checkbox" checked={selected.includes(o)} onChange={() => toggle(o)} />
                <span className="jf-item-text">{o}</span>
              </label>
            ))}
            {filtered.length === 0 && <div className="jf-empty">No matches</div>}
          </div>
          <div className="jf-actions">
            <button onClick={() => { onChange(options); setQuery(""); }}>Select all</button>
            <button onClick={() => onChange([])}>Clear</button>
          </div>
        </div>
      )}
    </div>
  );
}

interface SingleDropdownProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  open: boolean;
  onToggle: () => void;
}

function SingleDropdown({ label, value, options, onChange, open, onToggle }: SingleDropdownProps) {
  const current = options.find((o) => o.value === value);
  return (
    <div className="jf-filter">
      <button className={"jf-btn" + (value !== "all" ? " active" : "")} onClick={onToggle}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" /></svg>
        {current?.label || label}
        <svg className="jf-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9" /></svg>
      </button>
      {open && (
        <div className="jf-dropdown">
          {options.map((o) => (
            <button
              key={o.value}
              className={"jf-item-single" + (value === o.value ? " active" : "")}
              onClick={() => { onChange(o.value); onToggle(); }}
            >
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function JobFilters() {
  const { options, sources, locations, workType, setSources, setLocations, setWorkType, clear, hasFilters } = useJobFilters();
  const [open, setOpen] = useState<string | null>(null);

  return (
    <>
      {open && <div className="jf-overlay" onClick={() => setOpen(null)} />}
      <div className="jf-bar">
        <MultiDropdown
          label="Source"
          options={options.sources}
          selected={sources}
          onChange={setSources}
          open={open === "source"}
          onToggle={() => setOpen(open === "source" ? null : "source")}
        />
        <MultiDropdown
          label="Location"
          options={options.locations}
          selected={locations}
          onChange={setLocations}
          open={open === "location"}
          onToggle={() => setOpen(open === "location" ? null : "location")}
        />
        <SingleDropdown
          label="Work type: All"
          value={workType}
          options={[
            { value: "all", label: "Work type: All" },
            ...options.work_types.map((w) => ({
              value: w,
              label: `Work type: ${w.charAt(0).toUpperCase()}${w.slice(1)}`,
            })),
          ]}
          onChange={setWorkType}
          open={open === "work_type"}
          onToggle={() => setOpen(open === "work_type" ? null : "work_type")}
        />
        {hasFilters && (
          <button className="jf-clear" onClick={clear}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
            Clear
          </button>
        )}
      </div>
    </>
  );
}
