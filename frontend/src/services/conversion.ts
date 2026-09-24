/**
 * VELTO Conversion — Conversion Service
 * Handles both authenticated (V1) and guest (legacy) conversion operations.
 */

import api, { legacyApi } from './api';
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
   */
  async getJobStatus(jobId: string): Promise<ConversionJob> {
    const { data } = await api.get(`/conversions/${jobId}/`);
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
   * GET /api/v1/conversions/{id}/download/ (stream file)
   */
  getDownloadUrl(jobId: string): string {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    return `${baseUrl}/api/v1/conversions/${jobId}/download/`;
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
   * Download a completed job's file (handles both direct and presigned)
   */
  async downloadFile(jobId: string): Promise<void> {
    try {
      const { download_url } = await this.getPresignedDownloadUrl(jobId);
      window.open(download_url, '_blank');
    } catch {
      // Fallback to direct download
      const url = this.getDownloadUrl(jobId);
      const link = document.createElement('a');
      link.href = url;
      link.download = '';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  },
};
