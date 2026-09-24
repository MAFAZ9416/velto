/**
 * VELTO — Conversion Workspace Page
 */

import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Download, CheckCircle2, Loader2 } from 'lucide-react';
import AppShell from '../../components/layout/AppShell';
import Button from '../../components/ui/Button';
import FileDropzone from '../../components/ui/FileDropzone';
import { Select, ProgressBar, Badge, Card } from '../../components/ui/index';
import { conversionService } from '../../services/conversion';
import { detectSourceFormat, getTargetFormats, formatFileSize } from '../../utils';
import { FORMAT_LABELS } from '../../types';
import type { ConversionJob, SupportedFormat } from '../../types';
import type { NormalizedError } from '../../services/api';

export default function ConvertPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sourceFormat, setSourceFormat] = useState('');
  const [targetFormat, setTargetFormat] = useState('');
  const [formats, setFormats] = useState<SupportedFormat[]>([]);
  const [isConverting, setIsConverting] = useState(false);
  const [error, setError] = useState('');
  const [job, setJob] = useState<ConversionJob | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  useEffect(() => {
    conversionService.getSupportedFormats().then((res) => setFormats(res.formats)).catch(() => {});
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, []);

  const targetOptions = sourceFormat
    ? getTargetFormats(sourceFormat, formats).map((t) => ({ value: t, label: FORMAT_LABELS[t] || t.toUpperCase() }))
    : [];

  const handleConvert = async () => {
    if (!selectedFile || !sourceFormat || !targetFormat) return;
    setIsConverting(true);
    setError('');
    setJob(null);

    try {
      const newJob = await conversionService.createJob(selectedFile, sourceFormat, targetFormat);
      setJob(newJob);

      if (newJob.status === 'completed') {
        setIsConverting(false);
        return;
      }

      // Poll for status
      intervalRef.current = setInterval(async () => {
        try {
          const updated = await conversionService.getJobStatus(newJob.id);
          setJob(updated);
          if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'cancelled') {
            clearInterval(intervalRef.current);
            setIsConverting(false);
          }
        } catch {
          clearInterval(intervalRef.current);
          setIsConverting(false);
        }
      }, 2000);
    } catch (err) {
      setError((err as NormalizedError).message || 'Conversion failed.');
      setIsConverting(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setSourceFormat('');
    setTargetFormat('');
    setJob(null);
    setError('');
    clearInterval(intervalRef.current);
  };

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto">
        <h1 className="text-2xl font-bold text-velto-ivory mb-6">Convert</h1>

        <div className="space-y-5">
          {/* Upload */}
          <Card className="p-6">
            <h2 className="text-sm font-medium text-velto-muted mb-4 uppercase tracking-wider">1. Upload File</h2>
            <FileDropzone
              onFileSelect={(file) => {
                setSelectedFile(file);
                setJob(null);
                const detected = detectSourceFormat(file.name);
                if (detected) { setSourceFormat(detected); setTargetFormat(''); }
              }}
              selectedFile={selectedFile}
              onClear={handleReset}
            />
          </Card>

          {/* Format Selection */}
          {selectedFile && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <Card className="p-6">
                <h2 className="text-sm font-medium text-velto-muted mb-4 uppercase tracking-wider">2. Select Format</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-velto-dim mb-1.5">Source Format</p>
                    <div className="bg-velto-surface-2 border border-velto-surface-4 rounded-lg px-4 py-3 text-sm text-velto-ivory">
                      {FORMAT_LABELS[sourceFormat] || sourceFormat.toUpperCase()}
                    </div>
                  </div>
                  <Select
                    label="Convert to"
                    options={targetOptions}
                    value={targetFormat}
                    onChange={setTargetFormat}
                    placeholder="Select target format"
                  />
                </div>
              </Card>
            </motion.div>
          )}

          {/* Convert Button */}
          {selectedFile && targetFormat && !job && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              {error && <p className="text-sm text-red-400 mb-3">{error}</p>}
              <Button variant="primary" size="lg" fullWidth onClick={handleConvert} loading={isConverting} iconRight={<ArrowRight className="h-4 w-4" />}>
                Convert File
              </Button>
            </motion.div>
          )}

          {/* Progress / Result */}
          {job && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <Card className="p-6">
                <h2 className="text-sm font-medium text-velto-muted mb-4 uppercase tracking-wider">
                  {job.status === 'completed' ? '3. Download' : '3. Processing'}
                </h2>

                <div className="flex items-center gap-3 mb-4">
                  {job.status === 'completed' ? (
                    <CheckCircle2 className="h-6 w-6 text-emerald-400 flex-shrink-0" />
                  ) : job.status === 'failed' ? (
                    <span className="text-xl text-red-400">!</span>
                  ) : (
                    <Loader2 className="h-6 w-6 text-velto-gold animate-spin flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-velto-ivory font-medium truncate">{job.original_filename}</p>
                    <p className="text-xs text-velto-dim">
                      {FORMAT_LABELS[job.source_format]} → {FORMAT_LABELS[job.target_format]}
                      {job.output_size_bytes && ` · ${formatFileSize(job.output_size_bytes)}`}
                    </p>
                  </div>
                  <Badge status={job.status} />
                </div>

                {job.status !== 'completed' && job.status !== 'failed' && (
                  <ProgressBar value={job.progress} showLabel className="mb-4" />
                )}

                {job.status === 'failed' && (
                  <p className="text-sm text-red-400 mb-4">{job.error_message || 'Conversion failed.'}</p>
                )}

                {job.status === 'completed' && (
                  <div className="flex flex-col sm:flex-row gap-3">
                    <Button variant="primary" icon={<Download className="h-4 w-4" />} onClick={() => conversionService.downloadFile(job.id)}>
                      Download File
                    </Button>
                    <Button variant="secondary" onClick={handleReset}>Convert Another</Button>
                  </div>
                )}
              </Card>
            </motion.div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
