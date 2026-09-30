/**
 * VELTO Conversion — Conversion Service
 * Handles both authenticated (V1) and guest (legacy) conversion operations.
 */

import api, { legacyApi, tokenStorage } from './api';
import type {
  ConversionJob,
  SupportedFormatsResponse,
  PaginatedResponse,
  ListResponse,
} from '../types';

export interface HistoryParams {
  status?: string;
  source_format?: string;
  target_format?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export const conversionService = {
  /**
   * GET /api/v1/conversions/formats/ (no auth required)
   */
  async getSupportedFormats(): Promise<SupportedFormatsResponse> {
    const { data } = await api.get('/conversions/formats/');
    return data;
  },

  /**
   * POST /api/v1/conversions/ (authenticated)
   * Upload file and create conversion job.
   */
  async createJob(
    file: File,
    sourceFormat: string,
    targetFormat: string,
    options?: Record<string, unknown>
  ): Promise<ConversionJob> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_format', sourceFormat);
    formData.append('target_format', targetFormat);
    if (options) {
      formData.append('options', JSON.stringify(options));
    }

    const { data } = await api.post('/conversions/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  /**
   * POST /api/conversions/ (legacy — session-based, for guests)
   */
  async createGuestJob(
    file: File,
    sourceFormat: string,
    targetFormat: string,
    options?: Record<string, unknown>
  ): Promise<ConversionJob> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_format', sourceFormat);
    formData.append('target_format', targetFormat);
    if (options) {
      formData.append('options', JSON.stringify(options));
    }

    const { data } = await legacyApi.post('/conversions/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  /**
   * GET /api/v1/conversions/{id}/ (authenticated)
   * or GET /api/conversions/{id}/ (guest/session) depending on auth state.
   */
  async getJobStatus(jobId: string): Promise<ConversionJob> {
    const client = tokenStorage.getAccess() ? api : legacyApi;
    const { data } = await client.get(`/conversions/${jobId}/`);
    return data;
  },

  /**
   * GET /api/v1/conversions/ (authenticated)
   */
  async listJobs(): Promise<ListResponse<ConversionJob>> {
    const { data } = await api.get('/conversions/');
    return data;
  },

  /**
   * GET /api/v1/conversions/history/ (authenticated, paginated)
   */
  async getHistory(
    params?: HistoryParams
  ): Promise<PaginatedResponse<ConversionJob>> {
    const { data } = await api.get('/conversions/history/', { params });
    return data;
  },

  /**
   * GET /api/history/ (legacy — session-based, for guests)
   */
  async getGuestHistory(): Promise<ListResponse<ConversionJob>> {
    const { data } = await legacyApi.get('/history/');
    return data;
  },

  /**
   * POST /api/v1/conversions/{id}/cancel/
   */
  async cancelJob(
    jobId: string
  ): Promise<{ message: string; job: ConversionJob }> {
    const { data } = await api.post(`/conversions/${jobId}/cancel/`);
    return data;
  },

  /**
   * POST /api/v1/conversions/{id}/retry/
   */
  async retryJob(jobId: string): Promise<ConversionJob> {
    const { data } = await api.post(`/conversions/${jobId}/retry/`);
    return data.job || data;
  },

  /**
   * DELETE /api/v1/conversions/{id}/
   */
  async deleteJob(jobId: string): Promise<void> {
    await api.delete(`/conversions/${jobId}/`);
  },

  /**
   * GET /api/v1/conversions/{id}/download/ (authenticated)
   * or GET /api/conversions/{id}/download/ (guest/session)
   */
  getDownloadUrl(jobId: string): string {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const apiRoot = tokenStorage.getAccess() ? `${baseUrl}/api/v1` : `${baseUrl}/api`;
    return `${apiRoot}/conversions/${jobId}/download/`;
  },

  /**
   * GET /api/v1/conversions/{id}/download-url/ (presigned URL)
   */
  async getPresignedDownloadUrl(
    jobId: string
  ): Promise<{ download_url: string; expires_in: number; filename: string }> {
    const { data } = await api.get(`/conversions/${jobId}/download-url/`);
    return data;
  },

  /**
   * Download a completed job's file through the real backend download endpoint.
   * This honors auth/session ownership and avoids fake or malformed URLs.
   */
  async downloadFile(jobId: string): Promise<void> {
    const client = tokenStorage.getAccess() ? api : legacyApi;
    const url = this.getDownloadUrl(jobId);

    try {
      const response = await client.get(url, { responseType: 'blob' });
      const contentDisposition = response.headers['content-disposition'] as string | undefined;
      const rawContentType = response.headers['content-type'];
      const contentType = Array.isArray(rawContentType) ? rawContentType[0] : rawContentType;
      const normalizedContentType = typeof contentType === 'string' && contentType ? contentType : undefined;
      const blob = new Blob([response.data as BlobPart], {
        type: normalizedContentType || 'application/octet-stream',
      });
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = this.parseDownloadFilename(contentDisposition, jobId, normalizedContentType);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Failed to download conversion output:', error);
      const fallbackUrl = this.getDownloadUrl(jobId);
      const link = document.createElement('a');
      link.href = fallbackUrl;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  },

  parseDownloadFilename(contentDisposition?: string, fallbackJobId?: string, contentType?: string): string {
    const resolvedContentType = typeof contentType === 'string' ? contentType.toLowerCase() : '';
    const defaultExtension = this.getExtensionFromContentType(resolvedContentType) || '.bin';

    if (!contentDisposition) {
      return fallbackJobId ? `converted-${fallbackJobId}${defaultExtension}` : `download${defaultExtension}`;
    }

    const utf8Match = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
    if (utf8Match?.[1]) {
      const decoded = decodeURIComponent(utf8Match[1].trim());
      if (decoded) {
        return decoded;
      }
    }

    const normalMatch = contentDisposition.match(/filename\s*=\s*"?([^";]+)"?/i);
    if (normalMatch?.[1]) {
      const fileName = normalMatch[1].trim();
      if (fileName) {
        return fileName;
      }
    }

    return fallbackJobId ? `converted-${fallbackJobId}${defaultExtension}` : `download${defaultExtension}`;
  },

  getExtensionFromContentType(contentType?: string): string {
    if (!contentType) {
      return '';
    }

    const mimeMap: Record<string, string> = {
      'application/pdf': '.pdf',
      'application/zip': '.zip',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
      'image/jpeg': '.jpg',
      'image/png': '.png',
      'text/plain': '.txt',
      'text/html': '.html',
      'application/xhtml+xml': '.html',
      'application/json': '.json',
      'application/xml': '.xml',
    };

    return mimeMap[contentType] || '';
  },
};
