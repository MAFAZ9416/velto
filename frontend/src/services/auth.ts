/**
 * VELTO Conversion — Authentication Service
 */

import api, { tokenStorage } from './api';
import type {
  User,
  UserProfile,
  LoginResponse,
  TokenRefreshResponse,
} from '../types';

export const authService = {
  /**
   * POST /api/v1/auth/register/
   */
  async register(email: string, password: string): Promise<User> {
    const { data } = await api.post('/auth/register/', { email, password });
    return data;
  },

  /**
   * POST /api/v1/auth/login/
   */
  async login(email: string, password: string): Promise<LoginResponse> {
    const { data } = await api.post('/auth/login/', { email, password });
    if (data.tokens) {
      tokenStorage.setTokens(data.tokens.access, data.tokens.refresh);
    }
    return data;
  },

  /**
   * POST /api/v1/auth/token/refresh/
   */
  async refreshToken(): Promise<TokenRefreshResponse> {
    const refresh = tokenStorage.getRefresh();
    if (!refresh) throw new Error('No refresh token available');
    const { data } = await api.post('/auth/token/refresh/', { refresh });
    if (data.tokens) {
      tokenStorage.setTokens(data.tokens.access, data.tokens.refresh || refresh);
    }
    return data;
  },

  /**
   * POST /api/v1/auth/logout/
   */
  async logout(): Promise<void> {
    const refresh = tokenStorage.getRefresh();
    try {
      if (refresh) {
        await api.post('/auth/logout/', { refresh });
      }
    } finally {
      tokenStorage.clear();
    }
  },

  /**
   * GET /api/v1/auth/me/
   */
  async getCurrentUser(): Promise<UserProfile> {
    const { data } = await api.get('/auth/me/');
    return data;
  },

  /**
   * DELETE /api/v1/auth/me/
   */
  async deleteAccount(password: string): Promise<void> {
    await api.delete('/auth/me/', { data: { password } });
    tokenStorage.clear();
  },

  /**
   * POST /api/v1/auth/password-reset/request/
   */
  async requestPasswordReset(email: string): Promise<{ message: string }> {
    const { data } = await api.post('/auth/password-reset/request/', { email });
    return data;
  },

  /**
   * POST /api/v1/auth/password-reset/confirm/
   */
  async confirmPasswordReset(
    email: string,
    token: string,
    newPassword: string
  ): Promise<{ message: string }> {
    const { data } = await api.post('/auth/password-reset/confirm/', {
      email,
      token,
      new_password: newPassword,
    });
    return data;
  },

  /**
   * POST /api/v1/auth/email-verification/request/
   */
  async requestEmailVerification(email?: string): Promise<{ message: string }> {
    const { data } = await api.post('/auth/email-verification/request/', {
      ...(email ? { email } : {}),
    });
    return data;
  },

  /**
   * POST /api/v1/auth/email-verification/confirm/
   */
  async confirmEmailVerification(
    email: string,
    token: string
  ): Promise<{ message: string }> {
    const { data } = await api.post('/auth/email-verification/confirm/', {
      email,
      token,
    });
    return data;
  },

  /**
   * Check if user has stored tokens (doesn't verify validity)
   */
  hasStoredTokens(): boolean {
    return !!tokenStorage.getAccess();
  },
};
