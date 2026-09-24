/**
 * VELTO — Settings Page
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, Trash2, AlertTriangle } from 'lucide-react';
import AppShell from '../../components/layout/AppShell';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import { Card, Modal } from '../../components/ui/index';
import { useAuth } from '../../context/AuthContext';
import { authService } from '../../services/auth';
import type { NormalizedError } from '../../services/api';

export default function SettingsPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const handleDeleteAccount = async () => {
    if (!deletePassword) { setDeleteError('Please enter your password.'); return; }
    setDeleteLoading(true);
    setDeleteError('');
    try {
      await authService.deleteAccount(deletePassword);
      await logout();
      navigate('/');
    } catch (err) {
      setDeleteError((err as NormalizedError).message || 'Failed to delete account.');
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-velto-ivory mb-6">Settings</h1>

        <div className="space-y-6">
          {/* Account */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-velto-ivory mb-4">Account</h2>
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-velto-dim mb-1">Email Address</p>
                  <p className="text-velto-ivory">{user?.email}</p>
                </div>
                <div>
                  <p className="text-sm text-velto-dim mb-1">Email Verification</p>
                  <p className={user?.is_email_verified ? 'text-emerald-400' : 'text-amber-400'}>
                    {user?.is_email_verified ? 'Verified' : 'Not verified'}
                  </p>
                </div>
              </div>
            </Card>
          </motion.div>

          {/* Security */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <Card className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <Shield className="h-5 w-5 text-velto-gold" />
                <h2 className="text-lg font-semibold text-velto-ivory">Security</h2>
              </div>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-velto-ivory text-sm font-medium">Password</p>
                    <p className="text-xs text-velto-dim">Last changed: Unknown</p>
                  </div>
                  <Button variant="secondary" size="sm" onClick={() => navigate('/forgot-password')}>Change Password</Button>
                </div>
              </div>
            </Card>
          </motion.div>

          {/* Preferences */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-velto-ivory mb-4">Preferences</h2>
              <div className="space-y-4">
                <label className="flex items-center justify-between">
                  <div>
                    <p className="text-velto-ivory text-sm font-medium">Email Notifications</p>
                    <p className="text-xs text-velto-dim">Receive updates about your conversions</p>
                  </div>
                  <input type="checkbox" defaultChecked className="h-4 w-4 rounded border-velto-surface-4 bg-velto-surface-2 text-velto-gold focus:ring-velto-gold/30 cursor-pointer" />
                </label>
              </div>
            </Card>
          </motion.div>

          {/* Danger Zone */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <Card className="p-6 border-red-500/20">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="h-5 w-5 text-red-400" />
                <h2 className="text-lg font-semibold text-red-400">Danger Zone</h2>
              </div>
              <p className="text-sm text-velto-muted mb-4">
                Deleting your account will permanently remove all your data, including conversion history and files.
                This action cannot be undone.
              </p>
              <Button variant="danger" icon={<Trash2 className="h-4 w-4" />} onClick={() => setShowDeleteModal(true)}>
                Delete Account
              </Button>
            </Card>
          </motion.div>
        </div>

        {/* Delete Confirmation Modal */}
        <Modal
          isOpen={showDeleteModal}
          onClose={() => { setShowDeleteModal(false); setDeletePassword(''); setDeleteError(''); }}
          title="Delete Account"
        >
          <div className="space-y-4">
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <p className="text-sm text-red-400">
                This will permanently delete your account and all associated data.
                This action <strong>cannot be undone</strong>.
              </p>
            </div>
            <Input
              label="Confirm your password"
              type="password"
              placeholder="Enter your password"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
              error={deleteError}
            />
            <div className="flex gap-3 pt-2">
              <Button variant="ghost" onClick={() => setShowDeleteModal(false)} className="flex-1">Cancel</Button>
              <Button variant="danger" onClick={handleDeleteAccount} loading={deleteLoading} className="flex-1">Delete Account</Button>
            </div>
          </div>
        </Modal>
      </div>
    </AppShell>
  );
}
