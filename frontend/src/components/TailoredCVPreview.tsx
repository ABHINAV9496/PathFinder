import { useState } from "react";

interface TailoredCVPreviewProps {
  pdfBase64: string;
  filename: string;
  atsScore: number | null;
  onApply: () => void;
  onClose: () => void;
  applying: boolean;
  applyResult: { type: "success" | "error"; msg: string } | null;
}

export default function TailoredCVPreview({ pdfBase64, filename, atsScore, onApply, onClose, applying, applyResult }: TailoredCVPreviewProps) {
  const [viewMode, setViewMode] = useState<"embed" | "download">("embed");

  const pdfUrl = `data:application/pdf;base64,${pdfBase64}`;

  function handleDownload() {
    const a = document.createElement("a");
    a.href = pdfUrl;
    a.download = filename;
    a.click();
  }

  const cls = atsScore != null ? (atsScore >= 70 ? "high" : atsScore >= 40 ? "med" : "low") : "unknown";

  return (
    <div className="tcv-overlay" onClick={onClose}>
      <div className="tcv-modal" onClick={(e) => e.stopPropagation()}>
        <div className="tcv-header">
          <div className="tcv-header-left">
            <h3 className="tcv-title">Tailored Resume Preview</h3>
            {atsScore != null && (
              <span className={"tcv-ats-badge tcv-ats-" + cls}>ATS {atsScore}%</span>
            )}
          </div>
          <div className="tcv-header-right">
            <button className="tcv-btn tcv-btn-secondary" onClick={handleDownload}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Download
            </button>
            <button className="tcv-close" onClick={onClose} title="Close">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        <div className="tcv-view-toggle">
          <button
            className={"tcv-toggle-btn" + (viewMode === "embed" ? " active" : "")}
            onClick={() => setViewMode("embed")}
          >
            Preview
          </button>
          <button
            className={"tcv-toggle-btn" + (viewMode === "download" ? " active" : "")}
            onClick={() => setViewMode("download")}
          >
            Full Page
          </button>
        </div>

        <div className="tcv-preview">
          {viewMode === "embed" ? (
            <iframe src={pdfUrl} className="tcv-embed" title="Resume Preview" />
          ) : (
            <iframe src={pdfUrl} className="tcv-embed-full" title="Resume Full View" />
          )}
        </div>

        {applyResult && (
          <div className={"tcv-alert " + (applyResult.type === "success" ? "tcv-alert-success" : "tcv-alert-error")}>
            {applyResult.msg}
          </div>
        )}

        <div className="tcv-footer">
          <button className="tcv-btn tcv-btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className={"tcv-btn tcv-btn-primary" + (applying ? " loading" : "")}
            onClick={onApply}
            disabled={applying}
          >
            {applying ? (
              <>
                <span className="spinner" /> Sending Application...
              </>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
                Apply with Tailored CV
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
