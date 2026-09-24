/**
 * VELTO — Email Verification Page
 */

import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Check, Loader2, Mail, AlertTriangle, Zap } from 'lucide-react';
import Button from '../../components/ui/Button';
import { authService } from '../../services/auth';
import { useAuth } from '../../context/AuthContext';

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const email = searchParams.get('email') || '';
  const { user, refreshProfile } = useAuth();

  const [status, setStatus] = useState<'verifying' | 'success' | 'error' | 'idle'>(token ? 'verifying' : 'idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState(false);

  useEffect(() => {
    if (token && email) {
      authService.confirmEmailVerification(email, token)
        .then(() => {
          setStatus('success');
          refreshProfile();
        })
        .catch((err) => {
          setStatus('error');
          setErrorMsg(err.message || 'Verification failed.');
        });
    }
  }, [token, email, refreshProfile]);

  const handleResend = async () => {
    setResending(true);
    try {
      await authService.requestEmailVerification(user?.email || email);
      setResent(true);
    } catch {
      setErrorMsg('Failed to resend verification email.');
    } finally {
      setResending(false);
    }
  };

  const renderContent = () => {
    switch (status) {
      case 'verifying':
        return (
          <div className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-velto-gold/10 flex items-center justify-center mb-6">
              <Loader2 className="h-8 w-8 text-velto-gold animate-spin" />
            </div>
            <h1 className="text-2xl font-bold text-velto-ivory mb-3">Verifying your email</h1>
            <p className="text-velto-muted">Please wait while we verify your email address...</p>
          </div>
        );
      case 'success':
        return (
          <div className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-6">
              <Check className="h-8 w-8 text-emerald-400" />
            </div>
            <h1 className="text-2xl font-bold text-velto-ivory mb-3">Email verified!</h1>
            <p className="text-velto-muted mb-8">Your email has been successfully verified. You can now access all VELTO features.</p>
            <Link to="/dashboard"><Button variant="primary">Go to Dashboard<ArrowRight className="h-4 w-4 ml-1" /></Button></Link>
          </div>
        );
      case 'error':
        return (
          <div className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mb-6">
              <AlertTriangle className="h-8 w-8 text-red-400" />
            </div>
            <h1 className="text-2xl font-bold text-velto-ivory mb-3">Verification failed</h1>
            <p className="text-velto-muted mb-6">{errorMsg}</p>
            <div className="flex flex-col gap-3">
              <Button variant="secondary" onClick={handleResend} loading={resending}>
                <Mail className="h-4 w-4 mr-1" />Resend Verification Email
              </Button>
              <Link to="/login"><Button variant="ghost">Back to Login</Button></Link>
            </div>
          </div>
        );
      default:
        return (
          <div className="text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-velto-gold/10 flex items-center justify-center mb-6">
              <Mail className="h-8 w-8 text-velto-gold" />
            </div>
            <h1 className="text-2xl font-bold text-velto-ivory mb-3">Verify your email</h1>
            <p className="text-velto-muted mb-6">
              {user?.email ? (
                <>We've sent a verification link to <span className="text-velto-ivory font-medium">{user.email}</span>.</>
              ) : (
                'Please check your email for a verification link.'
              )}
            </p>
            <div className="flex flex-col gap-3">
              {resent ? (
                <p className="text-sm text-emerald-400">Verification email sent!</p>
              ) : (
                <Button variant="secondary" onClick={handleResend} loading={resending}>
                  <Mail className="h-4 w-4 mr-1" />Resend Verification Email
                </Button>
              )}
              <Link to="/dashboard"><Button variant="ghost">Continue to Dashboard</Button></Link>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-velto-black flex items-center justify-center p-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="flex justify-center mb-10">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg velto-gold-gradient flex items-center justify-center">
              <Zap className="h-4 w-4 text-velto-black" />
            </div>
            <span className="text-lg font-bold tracking-wide text-velto-ivory">VELTO</span>
          </Link>
        </div>
        {renderContent()}
      </motion.div>
    </div>
  );
}
