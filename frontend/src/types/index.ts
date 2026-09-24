/**
 * VELTO Conversion — TypeScript Type Definitions
 * Matches the Django REST Framework API contract.
 */

// ── Auth Types ────────────────────────────────────────────────────────────────

export interface User {
  user_id: string;
  email: string;
  is_email_verified: boolean;
  date_joined: string;
}

export interface UserProfile {
  user_id: string;
  email: string;
  is_email_verified: boolean;
  account_status: 'active' | 'inactive';
  storage_limit_bytes: number;
  storage_used_bytes: number;
  daily_conversion_count: number;
  daily_conversion_limit: number;
  monthly_conversion_count: number;
  monthly_conversion_limit: number;
  created_at: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginResponse {
  tokens: AuthTokens;
  user: User;
}

export interface TokenRefreshResponse {
  tokens: AuthTokens;
}

// ── Conversion Types ──────────────────────────────────────────────────────────

export type JobStatus =
  | 'pending'
  | 'queued'
  | 'started'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'retrying'
  | 'cancel_requested'
  | 'cancelled'
  | 'expired';

export interface ConversionJob {
  id: string;
  source_format: string;
  source_format_label: string;
  target_format: string;
  target_format_label: string;
  status: JobStatus;
  status_label: string;
  original_filename: string;
  file_size_bytes: number | null;
  options: Record<string, unknown>;
  progress: number;
  current_stage: string;
  stage_message: string;
  error_code: string;
  retry_count: number;
  max_retries: number;
  celery_task_id: string;
  worker_name: string;
  storage_backend: string;
  is_finalized: boolean;
  output_filename: string;
  output_size_bytes: number | null;
  download_url: string | null;
  download_available: boolean;
  cancellation_available: boolean;
  retry_available: boolean;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  cancelled_at: string | null;
  expires_at: string | null;
  error_message: string;
}

export interface SupportedFormat {
  source: string;
  target: string;
  source_label: string;
  target_label: string;
  category: 'document' | 'image';
  enabled: boolean;
  mime_types: string[];
  max_file_size: number;
  restrictions: {
    max_pdf_pages: number | null;
  };
}

export interface SupportedFormatsResponse {
  count: number;
  formats: SupportedFormat[];
}

// ── Pagination ────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  count: number;
  page: number;
  page_size: number;
  results: T[];
}

export interface ListResponse<T> {
  count: number;
  results: T[];
}

// ── API Envelope (V1 routes) ──────────────────────────────────────────────────

export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  error: ApiError | null;
}

export interface ApiError {
  code: string;
  message: string;
  details: Record<string, unknown>;
  request_id: string;
}

// ── Retry Response ────────────────────────────────────────────────────────────

export interface RetryResponse {
  original_job_id: string;
  new_job_id: string;
  status: string;
  message: string;
  job: ConversionJob;
}

// ── PDF Utility Types ─────────────────────────────────────────────────────────

export type PdfOperation =
  | 'pdf_merge'
  | 'pdf_split'
  | 'pdf_extract_pages'
  | 'pdf_rotate'
  | 'pdf_compress'
  | 'pdf_watermark'
  | 'pdf_protect'
  | 'pdf_unlock'
  | 'pdf_metadata'
  | 'pdf_page_numbers'
  | 'pdf_repair';

export type OcrOperation =
  | 'ocr_image_to_searchable_pdf'
  | 'ocr_image_to_txt'
  | 'ocr_pdf_to_txt'
  | 'ocr_scanned_pdf_to_searchable_pdf';

// ── Tool Card Types ───────────────────────────────────────────────────────────

export interface ToolInfo {
  id: string;
  name: string;
  description: string;
  category: 'document' | 'image' | 'pdf' | 'ocr';
  icon: string;
  sourceFormat: string;
  targetFormat: string;
  operation?: PdfOperation | OcrOperation;
  options?: Record<string, unknown>;
}

// ── Guest Conversion ──────────────────────────────────────────────────────────

export interface GuestConversionState {
  remaining: number;
  lastResetDate: string;
}

// ── Format Helpers ────────────────────────────────────────────────────────────

export const FORMAT_LABELS: Record<string, string> = {
  pdf: 'PDF',
  docx: 'Word (DOCX)',
  xlsx: 'Excel (XLSX)',
  pptx: 'PowerPoint (PPTX)',
  jpg: 'JPG Image',
  png: 'PNG Image',
  csv: 'CSV',
  webp: 'WebP Image',
  bmp: 'BMP Image',
  tiff: 'TIFF Image',
  gif: 'GIF Image',
  zip: 'ZIP Archive',
  txt: 'Text (TXT)',
  html: 'HTML',
  md: 'Markdown',
};

export const FORMAT_EXTENSIONS: Record<string, string[]> = {
  pdf: ['.pdf'],
  docx: ['.docx', '.doc'],
  xlsx: ['.xlsx', '.xls'],
  pptx: ['.pptx', '.ppt'],
  jpg: ['.jpg', '.jpeg'],
  png: ['.png'],
  csv: ['.csv'],
  webp: ['.webp'],
  bmp: ['.bmp'],
  tiff: ['.tiff', '.tif'],
  gif: ['.gif'],
  zip: ['.zip'],
  txt: ['.txt'],
  html: ['.html', '.htm'],
  md: ['.md', '.markdown'],
};
