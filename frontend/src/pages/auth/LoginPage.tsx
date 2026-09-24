/**
 * VELTO — Login Page
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Zap, Lock, FileText, Image, Shield } from 'lucide-react';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import { useAuth } from '../../context/AuthContext';
import type { NormalizedError } from '../../services/api';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim() || !password) {
      setError('Please enter your email and password.');
      return;
    }

    setIsLoading(true);
    try {
      await login(email.trim().toLowerCase(), password);
      navigate('/dashboard');
    } catch (err) {
      const apiError = err as NormalizedError;
      setError(apiError.message || 'Invalid email or password.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-velto-black flex">
      {/* Left decorative panel */}
      <div className="hidden lg:flex lg:w-1/2 xl:w-[45%] relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-velto-black via-velto-surface to-velto-black-2" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_60%_30%,rgba(212,175,55,0.06)_0%,transparent_70%)]" />
        
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
              Welcome back.
              <br />
              <span className="velto-gold-text">Let's convert.</span>
            </h2>
            <p className="text-velto-muted text-lg mb-12">
              Your files, your way. Securely and instantly.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="space-y-5"
          >
            {[
              { icon: FileText, text: 'Access your conversion history' },
              { icon: Image, text: '50 daily conversions with free plan' },
              { icon: Shield, text: 'End-to-end file security' },
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
            Welcome back
          </h1>
          <p className="text-velto-muted mb-8">
            Continue converting with VELTO.
          </p>

          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
              <Lock className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
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

            <Input
              label="Password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 rounded border-velto-surface-4 bg-velto-surface-2 text-velto-gold focus:ring-velto-gold/30 cursor-pointer"
                />
                <span className="text-sm text-velto-muted">Remember me</span>
              </label>
              <Link
                to="/forgot-password"
                className="text-sm text-velto-gold hover:text-velto-gold-light font-medium"
              >
                Forgot password?
              </Link>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              fullWidth
              loading={isLoading}
              iconRight={<ArrowRight className="h-4 w-4" />}
            >
              Log In
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-velto-muted">
            Don't have an account?{' '}
            <Link to="/register" className="text-velto-gold hover:text-velto-gold-light font-medium">
              Sign up
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
