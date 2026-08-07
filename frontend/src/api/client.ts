import type { PaginatedResponse, Job, JobDetail, ApplicationListResponse, SecurityStatus, ResumeStatus, ApplyProgress, AIConfig, ATSScore, FilterOptions } from "../types";

const BASE = "/api/v1";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  jobs: {
    list(params: Record<string, string> = {}): Promise<PaginatedResponse<Job>> {
      const qs = new URLSearchParams(params).toString();
      return get(`/jobs/${qs ? `?${qs}` : ""}`);
    },
    filters(): Promise<FilterOptions> {
      return get("/jobs/filters/");
    },
    detail(id: number): Promise<JobDetail> {
      return get(`/jobs/${id}/`);
    },
    apply(id: number, coverLetterText?: string): Promise<Record<string, unknown>> {
      const body = coverLetterText ? JSON.stringify({ cover_letter_text: coverLetterText }) : undefined;
      return fetch(`${BASE}/jobs/${id}/apply/`, {
        method: "POST",
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body,
      }).then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      });
    },
    generateCoverLetter(id: number): Promise<{ cover_letter: string }> {
      return fetch(`${BASE}/jobs/${id}/generate-cover-letter/`, { method: "POST" }).then((r) => {
        if (!r.ok) return r.json().then((d) => { throw new Error(d.detail || d.error || `API error: ${r.status}`); });
        return r.json();
      });
    },
    generateTemplateCoverLetter(id: number): Promise<{ cover_letter: string; template: string }> {
      return fetch(`${BASE}/jobs/${id}/generate-template-cover-letter/`, { method: "POST" }).then((r) => {
        if (!r.ok) return r.json().then((d) => { throw new Error(d.detail || d.error || `API error: ${r.status}`); });
        return r.json();
      });
    },
    atsScore(id: number): Promise<ATSScore> {
      return get(`/jobs/${id}/ats-score/`);
    },
    generateCV(id: number): Promise<{ pdf_base64: string; filename: string }> {
      return fetch(`${BASE}/jobs/${id}/generate-cv/`, { method: "POST" }).then((r) => {
        if (!r.ok) return r.json().then((d) => { throw new Error(d.detail || d.error || `API error: ${r.status}`); });
        return r.json();
      });
    },
    tailoredApply(id: number, resumePdfBase64: string, coverLetterText?: string): Promise<{ success: boolean; message: string }> {
      return fetch(`${BASE}/jobs/${id}/tailored-apply/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_pdf_base64: resumePdfBase64,
          ...(coverLetterText ? { cover_letter_text: coverLetterText } : {}),
        }),
      }).then((r) => {
        if (!r.ok) return r.json().then((d) => { throw new Error(d.detail || d.error || `API error: ${r.status}`); });
        return r.json();
      });
    },

  },
  applications: {
    list(params: Record<string, string> = {}): Promise<ApplicationListResponse> {
      const qs = new URLSearchParams(params).toString();
      return get(`/applications/${qs ? `?${qs}` : ""}`);
    },
  },
  applyQueue: {
    list(params: Record<string, string> = {}): Promise<PaginatedResponse<Job>> {
      const qs = new URLSearchParams(params).toString();
      return get(`/apply-queue/${qs ? `?${qs}` : ""}`);
    },
    applyBatch(jobIds: number[]): Promise<Record<string, unknown>> {
      return fetch(`${BASE}/apply-queue/batch/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_ids: jobIds }),
      }).then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      });
    },
    progress(): Promise<ApplyProgress> {
      return get("/apply-queue/progress/");
    },
  },
  stats: {
    overview(params: Record<string, string> = {}): Promise<Record<string, unknown>> {
      const qs = new URLSearchParams(params).toString();
      return get(`/stats/overview/${qs ? `?${qs}` : ""}`);
    },
    skills(): Promise<Record<string, unknown>> {
      return get("/stats/skills/");
    },
    companies(): Promise<Record<string, unknown>> {
      return get("/stats/companies/");
    },
    locations(): Promise<Record<string, unknown>> {
      return get("/stats/locations/");
    },
  },
  profile: {
    get(): Promise<Record<string, unknown>> {
      return get("/profile/");
    },
    update(data: Record<string, unknown>): Promise<Record<string, unknown>> {
      return fetch(`${BASE}/profile/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: data }),
      }).then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      });
    },
    uploadResume(file: File): Promise<Record<string, unknown>> {
      const form = new FormData();
      form.append("resume", file);
      return fetch(`${BASE}/profile/resume/`, {
        method: "POST",
        body: form,
      }).then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      });
    },
    deleteResume(): Promise<Record<string, unknown>> {
      return fetch(`${BASE}/profile/resume/`, { method: "DELETE" }).then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      });
    },
    getResume(): Promise<ResumeStatus> {
      return get("/profile/resume/");
    },
    getSecurity(): Promise<SecurityStatus> {
      return get("/profile/security/");
    },
    saveSecurity(senderEmail: string, password: string): Promise<Record<string, unknown>> {
      return fetch(`${BASE}/profile/security/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sender_email: senderEmail, password }),
      }).then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      });
    },
    deleteSecurity(): Promise<Record<string, unknown>> {
      return fetch(`${BASE}/profile/security/`, { method: "DELETE" }).then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      });
    },
    getAI(): Promise<AIConfig> {
      return get("/profile/ai/");
    },
    saveAI(data: { provider: string; api_base_url: string; model_name: string; api_key: string }): Promise<Record<string, unknown>> {
      return fetch(`${BASE}/profile/ai/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }).then((r) => {
        if (!r.ok) return r.json().then((d) => { throw new Error(d.detail || d.error || `API error: ${r.status}`); });
        return r.json();
      });
    },
    deleteAI(): Promise<Record<string, unknown>> {
      return fetch(`${BASE}/profile/ai/`, { method: "DELETE" }).then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      });
    },
  },
  webApply: {
    list(params: Record<string, string> = {}): Promise<Record<string, unknown>> {
      const qs = new URLSearchParams(params).toString();
      return get(`/web-apply/${qs ? `?${qs}` : ""}`);
    },
  },
  missingEmails: {
    list(params: Record<string, string> = {}): Promise<Record<string, unknown>> {
      const qs = new URLSearchParams(params).toString();
      return get(`/missing-emails/${qs ? `?${qs}` : ""}`);
    },
  },
  fetcher: {
    run(): Promise<Record<string, unknown>> {
      return fetch(`${BASE}/fetcher/run/`, { method: "POST" }).then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      });
    },
    status(): Promise<Record<string, unknown>> {
      return get("/fetcher/status/");
    },
  },
};
