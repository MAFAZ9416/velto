/**
 * VELTO Conversion — Authentication Context
 * Manages user state, tokens, and auth lifecycle.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { authService } from '../services/auth';
import { tokenStorage } from '../services/api';
import type { User, UserProfile } from '../types';

interface AuthContextValue {
  user: User | null;
  profile: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      if (!tokenStorage.getAccess()) {
        setIsLoading(false);
        return;
      }

      try {
        const userProfile = await authService.getCurrentUser();
        setUser({
          user_id: userProfile.user_id,
          email: userProfile.email,
          is_email_verified: userProfile.is_email_verified,
          date_joined: userProfile.created_at,
        });
        setProfile(userProfile);
      } catch {
        // Token expired or invalid — clear and continue as anonymous
        tokenStorage.clear();
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  // Listen for auth expiry events from the API interceptor
  useEffect(() => {
    const handleExpired = () => {
      setUser(null);
      setProfile(null);
    };
    window.addEventListener('velto:auth:expired', handleExpired);
    return () => window.removeEventListener('velto:auth:expired', handleExpired);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await authService.login(email, password);
    setUser(response.user);

    // Fetch full profile after login
    try {
      const userProfile = await authService.getCurrentUser();
      setProfile(userProfile);
    } catch {
      // Profile fetch failed, user is still set
    }
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    const newUser = await authService.register(email, password);
    return newUser;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setProfile(null);
    }
  }, []);

  const refreshProfile = useCallback(async () => {
    try {
      const userProfile = await authService.getCurrentUser();
      setUser({
        user_id: userProfile.user_id,
        email: userProfile.email,
        is_email_verified: userProfile.is_email_verified,
        date_joined: userProfile.created_at,
      });
      setProfile(userProfile);
    } catch {
      // Ignore — profile refresh is best-effort
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        isAuthenticated,
        isLoading,
        login,
        register,
        logout,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
