/**
 * VELTO — SEO-Optimized Converter Landing Page
 * Dynamic tool landing page for /tools/:tool
 *
 * Renders:
 * - Page-specific SEO metadata & structured data (SeoHead)
 * - Breadcrumb navigation matching schema
 * - Primary H1 heading & introduction
 * - Pre-configured interactive conversion interface (supports guest + auth flows)
 * - Factual feature benefits
 * - Step-by-step How-It-Works guide
 * - Visible, crawlable FAQ section
 * - Internal links grid ("Related Converters") with descriptive anchor text
 */

import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  Sparkles,
  Shield,
  Zap,
  CheckCircle2,
  ChevronDown,
  HelpCircle,
  ArrowRight,
  FileText,
  Lock,
} from 'lucide-react';
import AppShell from '../../components/layout/AppShell';
import SeoHead from '../../components/seo/SeoHead';
import Button from '../../components/ui/Button';
import FileDropzone from '../../components/ui/FileDropzone';
import { Card } from '../../components/ui/index';
import { useAuth } from '../../context/AuthContext';
import { conversionService } from '../../services/conversion';
import { pdfService } from '../../services/pdf';
import { getToolConfig } from '../../seo/tools';
import {
  formatFileSize,
  getGuestConversionsRemaining,
  recordGuestConversion,
} from '../../utils';

export default function ToolDetailPage() {
  const { tool = 'pdf-to-word' } = useParams<{ tool: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isConverting, setIsConverting] = useState(false);
  const [error, setError] = useState('');
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(0);
  const [guestRemaining, setGuestRemaining] = useState(getGuestConversionsRemaining());

  // Resolve tool SEO configuration
  const toolConfig = getToolConfig(tool);

  // Fallback metadata for PDF utility tools (like pdf-merge, pdf-split, etc.)
  const utilityTitles: Record<string, { name: string; desc: string }> = {
    'pdf-merge': { name: 'Merge PDF', desc: 'Combine multiple PDF files into one seamless document.' },
    'pdf-split': { name: 'Split PDF', desc: 'Extract pages or split PDF document into multiple files.' },
    'pdf-compress': { name: 'Compress PDF', desc: 'Reduce file size without loss of text sharpness.' },
    'pdf-rotate': { name: 'Rotate PDF', desc: 'Rotate PDF pages clockwise or counter-clockwise.' },
    'pdf-protect': { name: 'Protect PDF', desc: 'Add password security to your document.' },
    'pdf-unlock': { name: 'Unlock PDF', desc: 'Remove password restrictions from your PDF file.' },
  };

  useEffect(() => {
    setSelectedFile(null);
    setError('');
    setIsConverting(false);
  }, [tool]);

  if (!toolConfig && !utilityTitles[tool]) {
    return (
      <AppShell>
        <SeoHead
          title="Tool Not Found – VELTO Conversion"
          description="The requested conversion tool was not found on VELTO."
          noindex={true}
        />
        <div className="max-w-4xl mx-auto px-4 py-20 text-center space-y-4">
          <h1 className="text-3xl font-extrabold text-ivory-100">Tool Not Found</h1>
          <p className="text-muted-400">The tool URL you requested does not exist or has been moved.</p>
          <Link to="/tools" className="inline-block mt-4">
            <Button variant="primary" icon={<ArrowLeft className="w-4 h-4" />}>
              Explore Supported Tools
            </Button>
          </Link>
        </div>
      </AppShell>
    );
  }

  // Determine source and target format for dropzone and conversion logic
  const sourceFormat = toolConfig ? toolConfig.sourceFormat : 'pdf';
  const targetFormat = toolConfig ? toolConfig.targetFormat : 'docx';

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setError('');
  };

  const handleStartConversion = async () => {
    if (!selectedFile) return;

    if (!isAuthenticated && guestRemaining <= 0) {
      setError('Guest conversion limit reached. Create a free account to continue converting.');
      return;
    }

    setIsConverting(true);
    setError('');

    try {
      if (toolConfig) {
        // Core format conversion pair
        const job = isAuthenticated
          ? await conversionService.createJob(selectedFile, sourceFormat, targetFormat)
          : await conversionService.createGuestJob(selectedFile, sourceFormat, targetFormat);

        if (!isAuthenticated) {
          recordGuestConversion();
          setGuestRemaining(getGuestConversionsRemaining());
        }

        navigate(`/convert/processing?jobId=${job.id}`);
      } else {
        // PDF utility tool fallback
        const operation = tool.replace('pdf-', '');
        const responseJob = await pdfService.executePdfOperation(operation, selectedFile, null);
        if (responseJob.id) {
          navigate(`/convert/processing?jobId=${responseJob.id}`);
        }
      }
    } catch (err: any) {
      setIsConverting(false);
      setError(err.message || 'Failed to start conversion. Please check your file and try again.');
    }
  };

  const toolName = toolConfig ? toolConfig.name : utilityTitles[tool]?.name || tool;
  const toolH1 = toolConfig ? toolConfig.h1 : toolName;
  const toolIntro = toolConfig ? toolConfig.intro : utilityTitles[tool]?.desc || '';

  return (
    <AppShell>
      {/* Dynamic SEO Metadata & JSON-LD */}
      <SeoHead />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-12">
        {/* Breadcrumb Navigation */}
        <nav aria-label="Breadcrumb" className="flex items-center text-xs text-muted-400 space-x-2">
          <Link to="/" className="hover:text-gold-400 transition-colors">
            Home
          </Link>
          <span>/</span>
          <Link to="/tools" className="hover:text-gold-400 transition-colors">
            Tools
          </Link>
          <span>/</span>
          <span className="text-ivory-200 font-medium">{toolName}</span>
        </nav>

        {/* Page Header (H1) */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gold-500/10 border border-gold-500/20 text-gold-400 text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            VELTO Online Converter
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-ivory-100 tracking-tight leading-tight">
            {toolH1}
          </h1>
          <p className="text-base sm:text-lg text-muted-400 leading-relaxed">
            {toolIntro}
          </p>
        </div>

        {/* Conversion Action Card / Dropzone */}
        <div className="max-w-3xl mx-auto">
          <Card className="p-6 sm:p-8 space-y-6 shadow-2xl border-obsidian-800 bg-obsidian-900/90 backdrop-blur-sm">
            <div className="flex items-center justify-between border-b border-obsidian-800/80 pb-4 text-xs text-muted-400">
              <span className="flex items-center gap-2 text-ivory-200 font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-gold-500 animate-pulse"></span>
                Convert {sourceFormat.toUpperCase()} to {targetFormat.toUpperCase()}
              </span>
              {!isAuthenticated && (
                <span>
                  Guest conversions remaining: <strong className="text-gold-400">{guestRemaining}</strong>
                </span>
              )}
            </div>

            <FileDropzone
              onFileSelect={handleFileSelect}
              selectedFile={selectedFile}
              onClear={() => setSelectedFile(null)}
            />

            {selectedFile && (
              <div className="space-y-4 pt-4 border-t border-obsidian-800">
                <div className="flex items-center justify-between p-3.5 rounded-xl bg-obsidian-950 border border-obsidian-800 text-xs text-ivory-200">
                  <div className="flex items-center gap-3 truncate">
                    <FileText className="w-4 h-4 text-gold-400 flex-shrink-0" />
                    <span className="truncate font-medium">{selectedFile.name}</span>
                  </div>
                  <span className="text-muted-500 font-mono">{formatFileSize(selectedFile.size)}</span>
                </div>

                {error && (
                  <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 font-medium">
                    {error}
                  </div>
                )}

                <Button
                  variant="primary"
                  fullWidth
                  className="py-3.5 text-base font-semibold shadow-xl shadow-gold-500/20"
                  onClick={handleStartConversion}
                  loading={isConverting}
                >
                  Convert {toolConfig?.sourceLabel || sourceFormat.toUpperCase()} to {toolConfig?.targetLabel || targetFormat.toUpperCase()} Now
                </Button>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-center gap-6 pt-2 text-xs text-muted-500 border-t border-obsidian-800/60">
              <span className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-gold-400" /> 256-bit Encrypted SSL
              </span>
              <span className="flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-gold-400" /> Fast Cloud Conversion
              </span>
              <span className="flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-gold-400" /> Auto-Deleted Files
              </span>
            </div>
          </Card>
        </div>

        {/* Feature Benefits Grid */}
        {toolConfig?.features && toolConfig.features.length > 0 && (
          <section className="space-y-6 pt-6">
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-bold text-ivory-100">Why Use VELTO {toolName}?</h2>
              <p className="text-sm text-muted-400 max-w-2xl mx-auto">
                Engineered for maximum fidelity, rapid performance, and strict privacy.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {toolConfig.features.map((feat, idx) => (
                <div
                  key={idx}
                  className="p-6 rounded-2xl bg-obsidian-900 border border-obsidian-800 flex items-start gap-4 hover:border-gold-500/30 transition-all"
                >
                  <div className="w-10 h-10 rounded-xl bg-gold-500/10 border border-gold-500/20 flex items-center justify-center text-gold-400 flex-shrink-0">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-ivory-100 mb-1">Feature Highlight</h3>
                    <p className="text-sm text-muted-400 leading-relaxed">{feat}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* How It Works Section */}
        {toolConfig?.steps && toolConfig.steps.length > 0 && (
          <section className="space-y-6 py-6 border-t border-obsidian-800/80">
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-bold text-ivory-100">
                How to Convert {toolConfig.sourceLabel} to {toolConfig.targetLabel}
              </h2>
              <p className="text-sm text-muted-400">Follow 3 simple steps to complete your file conversion online.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {toolConfig.steps.map((stepText, idx) => (
                <div
                  key={idx}
                  className="relative p-6 rounded-2xl bg-obsidian-900 border border-obsidian-800 text-center space-y-3"
                >
                  <div className="w-12 h-12 rounded-full bg-gold-500/10 border border-gold-500/30 text-gold-400 text-lg font-extrabold flex items-center justify-center mx-auto">
                    {idx + 1}
                  </div>
                  <p className="text-sm text-ivory-200 leading-relaxed font-medium">{stepText}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* FAQ Accordion Section */}
        {toolConfig?.faqs && toolConfig.faqs.length > 0 && (
          <section className="space-y-6 py-6 border-t border-obsidian-800/80">
            <div className="text-center space-y-2">
              <div className="inline-flex items-center gap-1.5 text-xs text-gold-400 font-semibold uppercase tracking-wider">
                <HelpCircle className="w-3.5 h-3.5" /> Frequently Asked Questions
              </div>
              <h2 className="text-2xl font-bold text-ivory-100">
                Questions About {toolName}
              </h2>
            </div>

            <div className="max-w-3xl mx-auto space-y-3">
              {toolConfig.faqs.map((faq, idx) => {
                const isOpen = openFaqIndex === idx;
                return (
                  <div
                    key={idx}
                    className="rounded-2xl bg-obsidian-900 border border-obsidian-800 overflow-hidden transition-colors"
                  >
                    <button
                      onClick={() => setOpenFaqIndex(isOpen ? null : idx)}
                      className="w-full px-6 py-4.5 flex items-center justify-between text-left focus:outline-none"
                    >
                      <span className="text-sm sm:text-base font-bold text-ivory-100 pr-4">
                        {faq.question}
                      </span>
                      <ChevronDown
                        className={`w-5 h-5 text-gold-400 transition-transform duration-200 flex-shrink-0 ${
                          isOpen ? 'rotate-180' : ''
                        }`}
                      />
                    </button>
                    <AnimatePresence>
                      {isOpen && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="px-6 pb-5 pt-1 text-sm text-muted-400 leading-relaxed border-t border-obsidian-800/50"
                        >
                          {faq.answer}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Related Converters Grid (Internal Links) */}
        {toolConfig?.relatedSlugs && toolConfig.relatedSlugs.length > 0 && (
          <section className="space-y-6 py-6 border-t border-obsidian-800/80">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-ivory-100">Related Online Converters</h2>
                <p className="text-xs text-muted-400 mt-1">
                  Try other supported file conversion tools on VELTO.
                </p>
              </div>
              <Link to="/tools" className="text-xs text-gold-400 font-semibold hover:underline flex items-center gap-1">
                View All Tools <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {toolConfig.relatedSlugs.map((relSlug) => {
                const relConfig = getToolConfig(relSlug);
                if (!relConfig) return null;
                return (
                  <Link
                    key={relSlug}
                    to={`/tools/${relConfig.slug}`}
                    className="group p-4 rounded-xl bg-obsidian-900 border border-obsidian-800 hover:border-gold-500/40 hover:bg-obsidian-850 transition-all block"
                  >
                    <h3 className="text-sm font-bold text-ivory-200 group-hover:text-gold-400 transition-colors flex items-center justify-between">
                      <span>{relConfig.name}</span>
                      <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </h3>
                    <p className="text-xs text-muted-500 mt-1 line-clamp-2">
                      Convert {relConfig.sourceLabel} to {relConfig.targetLabel} online.
                    </p>
                  </Link>
                );
              })}
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}
