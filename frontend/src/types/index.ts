// frontend/src/types/index.ts
// Shared TypeScript types that mirror backend Pydantic schemas.
// Keep in sync with backend/schemas/*.py

// ── Enums ─────────────────────────────────────────────────────────────────────

export type UserRole = 'SUPER_ADMIN' | 'ADMIN' | 'REVIEWER' | 'ANNOTATOR' | 'PLATFORM';

export type AudioStatus =
  | 'UNASSIGNED'
  | 'ASSIGNED'
  | 'IN_PROGRESS'
  | 'SUBMITTED'
  | 'REVIEWED';

export type AnnotationState = 'DRAFT' | 'SUBMITTED' | 'RETURNED' | 'APPROVED';

export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

// ── Core Entities ─────────────────────────────────────────────────────────────

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
  last_seen: string | null;
}

export interface Dataset {
  id: string;
  name: string;
  zip_filename: string;
  language: string;
  uploaded_by: string;
  total_files: number;
  total_duration: number;
  total_size: number;
  uploaded_at: string;
}

export interface AudioFile {
  id: string;
  dataset_id: string;
  filename: string;
  original_filename: string;
  file_path: string;
  audio_url?: string;        // Phase 3+: Supabase Storage URL
  language: string;
  original_transcript: string | null;
  english_translation: string | null;
  metadata_json: string | null;
  duration: number;
  status: AudioStatus;
  uploaded_by: string | null;
  assigned_to: string | null;
  uploaded_at: string;
}

export interface Annotation {
  id: string;
  audio_id: string;
  annotator_id: string;
  transcript: string | null;
  rsml_content: string | null;
  state: AnnotationState;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnnotationVersion {
  id: string;
  annotation_id: string;
  version_number: number;
  transcript_snapshot: string | null;
  rsml_snapshot: string | null;
  submitted_by: string;
  submitted_at: string;
}

export interface ReviewComment {
  id: string;
  annotation_id: string;
  reviewer_id: string;
  version_commented: number;
  span_start: number | null;
  span_end: number | null;
  comment: string;
  is_return_reason: boolean;
  created_at: string;
}

export interface ReviewerApproval {
  id: string;
  annotation_id: string;
  reviewer_id: string;
  version_approved: number;
  status: ApprovalStatus;
  is_valid: boolean;
  created_at: string;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthTokens {
  access_token: string;
  token_type: string;
  expires_in: number;  // seconds
}

export interface LoginRequest {
  username: string;
  password: string;
}

// ── API Response Wrappers ─────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface KpiSummary {
  total_users: number;
  total_annotators: number;
  total_reviewers: number;
  total_audio: number;
  total_duration: number;
  approved_count: number;
  submitted_count: number;
  returned_count: number;
  draft_count: number;
  approved_duration: number;
  approved_pct: number;
}

// ── Task Locking (Phase 7) ────────────────────────────────────────────────────

export interface TaskLockStatus {
  is_locked: boolean;
  locked_by?: string;
  locked_by_username?: string;
  expires_at?: string;
  is_my_lock?: boolean;
}
