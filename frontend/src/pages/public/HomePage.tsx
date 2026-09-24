/**
 * VELTO — Home Page / Guest Converter
 * The most important public page — hero + file upload + conversion.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  Shield,
  Zap as ZapIcon,
  Clock,
  Lock,
  FileText,
  Image,
  FileSpreadsheet,
  Sparkles,
} from 'lucide-react';
import PublicLayout from '../../components/layout/PublicLayout';
import Button from '../../components/ui/Button';
import FileDropzone from '../../components/ui/FileDropzone';
import { Select } from '../../components/ui/index';
import { useAuth } from '../../context/AuthContext';
import { conversionService } from '../../services/conversion';
import {
  detectSourceFormat,
  getTargetFormats,
  getGuestConversionsRemaining,
  recordGuestConversion,
} from '../../utils';
import { FORMAT_LABELS } from '../../types';
import type { SupportedFormat } from '../../types';
import type { NormalizedError } from '../../services/api';

export default function HomePage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sourceFormat, setSourceFormat] = useState('');
  const [targetFormat, setTargetFormat] = useState('');
  const [supportedFormats, setSupportedFormats] = useState<SupportedFormat[]>([]);
  const [isConverting, setIsConverting] = useState(false);
  const [error, setError] = useState('');
  const [guestRemaining, setGuestRemaining] = useState(getGuestConversionsRemaining());

  // Load supported formats on mount
  useEffect(() => {
    conversionService.getSupportedFormats().then((res) => {
      setSupportedFormats(res.formats);
    }).catch(() => {});
  }, []);

  const handleFileSelect = useCallback(
    (file: File) => {
      setSelectedFile(file);
      setError('');
      const detected = detectSourceFormat(file.name);
      if (detected) {
        setSourceFormat(detected);
        setTargetFormat('');
      }
    },
    []
  );

  const availableTargets = sourceFormat
    ? getTargetFormats(sourceFormat, supportedFormats)
    : [];

  const targetOptions = availableTargets.map((t) => ({
    value: t,
    label: FORMAT_LABELS[t] || t.toUpperCase(),
  }));

  const handleConvert = async () => {
    if (!selectedFile || !sourceFormat || !targetFormat) {
      setError('Please select a file and target format.');
      return;
    }

    if (!isAuthenticated && guestRemaining <= 0) {
      setError('Guest conversion limit reached. Create a free account to continue converting.');
      return;
    }

    setIsConverting(true);
    setError('');

    try {
      const job = isAuthenticated
        ? await conversionService.createJob(selectedFile, sourceFormat, targetFormat)
        : await conversionService.createGuestJob(selectedFile, sourceFormat, targetFormat);

      if (!isAuthenticated) {
        recordGuestConversion();
        setGuestRemaining(getGuestConversionsRemaining());
      }

      // Navigate to processing/result
      if (job.status === 'completed') {
        navigate(`/convert/result/${job.id}`);
      } else {
        navigate(`/convert/processing?id=${job.id}`);
      }
    } catch (err) {
      const apiError = err as NormalizedError;
      setError(apiError.message || 'Conversion failed. Please try again.');
    } finally {
      setIsConverting(false);
    }
  };

  return (
    <PublicLayout>
      {/* Hero + Converter Section */}
      <section className="relative overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_20%,rgba(212,175,55,0.05)_0%,transparent_60%)]" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-[radial-gradient(ellipse,rgba(212,175,55,0.03)_0%,transparent_70%)]" />

        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 sm:pt-24 pb-16">
          {/* Hero Text */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-velto-ivory leading-tight mb-4">
              Convert Anything.
              <br />
              <span className="velto-gold-text">Into Possibilities.</span>
            </h1>
            <p className="text-lg sm:text-xl text-velto-muted max-w-xl mx-auto">
              Fast, secure and effortless file conversion.
            </p>
          </motion.div>

          {/* Converter Card */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="max-w-2xl mx-auto"
          >
            <div className="bg-velto-surface border border-velto-surface-4 rounded-2xl p-5 sm:p-8 velto-glow">
              <FileDropzone
                onFileSelect={handleFileSelect}
                selectedFile={selectedFile}
                onClear={() => { setSelectedFile(null); setSourceFormat(''); setTargetFormat(''); }}
              />

              {selectedFile && sourceFormat && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="mt-5 space-y-4"
                >
                  <Select
                    label="Convert to"
                    options={targetOptions}
                    value={targetFormat}
                    onChange={setTargetFormat}
                    placeholder="Select target format"
                  />

                  {error && (
                    <p className="text-sm text-red-400">{error}</p>
                  )}

                  <Button
                    variant="primary"
                    size="lg"
                    fullWidth
                    loading={isConverting}
                    onClick={handleConvert}
                    disabled={!targetFormat}
                    iconRight={<ArrowRight className="h-4 w-4" />}
                  >
                    Convert File
                  </Button>
                </motion.div>
              )}

              {/* Guest counter */}
              {!isAuthenticated && (
                <div className="mt-4 text-center">
                  <p className="text-xs text-velto-dim">
                    Guest conversions remaining:{' '}
                    <span className="text-velto-gold font-medium">{guestRemaining}</span>
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 border-t border-velto-surface-4/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-14"
          >
            <h2 className="text-2xl sm:text-3xl font-bold text-velto-ivory mb-3">
              Why <span className="velto-gold-text">VELTO</span>?
            </h2>
            <p className="text-velto-muted max-w-lg mx-auto">
              Built for professionals who demand quality, speed, and security.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              { icon: ZapIcon, title: 'Lightning Fast', desc: 'Convert files in seconds with optimized engines.' },
              { icon: Shield, title: 'Secure', desc: 'Enterprise-grade security. Files are encrypted in transit.' },
              { icon: Clock, title: 'No Waiting', desc: 'Start converting immediately — no forced registration.' },
              { icon: Sparkles, title: '15+ Formats', desc: 'PDF, DOCX, XLSX, images, and many more.' },
            ].map(({ icon: Icon, title, desc }, i) => (
              <motion.div
                key={title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="bg-velto-surface border border-velto-surface-4 rounded-xl p-6 hover:border-velto-border transition-colors"
              >
                <div className="w-10 h-10 rounded-lg bg-velto-gold/10 flex items-center justify-center mb-4">
                  <Icon className="h-5 w-5 text-velto-gold" />
                </div>
                <h3 className="text-velto-ivory font-semibold mb-1.5">{title}</h3>
                <p className="text-sm text-velto-muted">{desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Supported Formats */}
      <section className="py-20 border-t border-velto-surface-4/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-14"
          >
            <h2 className="text-2xl sm:text-3xl font-bold text-velto-ivory mb-3">
              Supported Formats
            </h2>
            <p className="text-velto-muted">All the formats you need in one place.</p>
          </motion.div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {[
              { icon: FileText, formats: ['PDF', 'DOCX', 'TXT'] },
              { icon: FileSpreadsheet, formats: ['XLSX', 'CSV', 'PPTX'] },
              { icon: Image, formats: ['JPG', 'PNG', 'WebP'] },
              { icon: Image, formats: ['BMP', 'TIFF', 'GIF'] },
              { icon: FileText, formats: ['HTML', 'Markdown'] },
            ].map(({ icon: Icon, formats }, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="bg-velto-surface-2 border border-velto-surface-4 rounded-lg p-4 text-center"
              >
                <Icon className="h-6 w-6 text-velto-gold mx-auto mb-2" />
                <div className="space-y-0.5">
                  {formats.map((f) => (
                    <p key={f} className="text-sm text-velto-muted">{f}</p>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      {!isAuthenticated && (
        <section className="py-20 border-t border-velto-surface-4/50">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <Lock className="h-8 w-8 text-velto-gold mx-auto mb-5" />
              <h2 className="text-2xl sm:text-3xl font-bold text-velto-ivory mb-3">
                Unlock unlimited conversions
              </h2>
              <p className="text-velto-muted mb-8 max-w-md mx-auto">
                Create a free account to access your conversion history, increased limits, and more.
              </p>
              <Button
                variant="primary"
                size="lg"
                onClick={() => navigate('/register')}
                iconRight={<ArrowRight className="h-4 w-4" />}
              >
                Create Free Account
              </Button>
            </motion.div>
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="border-t border-velto-surface-4/50 py-8">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md velto-gold-gradient flex items-center justify-center">
              <ZapIcon className="h-3 w-3 text-velto-black" />
            </div>
            <span className="text-sm font-semibold text-velto-ivory">VELTO</span>
            <span className="text-sm text-velto-dim">Conversion</span>
          </div>
          <p className="text-xs text-velto-dim">
            © {new Date().getFullYear()} VELTO Conversion. All rights reserved.
          </p>
        </div>
      </footer>
    </PublicLayout>
  );
}
