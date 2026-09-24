/**
 * VELTO — Forgot Password Page
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, ArrowRight, Mail, Zap } from 'lucide-react';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import { authService } from '../../services/auth';
import type { NormalizedError } from '../../services/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email.trim()) { setError('Please enter your email address.'); return; }

    setIsLoading(true);
    try {
      await authService.requestPasswordReset(email.trim().toLowerCase());
      setSent(true);
    } catch (err) {
      const apiError = err as NormalizedError;
      setError(apiError.message || 'Failed to send reset link.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-velto-black flex items-center justify-center p-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <Link to="/" className="flex items-center gap-2 mb-10">
          <div className="h-8 w-8 rounded-lg velto-gold-gradient flex items-center justify-center">
            <Zap className="h-4 w-4 text-velto-black" />
          </div>
          <span className="text-lg font-bold tracking-wide text-velto-ivory">VELTO</span>
        </Link>

        {sent ? (
          <div className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-velto-gold/10 flex items-center justify-center mb-6">
              <Mail className="h-8 w-8 text-velto-gold" />
            </div>
            <h1 className="text-2xl font-bold text-velto-ivory mb-3">Check your email</h1>
            <p className="text-velto-muted mb-8">
              If an account exists for <span className="text-velto-ivory font-medium">{email}</span>, we've sent a password reset link.
            </p>
            <Link to="/login">
              <Button variant="secondary">
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back to Login
              </Button>
            </Link>
          </div>
        ) : (
          <>
            <h1 className="text-2xl sm:text-3xl font-bold text-velto-ivory mb-2">Forgot password?</h1>
            <p className="text-velto-muted mb-8">Enter your email and we'll send you a reset link.</p>

            {error && (
              <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <Input
                label="Email Address"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
              />
              <Button type="submit" variant="primary" size="lg" fullWidth loading={isLoading} iconRight={<ArrowRight className="h-4 w-4" />}>
                Send Reset Link
              </Button>
            </form>

            <p className="mt-6 text-center text-sm text-velto-muted">
              <Link to="/login" className="text-velto-gold hover:text-velto-gold-light font-medium flex items-center justify-center gap-1">
                <ArrowLeft className="h-3.5 w-3.5" />
                Back to Login
              </Link>
            </p>
          </>
        )}
      </motion.div>
    </div>
  );
}
