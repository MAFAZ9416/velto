/**
 * VELTO — Home Page / Guest Converter
 * The most important public page — hero + file upload + conversion + SEO internal linking.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  Shield,
  Zap as ZapIcon,
  Clock,
  Lock,
  FileText,
  Image as ImageIcon,
  FileSpreadsheet,
  Sparkles,
} from 'lucide-react';
import PublicLayout from '../../components/layout/PublicLayout';
import SeoHead from '../../components/seo/SeoHead';
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
    conversionService
      .getSupportedFormats()
      .then((res) => {
        setSupportedFormats(res.formats);
      })
      .catch(() => {});
  }, []);

  const handleFileSelect = useCallback((file: File) => {
    setSelectedFile(file);
    setError('');
    const detected = detectSourceFormat(file.name);
    if (detected) {
      setSourceFormat(detected);
      setTargetFormat('');
    }
  }, []);

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

      navigate(`/convert/processing?jobId=${job.id}`);
    } catch (err: any) {
      setIsConverting(false);
      setError(err.message || 'Conversion failed. Please try again.');
    }
  };

  return (
    <PublicLayout>
      {/* Page-Specific SEO Metadata & JSON-LD */}
      <SeoHead />

      {/* Hero Section */}
      <section className="relative pt-12 pb-20 overflow-hidden">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gold-500/10 border border-gold-500/20 text-gold-400 text-xs font-semibold uppercase tracking-wider mb-6"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Universal Online File Converter
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-ivory-100 tracking-tight leading-none mb-6"
            >
              Convert Your Files. <span className="velto-gold-text">Simply.</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-lg text-muted-400 max-w-xl mx-auto"
            >
              Convert PDF, Word, Excel, PowerPoint, images, and documents online in seconds with VELTO Conversion.
            </motion.p>
          </div>

          {/* Upload Dropzone */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="max-w-2xl mx-auto"
          >
            <div className="bg-obsidian-900 border border-obsidian-800 rounded-2xl p-6 sm:p-8 shadow-2xl">
              <FileDropzone
                onFileSelect={handleFileSelect}
                selectedFile={selectedFile}
                onClear={() => {
                  setSelectedFile(null);
                  setSourceFormat('');
                  setTargetFormat('');
                }}
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

                  {error && <p className="text-sm text-red-400">{error}</p>}

                  <Button
                    variant="primary"
                    size="lg"
                    fullWidth
                    loading={isConverting}
                    onClick={handleConvert}
                    disabled={!targetFormat}
                    iconRight={<ArrowRight className="h-4 w-4" />}
                  >
                    Convert File Now
                  </Button>
                </motion.div>
              )}

              {/* Guest counter */}
              {!isAuthenticated && (
                <div className="mt-4 text-center">
                  <p className="text-xs text-muted-500">
                    Guest conversions remaining:{' '}
                    <span className="text-gold-400 font-semibold">{guestRemaining}</span>
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Popular Converter Landing Pages (SEO Internal Links Grid) */}
      <section className="py-16 border-t border-obsidian-800/80 bg-obsidian-900/40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
            <div>
              <h2 className="text-2xl font-bold text-ivory-100">Popular Online File Converters</h2>
              <p className="text-sm text-muted-400 mt-1">
                Select a dedicated converter tool for your document and image conversion needs.
              </p>
            </div>
            <Link
              to="/tools"
              className="text-xs text-gold-400 font-semibold hover:underline flex items-center gap-1.5"
            >
              Browse All 35+ Tools <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { slug: 'pdf-to-word', title: 'PDF to Word Converter', desc: 'Convert PDF to editable DOCX documents online.' },
              { slug: 'word-to-pdf', title: 'Word to PDF Converter', desc: 'Convert Word DOCX files to PDF documents.' },
              { slug: 'pdf-to-excel', title: 'PDF to Excel Converter', desc: 'Extract PDF tables into editable XLSX spreadsheets.' },
              { slug: 'pdf-to-jpg', title: 'PDF to JPG Converter', desc: 'Convert PDF document pages to high-res JPG images.' },
              { slug: 'jpg-to-png', title: 'JPG to PNG Converter', desc: 'Convert JPG images to PNG format with high quality.' },
              { slug: 'png-to-jpg', title: 'PNG to JPG Converter', desc: 'Convert PNG images to compact JPG files.' },
              { slug: 'webp-to-jpg', title: 'WEBP to JPG Converter', desc: 'Convert web WEBP images to standard JPG format.' },
              { slug: 'xlsx-to-pdf', title: 'Excel to PDF Converter', desc: 'Convert Excel XLSX spreadsheets to PDF format.' },
            ].map((tool) => (
              <Link
                key={tool.slug}
                to={`/tools/${tool.slug}`}
                className="group p-5 rounded-2xl bg-obsidian-900 border border-obsidian-800 hover:border-gold-500/50 hover:bg-obsidian-850 transition-all shadow-md block"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-bold text-ivory-100 group-hover:text-gold-400 transition-colors">
                    {tool.title}
                  </span>
                  <ArrowRight className="w-4 h-4 text-gold-400 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                </div>
                <p className="text-xs text-muted-400 leading-relaxed">{tool.desc}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 border-t border-obsidian-800">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-14">
            <h2 className="text-2xl sm:text-3xl font-bold text-ivory-100 mb-3">
              Why Choose <span className="velto-gold-text">VELTO Conversion</span>?
            </h2>
            <p className="text-muted-400 max-w-lg mx-auto">
              Built for professionals who demand quality, speed, and privacy.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              { icon: ZapIcon, title: 'Lightning Fast', desc: 'Convert files in seconds with optimized conversion engines.' },
              { icon: Shield, title: 'Secure & Encrypted', desc: 'TLS encrypted transfers. Files are deleted after processing.' },
              { icon: Clock, title: 'No Waiting', desc: 'Start converting immediately with our guest conversion flow.' },
              { icon: Sparkles, title: '15+ Formats', desc: 'Convert PDF, DOCX, XLSX, PPTX, JPG, PNG, WEBP, and more.' },
            ].map(({ icon: Icon, title, desc }) => (
              <div
                key={title}
                className="bg-obsidian-900 border border-obsidian-800 rounded-xl p-6 hover:border-gold-500/40 transition-colors"
              >
                <div className="w-10 h-10 rounded-lg bg-gold-500/10 border border-gold-500/20 flex items-center justify-center mb-4 text-gold-400">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="text-ivory-100 font-semibold mb-1.5">{title}</h3>
                <p className="text-sm text-muted-400">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Supported Formats Section */}
      <section className="py-16 border-t border-obsidian-800">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-ivory-100 mb-3">
              Supported File Formats
            </h2>
            <p className="text-muted-400">Universal document and image format support.</p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {[
              { icon: FileText, label: 'Documents', formats: ['PDF', 'DOCX', 'TXT'] },
              { icon: FileSpreadsheet, label: 'Spreadsheets', formats: ['XLSX', 'CSV', 'PPTX'] },
              { icon: ImageIcon, label: 'Web Images', formats: ['JPG', 'PNG', 'WebP'] },
              { icon: ImageIcon, label: 'Raw Images', formats: ['BMP', 'TIFF', 'GIF'] },
              { icon: FileText, label: 'Text & Code', formats: ['HTML', 'Markdown'] },
            ].map(({ icon: Icon, label, formats }, i) => (
              <div
                key={i}
                className="bg-obsidian-900 border border-obsidian-800 rounded-xl p-4 text-center"
              >
                <Icon className="h-6 w-6 text-gold-400 mx-auto mb-2" />
                <p className="text-xs font-bold text-ivory-200 mb-1">{label}</p>
                <div className="space-y-0.5">
                  {formats.map((f) => (
                    <p key={f} className="text-xs text-muted-500">{f}</p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      {!isAuthenticated && (
        <section className="py-20 border-t border-obsidian-800">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <Lock className="h-8 w-8 text-gold-400 mx-auto mb-5" />
            <h2 className="text-2xl sm:text-3xl font-bold text-ivory-100 mb-3">
              Unlock Unlimited Conversions
            </h2>
            <p className="text-muted-400 mb-8 max-w-md mx-auto">
              Create a free account to access your conversion history, increased file limits, and more.
            </p>
            <Button
              variant="primary"
              size="lg"
              onClick={() => navigate('/register')}
              iconRight={<ArrowRight className="h-4 w-4" />}
            >
              Create Free Account
            </Button>
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="border-t border-obsidian-800 py-8">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-gold-500 text-obsidian-950 font-bold flex items-center justify-center text-xs">
              V
            </div>
            <span className="text-sm font-semibold text-ivory-100">VELTO</span>
            <span className="text-sm text-muted-400">Conversion</span>
          </div>
          <p className="text-xs text-muted-500">
            © {new Date().getFullYear()} VELTO Conversion. All rights reserved.
          </p>
        </div>
      </footer>
    </PublicLayout>
  );
}
