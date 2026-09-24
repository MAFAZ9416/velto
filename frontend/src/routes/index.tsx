/**
 * VELTO Conversion — Route Definitions
 * Lazy-loaded pages with protected/public route wrappers.
 */

import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import PageLoader from '../components/ui/PageLoader';

// Lazy-loaded pages
const HomePage = lazy(() => import('../pages/public/HomePage'));
const ProcessingPage = lazy(() => import('../pages/public/ProcessingPage'));
const ResultPage = lazy(() => import('../pages/public/ResultPage'));
const PricingPage = lazy(() => import('../pages/public/PricingPage'));
const LoginPage = lazy(() => import('../pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('../pages/auth/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('../pages/auth/ForgotPasswordPage'));
const ResetPasswordPage = lazy(() => import('../pages/auth/ResetPasswordPage'));
const VerifyEmailPage = lazy(() => import('../pages/auth/VerifyEmailPage'));
const DashboardPage = lazy(() => import('../pages/dashboard/DashboardPage'));
const ConvertPage = lazy(() => import('../pages/converter/ConvertPage'));
const ConversionsPage = lazy(() => import('../pages/converter/ConversionsPage'));
const ToolsPage = lazy(() => import('../pages/tools/ToolsPage'));
const ToolDetailPage = lazy(() => import('../pages/tools/ToolDetailPage'));
const AccountPage = lazy(() => import('../pages/account/AccountPage'));
const SettingsPage = lazy(() => import('../pages/settings/SettingsPage'));
const NotFoundPage = lazy(() => import('../pages/errors/NotFoundPage'));
const ForbiddenPage = lazy(() => import('../pages/errors/ForbiddenPage'));
const ServerErrorPage = lazy(() => import('../pages/errors/ServerErrorPage'));

// Route guard for authenticated-only pages
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <PageLoader />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return <>{children}</>;
}

// Route guard for guest-only pages (redirect logged-in users)
function GuestRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <PageLoader />;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  return <>{children}</>;
}

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<HomePage />} />
          <Route path="/convert/processing" element={<ProcessingPage />} />
          <Route path="/convert/result/:id" element={<ResultPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/tools" element={<ToolsPage />} />
          <Route path="/tools/:tool" element={<ToolDetailPage />} />

          {/* Auth routes (guest only) */}
          <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
          <Route path="/register" element={<GuestRoute><RegisterPage /></GuestRoute>} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />

          {/* Protected routes */}
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/convert" element={<ProtectedRoute><ConvertPage /></ProtectedRoute>} />
          <Route path="/conversions" element={<ProtectedRoute><ConversionsPage /></ProtectedRoute>} />
          <Route path="/account" element={<ProtectedRoute><AccountPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />

          {/* Error pages */}
          <Route path="/403" element={<ForbiddenPage />} />
          <Route path="/500" element={<ServerErrorPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
