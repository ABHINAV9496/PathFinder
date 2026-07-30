export interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  source: string;
  posted_date: string;
  fetched_date: string;
  match_score: number;
  status: string;
  matched_skills: string[];
  salary: number;
  salary_display: string;
  job_url: string;
  uid: string;
  apply_email: string;
  apply_url: string;
}

export interface JobDetail extends Job {
  description: string;
  skill_score_breakdown: Record<string, number>;
  skill_gaps: string[];
  match_explanation: string;
  filter_reason: string;
  search_query: string;
  application: Application | null;
}

export interface Application {
  id: number;
  job: Job;
  sent_at: string;
  status: string;
  email_subject: string;
  cover_letter_text: string;
  error_message: string;
  skills_highlighted: string[];
  skills_in_job_desc: string[];
  skill_match_pct: number;
  criteria_data: Record<string, unknown>;
  skill_gaps: string[];
  match_explanation: string;
}

export interface PaginatedResponse<T> {
  count: number;
  page: number;
  total_pages: number;
  next: boolean;
  previous: boolean;
  results: T[];
}

export interface SecurityStatus {
  sender_email: string;
  has_password: boolean;
  has_credentials: boolean;
}

export interface ResumeStatus {
  has_resume: boolean;
  filename?: string;
  size_kb?: number;
}

export interface ApplyProgress {
  running: boolean;
  total: number;
  done: number;
  succeeded: number;
  failed: number;
  current: string;
}

export interface AIConfig {
  provider: string;
  api_base_url: string;
  model_name: string;
  has_api_key: boolean;
  has_ai_config: boolean;
  presets: Record<string, { name: string; api_base_url: string; model: string }>;
}

export interface ExperienceEntry {
  id: number;
  role: string;
  company: string;
  location: string;
  duration: string;
  type: "full-time" | "part-time" | "internship" | "freelance" | "contract";
  highlights: string[];
  tech: string[];
}

export interface ATSScore {
  score: number | null;
  reason?: string;
}

export interface TailoredCVResponse {
  pdf_base64: string;
  filename: string;
  ats_score?: number;
  summary?: string;
  sections_used?: string[];
}
