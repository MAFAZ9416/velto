/**
 * VELTO — Reset Password Page
 */

import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Check, Zap } from 'lucide-react';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import { PasswordStrength } from '../../components/ui/index';
import { authService } from '../../services/auth';
import type { NormalizedError } from '../../services/api';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const email = searchParams.get('email') || '';

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!password || password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (password !== confirmPassword) { setError('Passwords do not match.'); return; }
    if (!token || !email) { setError('Invalid reset link. Please request a new one.'); return; }

    setIsLoading(true);
    try {
      await authService.confirmPasswordReset(email, token, password);
      setSuccess(true);
    } catch (err) {
      const apiError = err as NormalizedError;
      setError(apiError.message || 'Failed to reset password.');
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

        {success ? (
          <div className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-6">
              <Check className="h-8 w-8 text-emerald-400" />
            </div>
            <h1 className="text-2xl font-bold text-velto-ivory mb-3">Password reset</h1>
            <p className="text-velto-muted mb-8">Your password has been successfully reset. You can now log in with your new password.</p>
            <Link to="/login"><Button variant="primary">Continue to Login<ArrowRight className="h-4 w-4 ml-1" /></Button></Link>
          </div>
        ) : (
          <>
            <h1 className="text-2xl sm:text-3xl font-bold text-velto-ivory mb-2">Reset your password</h1>
            <p className="text-velto-muted mb-8">Enter your new password below.</p>

            {error && (
              <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-1.5">
                <Input label="New Password" type="password" placeholder="Create a strong password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
                <PasswordStrength password={password} />
              </div>
              <Input label="Confirm Password" type="password" placeholder="Confirm your password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} autoComplete="new-password" />
              <Button type="submit" variant="primary" size="lg" fullWidth loading={isLoading} iconRight={<ArrowRight className="h-4 w-4" />}>Reset Password</Button>
            </form>
          </>
        )}
      </motion.div>
    </div>
  );
}
