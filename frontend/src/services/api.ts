/**
 * VELTO Conversion — Centralized Axios API Client
 *
 * Two instances:
 * - `api`: V1 endpoints (JWT auth, envelope unwrapping)
 * - `legacyApi`: Legacy endpoints (session cookies, raw responses)
 */

import axios, { AxiosError } from 'axios';
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ── Token Storage ─────────────────────────────────────────────────────────────

const TOKEN_KEY = 'velto_access_token';
const REFRESH_KEY = 'velto_refresh_token';

export const tokenStorage = {
  getAccess: (): string | null => localStorage.getItem(TOKEN_KEY),
  getRefresh: (): string | null => localStorage.getItem(REFRESH_KEY),
  setTokens: (access: string, refresh: string) => {
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// ── V1 API Instance (JWT + Envelope) ──────────────────────────────────────────

const api: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

// Attach JWT token to requests
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccess();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Track refresh state to prevent concurrent refreshes
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });
  failedQueue = [];
};

// Response interceptor: unwrap envelope + handle 401
api.interceptors.response.use(
  (response) => {
    // Unwrap V1 envelope: { success, data, error }
    if (response.data && typeof response.data === 'object' && 'success' in response.data) {
      if (response.data.success) {
        response.data = response.data.data;
      } else {
        return Promise.reject(
          normalizeApiError(response.data.error, response.status)
        );
      }
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Handle 401 — attempt token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = tokenStorage.getRefresh();

      if (!refreshToken) {
        tokenStorage.clear();
        window.dispatchEvent(new CustomEvent('velto:auth:expired'));
        return Promise.reject(normalizeApiError(error.response?.data, 401));
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              resolve(api(originalRequest));
            },
            reject,
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await axios.post(`${BASE_URL}/api/v1/auth/token/refresh/`, {
          refresh: refreshToken,
        });

        const responseData = data?.data || data;
        const newAccess = responseData.tokens?.access;
        const newRefresh = responseData.tokens?.refresh;

        if (newAccess) {
          tokenStorage.setTokens(newAccess, newRefresh || refreshToken);
          processQueue(null, newAccess);
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newAccess}`;
          }
          return api(originalRequest);
        }

        throw new Error('No access token in refresh response');
      } catch (refreshError) {
        processQueue(refreshError, null);
        tokenStorage.clear();
        window.dispatchEvent(new CustomEvent('velto:auth:expired'));
        return Promise.reject(normalizeApiError(null, 401));
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(
      normalizeApiError(error.response?.data, error.response?.status || 500)
    );
  }
);

// ── Legacy API Instance (Session cookies, no envelope) ────────────────────────

const legacyApi: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api`,
  withCredentials: true,
});

// Also attach JWT for legacy routes if user is logged in
legacyApi.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccess();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

legacyApi.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    return Promise.reject(
      normalizeApiError(error.response?.data, error.response?.status || 500)
    );
  }
);

// ── Error Normalization ───────────────────────────────────────────────────────

export interface NormalizedError {
  status: number;
  code: string;
  message: string;
  details: Record<string, unknown>;
  requestId?: string;
}

function normalizeApiError(
  data: unknown,
  status: number = 500
): NormalizedError {
  // V1 envelope error format
  if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>;

    // { success: false, error: { code, message, details, request_id } }
    if (obj.error && typeof obj.error === 'object') {
      const err = obj.error as Record<string, unknown>;
      return {
        status,
        code: (err.code as string) || 'UNKNOWN_ERROR',
        message: (err.message as string) || getDefaultMessage(status),
        details: (err.details as Record<string, unknown>) || {},
        requestId: err.request_id as string | undefined,
      };
    }

    // { detail: "..." } (DRF standard)
    if (typeof obj.detail === 'string') {
      return {
        status,
        code: 'API_ERROR',
        message: obj.detail,
        details: {},
      };
    }

    // { message: "..." }
    if (typeof obj.message === 'string') {
      return {
        status,
        code: 'API_ERROR',
        message: obj.message,
        details: {},
      };
    }

    // Validation errors: { field: ["error1", "error2"] }
    const fieldErrors: Record<string, unknown> = {};
    let hasFieldErrors = false;
    for (const [key, value] of Object.entries(obj)) {
      if (Array.isArray(value) && value.every((v) => typeof v === 'string')) {
        fieldErrors[key] = value;
        hasFieldErrors = true;
      }
    }
    if (hasFieldErrors) {
      const firstField = Object.keys(fieldErrors)[0];
      const firstError = (fieldErrors[firstField] as string[])[0];
      return {
        status,
        code: 'VALIDATION_ERROR',
        message: firstError || 'Validation failed.',
        details: fieldErrors,
      };
    }
  }

  return {
    status,
    code: 'UNKNOWN_ERROR',
    message: getDefaultMessage(status),
    details: {},
  };
}

function getDefaultMessage(status: number): string {
  switch (status) {
    case 400:
      return 'Invalid request. Please check your input.';
    case 401:
      return 'Your session has expired. Please log in again.';
    case 403:
      return 'You do not have permission to perform this action.';
    case 404:
      return 'The requested resource was not found.';
    case 409:
      return 'A conflict occurred. Please try again.';
    case 422:
      return 'The request could not be processed.';
    case 429:
      return 'Too many requests. Please wait before trying again.';
    case 500:
      return 'An unexpected error occurred. Please try again later.';
    default:
      return 'Something went wrong. Please try again.';
  }
}

export { api, legacyApi };
export default api;
