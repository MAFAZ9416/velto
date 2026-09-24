/**
 * VELTO — Result Page (Download completed conversion)
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Download, ArrowRight, Check, RefreshCw, UserPlus, Clock } from 'lucide-react';
import PublicLayout from '../../components/layout/PublicLayout';
import Button from '../../components/ui/Button';
import { conversionService } from '../../services/conversion';
import { formatFileSize } from '../../utils';
import { FORMAT_LABELS } from '../../types';
import type { ConversionJob } from '../../types';
import { useAuth } from '../../context/AuthContext';

export default function ResultPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const [job, setJob] = useState<ConversionJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    conversionService.getJobStatus(id)
      .then((data) => { setJob(data); setLoading(false); })
      .catch((err) => { setError(err.message || 'Failed to load conversion result.'); setLoading(false); });
  }, [id]);

  const handleDownload = () => {
    if (id) conversionService.downloadFile(id);
  };

  if (loading) {
    return (
      <PublicLayout>
        <div className="flex items-center justify-center py-32">
          <div className="h-10 w-10 rounded-full border-2 border-velto-surface-4 border-t-velto-gold animate-spin" />
        </div>
      </PublicLayout>
    );
  }

  if (error || !job) {
    return (
      <PublicLayout>
        <div className="max-w-md mx-auto px-4 py-32 text-center">
          <h1 className="text-2xl font-bold text-velto-ivory mb-3">File not found</h1>
          <p className="text-velto-muted mb-8">{error || 'This conversion result is no longer available.'}</p>
          <Button variant="primary" onClick={() => navigate('/')}>Convert Another File</Button>
        </div>
      </PublicLayout>
    );
  }

  return (
    <PublicLayout>
      <div className="max-w-xl mx-auto px-4 py-16 sm:py-24">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
          {/* Success icon */}
          <div className="mx-auto w-20 h-20 rounded-full bg-emerald-500/10 flex items-center justify-center mb-6">
            <Check className="h-10 w-10 text-emerald-400" />
          </div>

          <h1 className="text-2xl sm:text-3xl font-bold text-velto-ivory mb-2">
            Your file is ready.
          </h1>
          <p className="text-velto-muted mb-8">
            Conversion completed successfully.
          </p>

          {/* File info card */}
          <div className="bg-velto-surface border border-velto-surface-4 rounded-xl p-5 mb-6 text-left">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-velto-dim mb-1">Original File</p>
                <p className="text-velto-ivory font-medium truncate">{job.original_filename}</p>
              </div>
              <div>
                <p className="text-velto-dim mb-1">Converted To</p>
                <p className="text-velto-ivory font-medium">{FORMAT_LABELS[job.target_format] || job.target_format.toUpperCase()}</p>
              </div>
              <div>
                <p className="text-velto-dim mb-1">Input Size</p>
                <p className="text-velto-text">{formatFileSize(job.file_size_bytes)}</p>
              </div>
              <div>
                <p className="text-velto-dim mb-1">Output Size</p>
                <p className="text-velto-text">{formatFileSize(job.output_size_bytes)}</p>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col gap-3 mb-8">
            <Button
              variant="primary"
              size="lg"
              fullWidth
              onClick={handleDownload}
              icon={<Download className="h-4 w-4" />}
            >
              Download File
            </Button>
            <Button
              variant="secondary"
              fullWidth
              onClick={() => navigate('/')}
              icon={<RefreshCw className="h-4 w-4" />}
            >
              Convert Another
            </Button>
          </div>

          {/* File retention notice */}
          <div className="flex items-center justify-center gap-2 text-xs text-velto-dim mb-8">
            <Clock className="h-3.5 w-3.5" />
            Files are available for 24 hours, then automatically deleted.
          </div>

          {/* Sign up CTA for guests */}
          {!isAuthenticated && (
            <div className="bg-velto-surface border border-velto-border rounded-xl p-6">
              <UserPlus className="h-6 w-6 text-velto-gold mx-auto mb-3" />
              <h3 className="text-velto-ivory font-semibold mb-1.5">
                Want to keep your conversion history?
              </h3>
              <p className="text-sm text-velto-muted mb-4">
                Create a free VELTO account to access unlimited features.
              </p>
              <Link to="/register">
                <Button variant="secondary" size="sm" iconRight={<ArrowRight className="h-3.5 w-3.5" />}>
                  Create Free Account
                </Button>
              </Link>
            </div>
          )}
        </motion.div>
      </div>
    </PublicLayout>
  );
}
