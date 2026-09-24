/**
 * VELTO — Registration Page
 * Premium split-panel registration with gold accents.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, FileText, Image, Zap, Shield, Mail } from 'lucide-react';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import { PasswordStrength } from '../../components/ui/index';
import { useAuth } from '../../context/AuthContext';
import type { NormalizedError } from '../../services/api';

export default function RegisterPage() {
  const { register } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [success, setSuccess] = useState(false);

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (!email.trim()) errors.email = 'Email is required.';
    if (!password) errors.password = 'Password is required.';
    else if (password.length < 8) errors.password = 'Password must be at least 8 characters.';
    if (password !== confirmPassword) errors.confirmPassword = 'Passwords do not match.';
    if (!agreedToTerms) errors.terms = 'You must agree to the terms and privacy policy.';
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!validate()) return;

    setIsLoading(true);
    try {
      await register(email.trim().toLowerCase(), password);
      setSuccess(true);
    } catch (err) {
      const apiError = err as NormalizedError;
      if (apiError.details && typeof apiError.details === 'object') {
        const newFieldErrors: Record<string, string> = {};
        for (const [key, value] of Object.entries(apiError.details)) {
          if (Array.isArray(value)) {
            newFieldErrors[key] = value[0];
          }
        }
        if (Object.keys(newFieldErrors).length > 0) {
          setFieldErrors(newFieldErrors);
        } else {
          setError(apiError.message);
        }
      } else {
        setError(apiError.message || 'Registration failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-velto-black flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-md w-full text-center"
        >
          <div className="mx-auto w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-6">
            <Mail className="h-8 w-8 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-velto-ivory mb-3">Check your email</h1>
          <p className="text-velto-muted mb-8">
            We've sent a verification link to <span className="text-velto-ivory font-medium">{email}</span>.
            Please verify your email to complete your registration.
          </p>
          <Link to="/login">
            <Button variant="primary">
              Continue to Login
              <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </Link>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-velto-black flex">
      {/* Left decorative panel — desktop only */}
      <div className="hidden lg:flex lg:w-1/2 xl:w-[45%] relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-velto-black via-velto-surface to-velto-black-2" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_30%_40%,rgba(212,175,55,0.06)_0%,transparent_70%)]" />
        
        <div className="relative z-10 flex flex-col justify-center px-12 xl:px-16">
          <Link to="/" className="flex items-center gap-2 mb-16">
            <div className="h-10 w-10 rounded-xl velto-gold-gradient flex items-center justify-center">
              <Zap className="h-5 w-5 text-velto-black" />
            </div>
            <span className="text-2xl font-bold tracking-wide text-velto-ivory">VELTO</span>
          </Link>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <h2 className="text-3xl xl:text-4xl font-bold text-velto-ivory leading-tight mb-4">
              Convert anything.
              <br />
              <span className="velto-gold-text">Into possibilities.</span>
            </h2>
            <p className="text-velto-muted text-lg mb-12">
              Fast, secure, and effortless file conversion.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="space-y-5"
          >
            {[
              { icon: FileText, text: 'PDF, DOCX, XLSX, PPTX and 15+ formats' },
              { icon: Image, text: 'Image conversion & optimization' },
              { icon: Shield, text: 'Enterprise-grade security & encryption' },
            ].map(({ icon: Icon, text }, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-velto-gold/10 flex items-center justify-center flex-shrink-0">
                  <Icon className="h-4 w-4 text-velto-gold" />
                </div>
                <span className="text-velto-text text-sm">{text}</span>
              </div>
            ))}
          </motion.div>
        </div>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <Link to="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg velto-gold-gradient flex items-center justify-center">
                <Zap className="h-4 w-4 text-velto-black" />
              </div>
              <span className="text-lg font-bold tracking-wide text-velto-ivory">VELTO</span>
            </Link>
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold text-velto-ivory mb-2">
            Create your VELTO account
          </h1>
          <p className="text-velto-muted mb-8">
            Join VELTO and convert smarter.
          </p>

          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <Input
              label="Full Name"
              type="text"
              placeholder="Your name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              hint="Optional — for personalizing your experience"
            />

            <Input
              label="Email Address"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setFieldErrors((p) => ({ ...p, email: '' })); }}
              error={fieldErrors.email}
              autoComplete="email"
            />

            <div className="space-y-1.5">
              <Input
                label="Password"
                type="password"
                placeholder="Create a strong password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setFieldErrors((p) => ({ ...p, password: '' })); }}
                error={fieldErrors.password}
                autoComplete="new-password"
              />
              <PasswordStrength password={password} />
            </div>

            <Input
              label="Confirm Password"
              type="password"
              placeholder="Confirm your password"
              value={confirmPassword}
              onChange={(e) => { setConfirmPassword(e.target.value); setFieldErrors((p) => ({ ...p, confirmPassword: '' })); }}
              error={fieldErrors.confirmPassword}
              autoComplete="new-password"
            />

            <label className="flex items-start gap-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={agreedToTerms}
                onChange={(e) => { setAgreedToTerms(e.target.checked); setFieldErrors((p) => ({ ...p, terms: '' })); }}
                className="mt-1 h-4 w-4 rounded border-velto-surface-4 bg-velto-surface-2 text-velto-gold focus:ring-velto-gold/30 cursor-pointer"
              />
              <span className="text-sm text-velto-muted">
                I agree to the{' '}
                <span className="text-velto-gold hover:text-velto-gold-light cursor-pointer">Terms of Service</span>
                {' '}and{' '}
                <span className="text-velto-gold hover:text-velto-gold-light cursor-pointer">Privacy Policy</span>
              </span>
            </label>
            {fieldErrors.terms && (
              <p className="text-sm text-red-400 -mt-2">{fieldErrors.terms}</p>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              fullWidth
              loading={isLoading}
              iconRight={<ArrowRight className="h-4 w-4" />}
            >
              Create Account
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-velto-muted">
            Already have an account?{' '}
            <Link to="/login" className="text-velto-gold hover:text-velto-gold-light font-medium">
              Log in
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
