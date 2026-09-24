/**
 * VELTO — Account Page
 */

import { motion } from 'framer-motion';
import { User, Mail, Calendar, Crown, CheckCircle2, AlertCircle } from 'lucide-react';
import AppShell from '../../components/layout/AppShell';
import Button from '../../components/ui/Button';
import { Card, ProgressBar } from '../../components/ui/index';
import { useAuth } from '../../context/AuthContext';
import { formatFileSize, formatDate } from '../../utils';

export default function AccountPage() {
  const { user, profile } = useAuth();

  if (!user) return null;

  const storageUsed = profile?.storage_used_bytes || 0;
  const storageLimit = profile?.storage_limit_bytes || 524_288_000;
  const dailyUsed = profile?.daily_conversion_count || 0;
  const dailyLimit = profile?.daily_conversion_limit || 50;
  const monthlyUsed = profile?.monthly_conversion_count || 0;
  const monthlyLimit = profile?.monthly_conversion_limit || 500;

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-velto-ivory mb-6">Account</h1>

        <div className="space-y-5">
          {/* Profile Info */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="p-6">
              <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-full bg-velto-gold/10 flex items-center justify-center flex-shrink-0">
                  <User className="h-6 w-6 text-velto-gold" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-lg font-semibold text-velto-ivory">{user.email}</h2>
                    {user.is_email_verified ? (
                      <span className="inline-flex items-center gap-1 text-xs text-emerald-400"><CheckCircle2 className="h-3 w-3" /> Verified</span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs text-amber-400"><AlertCircle className="h-3 w-3" /> Unverified</span>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-sm text-velto-dim">
                    <span className="flex items-center gap-1.5"><Mail className="h-3.5 w-3.5" />{user.email}</span>
                    <span className="flex items-center gap-1.5"><Calendar className="h-3.5 w-3.5" />Joined {formatDate(user.date_joined)}</span>
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>

          {/* Plan */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card className="p-6" gold>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Crown className="h-5 w-5 text-velto-gold" />
                  <h3 className="text-lg font-semibold text-velto-ivory">Free Plan</h3>
                </div>
                <Button variant="primary" size="sm">Upgrade to Pro</Button>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="text-center p-3 bg-velto-surface-2 rounded-lg">
                  <p className="text-2xl font-bold text-velto-ivory">{dailyLimit}</p>
                  <p className="text-xs text-velto-dim">Daily conversions</p>
                </div>
                <div className="text-center p-3 bg-velto-surface-2 rounded-lg">
                  <p className="text-2xl font-bold text-velto-ivory">{formatFileSize(storageLimit)}</p>
                  <p className="text-xs text-velto-dim">Storage</p>
                </div>
                <div className="text-center p-3 bg-velto-surface-2 rounded-lg">
                  <p className="text-2xl font-bold text-velto-ivory">50 MB</p>
                  <p className="text-xs text-velto-dim">Max file size</p>
                </div>
              </div>
            </Card>
          </motion.div>

          {/* Usage */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-velto-ivory mb-5">Usage</h3>
              <div className="space-y-5">
                <ProgressBar value={dailyUsed} max={dailyLimit} showLabel label={`Daily Conversions (${dailyUsed} / ${dailyLimit})`} />
                <ProgressBar value={monthlyUsed} max={monthlyLimit} showLabel label={`Monthly Conversions (${monthlyUsed} / ${monthlyLimit})`} />
                <ProgressBar value={storageUsed} max={storageLimit} showLabel label={`Storage (${formatFileSize(storageUsed)} / ${formatFileSize(storageLimit)})`} />
              </div>
            </Card>
          </motion.div>
        </div>
      </div>
    </AppShell>
  );
}
