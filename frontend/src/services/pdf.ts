/**
 * VELTO Conversion — PDF & OCR Utilities Service
 */

import api from './api';
import type { ConversionJob } from '../types';

export const pdfService = {
  /**
   * POST /api/v1/pdf/utilities/
   */
  async executePdfOperation(
    operation: string,
    file: File | null,
    files: File[] | null,
    options?: Record<string, unknown>
  ): Promise<ConversionJob> {
    const formData = new FormData();
    formData.append('operation', operation);

    if (files && files.length > 0) {
      files.forEach((f) => formData.append('files', f));
    } else if (file) {
      formData.append('file', file);
    }

    if (options) {
      Object.entries(options).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          formData.append(key, String(value));
        }
      });
    }

    const { data } = await api.post('/pdf/utilities/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  /**
   * POST /api/v1/conversions/ocr/
   */
  async executeOcrOperation(
    operation: string,
    file: File,
    sourceFormat: string,
    targetFormat: string
  ): Promise<ConversionJob> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_format', sourceFormat);
    formData.append('target_format', targetFormat);
    formData.append('options', JSON.stringify({ operation }));

    const { data } = await api.post('/conversions/ocr/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
};
