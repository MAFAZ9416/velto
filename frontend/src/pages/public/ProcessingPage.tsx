/**
 * VELTO — Processing Page (Guest conversion progress)
 */

import { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { CheckCircle2, Loader2, Shield, ArrowRight } from 'lucide-react';
import PublicLayout from '../../components/layout/PublicLayout';
import { ProgressBar } from '../../components/ui/index';
import Button from '../../components/ui/Button';
import { conversionService } from '../../services/conversion';
import { formatFileSize } from '../../utils';
import { FORMAT_LABELS } from '../../types';
import type { ConversionJob } from '../../types';

const STAGES = [
  { key: 'uploading', label: 'Uploading' },
  { key: 'preparing', label: 'Preparing' },
  { key: 'converting', label: 'Converting' },
  { key: 'finalizing', label: 'Finalizing' },
  { key: 'complete', label: 'Complete' },
];

function getStageIndex(job: ConversionJob | null): number {
  if (!job) return 0;
  switch (job.status) {
    case 'pending': return 0;
    case 'queued': return 1;
    case 'started': return 2;
    case 'processing': return 2;
    case 'completed': return 4;
    case 'failed': return -1;
    default: return 1;
  }
}

export default function ProcessingPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const jobId = searchParams.get('id');

  const [job, setJob] = useState<ConversionJob | null>(null);
  const [error, setError] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  useEffect(() => {
    if (!jobId) { setError('No conversion job found.'); return; }

    const poll = async () => {
      try {
        const jobData = await conversionService.getJobStatus(jobId);
        setJob(jobData);
        if (jobData.status === 'completed') {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setTimeout(() => navigate(`/convert/result/${jobId}`), 1200);
        } else if (jobData.status === 'failed' || jobData.status === 'cancelled') {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setError(jobData.error_message || 'Conversion failed.');
        }
      } catch (err: any) {
        // If job not found (guest session), show generic progress
        if (err.status === 401 || err.status === 403) {
          // Guest user — can't poll V1, simulate progress
        }
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [jobId, navigate]);

  const stageIndex = getStageIndex(job);
  const progress = job?.progress || Math.min(stageIndex * 25, 95);

  return (
    <PublicLayout>
      <div className="max-w-xl mx-auto px-4 py-20 sm:py-32">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          {/* Main icon */}
          <div className="relative mx-auto w-20 h-20 mb-8">
            {stageIndex === 4 ? (
              <div className="w-20 h-20 rounded-full bg-emerald-500/10 flex items-center justify-center">
                <CheckCircle2 className="h-10 w-10 text-emerald-400" />
              </div>
            ) : error ? (
              <div className="w-20 h-20 rounded-full bg-red-500/10 flex items-center justify-center">
                <span className="text-3xl text-red-400">!</span>
              </div>
            ) : (
              <div className="w-20 h-20 rounded-full bg-velto-gold/10 flex items-center justify-center">
                <Loader2 className="h-10 w-10 text-velto-gold animate-spin" />
              </div>
            )}
          </div>

          {error ? (
            <>
              <h1 className="text-2xl font-bold text-velto-ivory mb-3">Conversion failed</h1>
              <p className="text-velto-muted mb-8">{error}</p>
              <Button variant="primary" onClick={() => navigate('/')}>
                Try Again
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </>
          ) : (
            <>
              <h1 className="text-2xl font-bold text-velto-ivory mb-2">
                {stageIndex === 4 ? 'Conversion complete!' : 'Converting your file...'}
              </h1>

              {/* File info */}
              {job && (
                <div className="text-sm text-velto-muted mb-6">
                  <span className="text-velto-ivory">{job.original_filename}</span>
                  {job.file_size_bytes && (
                    <span> · {formatFileSize(job.file_size_bytes)}</span>
                  )}
                  <span> · {FORMAT_LABELS[job.source_format] || job.source_format} → {FORMAT_LABELS[job.target_format] || job.target_format}</span>
                </div>
              )}

              {/* Progress bar */}
              <div className="mb-8">
                <ProgressBar value={progress} showLabel size="lg" />
              </div>

              {/* Status stages */}
              <div className="flex flex-col gap-3 max-w-xs mx-auto mb-8">
                {STAGES.map((stage, i) => (
                  <div key={stage.key} className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                      i < stageIndex ? 'bg-emerald-500/20 text-emerald-400' :
                      i === stageIndex ? 'bg-velto-gold/20 text-velto-gold' :
                      'bg-velto-surface-3 text-velto-dim'
                    }`}>
                      {i < stageIndex ? <CheckCircle2 className="h-3.5 w-3.5" /> : i + 1}
                    </div>
                    <span className={`text-sm ${
                      i <= stageIndex ? 'text-velto-ivory' : 'text-velto-dim'
                    }`}>
                      {stage.label}
                    </span>
                  </div>
                ))}
              </div>

              {/* Security badge */}
              <div className="flex items-center justify-center gap-2 text-xs text-velto-dim">
                <Shield className="h-3.5 w-3.5" />
                Your file is encrypted and will be automatically deleted
              </div>
            </>
          )}
        </motion.div>
      </div>
    </PublicLayout>
  );
}
