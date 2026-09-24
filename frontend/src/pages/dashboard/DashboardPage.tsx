/**
 * VELTO — Dashboard Page
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  ArrowRightLeft,
  Download,
  HardDrive,
  Shield,
} from 'lucide-react';
import AppShell from '../../components/layout/AppShell';
import Button from '../../components/ui/Button';
import FileDropzone from '../../components/ui/FileDropzone';
import { Badge, Card, Select, EmptyState, SkeletonCard } from '../../components/ui/index';
import { useAuth } from '../../context/AuthContext';
import { conversionService } from '../../services/conversion';
import {
  detectSourceFormat,
  getTargetFormats,
  formatFileSize,
  formatRelativeTime,
} from '../../utils';
import { FORMAT_LABELS } from '../../types';
import type { ConversionJob, SupportedFormat } from '../../types';
import type { NormalizedError } from '../../services/api';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { profile } = useAuth();

  const [recentJobs, setRecentJobs] = useState<ConversionJob[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sourceFormat, setSourceFormat] = useState('');
  const [targetFormat, setTargetFormat] = useState('');
  const [formats, setFormats] = useState<SupportedFormat[]>([]);
  const [isConverting, setIsConverting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    conversionService.getHistory({ page_size: 5 }).then((res) => {
      setRecentJobs(res.results);
    }).catch(() => {}).finally(() => setLoadingJobs(false));

    conversionService.getSupportedFormats().then((res) => setFormats(res.formats)).catch(() => {});
  }, []);

  const targetOptions = sourceFormat
    ? getTargetFormats(sourceFormat, formats).map((t) => ({ value: t, label: FORMAT_LABELS[t] || t.toUpperCase() }))
    : [];

  const handleConvert = async () => {
    if (!selectedFile || !sourceFormat || !targetFormat) return;
    setIsConverting(true);
    setError('');
    try {
      const job = await conversionService.createJob(selectedFile, sourceFormat, targetFormat);
      if (job.status === 'completed') navigate(`/convert/result/${job.id}`);
      else navigate(`/convert/processing?id=${job.id}`);
    } catch (err) {
      setError((err as NormalizedError).message || 'Conversion failed.');
    } finally {
      setIsConverting(false);
    }
  };

  const storageUsed = profile?.storage_used_bytes || 0;
  const storageLimit = profile?.storage_limit_bytes || 524_288_000;
  const conversionsUsed = profile?.daily_conversion_count || 0;
  const conversionsLimit = profile?.daily_conversion_limit || 50;

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Welcome Hero */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative overflow-hidden bg-velto-surface border border-velto-surface-4 rounded-2xl p-6 sm:p-8"
        >
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_80%_20%,rgba(212,175,55,0.04)_0%,transparent_60%)]" />
          <div className="relative">
            <h1 className="text-2xl sm:text-3xl font-bold text-velto-ivory mb-1.5">
              Welcome back.
            </h1>
            <p className="text-velto-muted mb-6">
              Convert anything into possibilities.
            </p>
            <div className="max-w-lg">
              <FileDropzone
                onFileSelect={(file) => {
                  setSelectedFile(file);
                  const detected = detectSourceFormat(file.name);
                  if (detected) { setSourceFormat(detected); setTargetFormat(''); }
                }}
                selectedFile={selectedFile}
                onClear={() => { setSelectedFile(null); setSourceFormat(''); setTargetFormat(''); }}
                compact
              />
              {selectedFile && sourceFormat && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-4 flex flex-col sm:flex-row gap-3">
                  <div className="flex-1">
                    <Select options={targetOptions} value={targetFormat} onChange={setTargetFormat} placeholder="Select format" />
                  </div>
                  <Button variant="primary" onClick={handleConvert} loading={isConverting} disabled={!targetFormat} iconRight={<ArrowRight className="h-4 w-4" />}>
                    Convert
                  </Button>
                </motion.div>
              )}
              {error && <p className="text-sm text-red-400 mt-2">{error}</p>}
            </div>
          </div>
        </motion.div>

        {/* Usage Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 rounded-lg bg-velto-gold/10 flex items-center justify-center">
                <ArrowRightLeft className="h-4 w-4 text-velto-gold" />
              </div>
              <div>
                <p className="text-xs text-velto-dim">Daily Conversions</p>
                <p className="text-lg font-bold text-velto-ivory">{conversionsUsed} <span className="text-sm font-normal text-velto-dim">/ {conversionsLimit}</span></p>
              </div>
            </div>
            <div className="h-1.5 bg-velto-surface-3 rounded-full overflow-hidden">
              <div className="h-full velto-gold-gradient rounded-full" style={{ width: `${Math.min(100, (conversionsUsed / conversionsLimit) * 100)}%` }} />
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 rounded-lg bg-velto-gold/10 flex items-center justify-center">
                <HardDrive className="h-4 w-4 text-velto-gold" />
              </div>
              <div>
                <p className="text-xs text-velto-dim">Storage Used</p>
                <p className="text-lg font-bold text-velto-ivory">{formatFileSize(storageUsed)} <span className="text-sm font-normal text-velto-dim">/ {formatFileSize(storageLimit)}</span></p>
              </div>
            </div>
            <div className="h-1.5 bg-velto-surface-3 rounded-full overflow-hidden">
              <div className="h-full velto-gold-gradient rounded-full" style={{ width: `${Math.min(100, (storageUsed / storageLimit) * 100)}%` }} />
            </div>
          </Card>

          <Card>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 rounded-lg bg-velto-gold/10 flex items-center justify-center">
                <Shield className="h-4 w-4 text-velto-gold" />
              </div>
              <div>
                <p className="text-xs text-velto-dim">Security</p>
                <p className="text-lg font-bold text-velto-ivory">Active</p>
              </div>
            </div>
            <p className="text-xs text-velto-dim">End-to-end encryption enabled</p>
          </Card>
        </div>

        {/* Recent Conversions */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-velto-ivory">Recent Conversions</h2>
            <button onClick={() => navigate('/conversions')} className="text-sm text-velto-gold hover:text-velto-gold-light transition-colors">
              View All →
            </button>
          </div>

          {loadingJobs ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[1, 2].map((i) => <SkeletonCard key={i} />)}
            </div>
          ) : recentJobs.length === 0 ? (
            <EmptyState
              icon={<ArrowRightLeft className="h-12 w-12" />}
              title="No conversions yet"
              description="Your completed conversions will appear here."
              action={<Button variant="primary" onClick={() => navigate('/convert')}>Start Converting</Button>}
            />
          ) : (
            <div className="space-y-2">
              {recentJobs.map((job) => (
                <div
                  key={job.id}
                  className="bg-velto-surface border border-velto-surface-4 rounded-xl p-4 flex items-center gap-4 hover:border-velto-border transition-colors cursor-pointer"
                  onClick={() => job.status === 'completed' ? navigate(`/convert/result/${job.id}`) : null}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-velto-ivory font-medium truncate text-sm">{job.original_filename}</p>
                    <p className="text-xs text-velto-dim mt-0.5">
                      {FORMAT_LABELS[job.source_format] || job.source_format} → {FORMAT_LABELS[job.target_format] || job.target_format}
                      {' · '}
                      {formatRelativeTime(job.created_at)}
                    </p>
                  </div>
                  <Badge status={job.status} />
                  {job.download_available && (
                    <button
                      onClick={(e) => { e.stopPropagation(); conversionService.downloadFile(job.id); }}
                      className="p-2 rounded-lg text-velto-dim hover:text-velto-gold hover:bg-velto-gold/10 transition-colors"
                      aria-label="Download"
                    >
                      <Download className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
