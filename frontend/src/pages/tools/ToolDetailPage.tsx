/**
 * VELTO — Tool Detail Page
 * Specific tool interface with file upload, options, processing & download.
 */

import { useState, useRef, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Download, CheckCircle2, Loader2, Sparkles, Layers, Shield } from 'lucide-react';
import AppShell from '../../components/layout/AppShell';
import Button from '../../components/ui/Button';
import FileDropzone from '../../components/ui/FileDropzone';
import { ProgressBar, Card } from '../../components/ui/index';
import { pdfService } from '../../services/pdf';
import { conversionService } from '../../services/conversion';
import { formatFileSize } from '../../utils';
import type { ConversionJob } from '../../types';

export default function ToolDetailPage() {
  const { tool = 'pdf-merge' } = useParams<{ tool: string }>();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [job, setJob] = useState<ConversionJob | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const toolTitles: Record<string, { name: string; desc: string }> = {
    'pdf-merge': { name: 'Merge PDF', desc: 'Combine multiple PDF files into one seamless document.' },
    'pdf-split': { name: 'Split PDF', desc: 'Extract pages or split PDF document into multiple files.' },
    'pdf-compress': { name: 'Compress PDF', desc: 'Reduce file size without loss of text sharpness.' },
    'pdf-rotate': { name: 'Rotate PDF', desc: 'Rotate PDF pages clockwise or counter-clockwise.' },
    'pdf-protect': { name: 'Protect PDF', desc: 'Add 256-bit encryption password to your document.' },
    'pdf-unlock': { name: 'Unlock PDF', desc: 'Remove password restrictions from your PDF file.' },
    'ocr-pdf': { name: 'OCR PDF Scanner', desc: 'Extract searchable text from scanned PDFs.' },
    'ocr-image': { name: 'Image Text Extractor', desc: 'Extract text content from images and photos.' },
  };

  const toolMeta = toolTitles[tool] || {
    name: tool.replace('-', ' ').toUpperCase(),
    desc: 'Perform advanced document processing with VELTO engine.',
  };

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setError('');
    setJob(null);
    setDownloadUrl(null);
  };

  const handleExecuteTool = async () => {
    if (!selectedFile) return;
    setIsProcessing(true);
    setProgress(10);
    setError('');

    try {
      if (tool.startsWith('pdf-')) {
        const operation = tool.replace('pdf-', '');
        const responseJob = await pdfService.executePdfOperation(operation, selectedFile, null);
        if (responseJob.id) {
          // Poll for completion
          intervalRef.current = setInterval(async () => {
            try {
              const status = await conversionService.getJobStatus(responseJob.id);
              setJob(status);
              setProgress(status.progress || 60);
              if (status.status === 'completed') {
                if (intervalRef.current) clearInterval(intervalRef.current);
                setIsProcessing(false);
                setProgress(100);
              } else if (status.status === 'failed') {
                if (intervalRef.current) clearInterval(intervalRef.current);
                setIsProcessing(false);
                setError(status.error_message || 'Tool execution failed.');
              }
            } catch {
              if (intervalRef.current) clearInterval(intervalRef.current);
              setIsProcessing(false);
            }
          }, 1500);
        }
      } else {
        // Fallback for general file tool using createJob
        const newJob = await conversionService.createJob(selectedFile, 'pdf', 'docx');
        setJob(newJob);
        setIsProcessing(false);
        setProgress(100);
      }
    } catch (err: any) {
      setIsProcessing(false);
      setError(err.message || 'Operation failed. Please try again.');
    }
  };

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Back Link */}
        <Link
          to="/tools"
          className="inline-flex items-center gap-2 text-sm text-muted-400 hover:text-gold-400 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Tools Suite
        </Link>

        {/* Header */}
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gold-500/10 border border-gold-500/20 text-gold-400 text-xs font-semibold uppercase tracking-wider mb-3">
            <Sparkles className="w-3.5 h-3.5" />
            VELTO Tool
          </div>
          <h1 className="text-3xl font-extrabold text-ivory-100 tracking-tight">
            {toolMeta.name}
          </h1>
          <p className="text-muted-400 text-sm mt-1">
            {toolMeta.desc}
          </p>
        </div>

        {/* File Dropzone */}
        <Card className="p-8 space-y-6">
          <FileDropzone
            onFileSelect={handleFileSelect}
            selectedFile={selectedFile}
            onClear={() => setSelectedFile(null)}
          />

          {selectedFile && (
            <div className="space-y-4 pt-4 border-t border-obsidian-800">
              <div className="flex items-center justify-between p-3 rounded-xl bg-obsidian-950 border border-obsidian-800 text-xs text-ivory-200">
                <div className="flex items-center gap-3 truncate">
                  <Layers className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span className="truncate font-medium">{selectedFile.name}</span>
                </div>
                <span className="text-muted-500">{formatFileSize(selectedFile.size)}</span>
              </div>

              {error && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                  {error}
                </div>
              )}

              {/* Progress */}
              {isProcessing && (
                <div className="space-y-2 pt-2">
                  <div className="flex justify-between text-xs text-muted-400">
                    <span className="flex items-center gap-1.5 text-gold-400">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" /> Processing file...
                    </span>
                    <span>{progress}%</span>
                  </div>
                  <ProgressBar value={progress} />
                </div>
              )}

              {/* Completed Download */}
              {(job?.status === 'completed' || downloadUrl) && (
                <div className="p-6 rounded-xl bg-gold-500/10 border border-gold-500/30 text-center space-y-3">
                  <div className="w-12 h-12 rounded-full bg-gold-500/20 text-gold-400 flex items-center justify-center mx-auto">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                  <h3 className="text-base font-bold text-ivory-100">Operation Completed!</h3>
                  <p className="text-xs text-muted-400">Your processed file is ready to download.</p>
                  {job && (
                    <Button
                      variant="primary"
                      icon={<Download className="w-4 h-4" />}
                      onClick={() => conversionService.downloadFile(job.id)}
                    >
                      Download Processed File
                    </Button>
                  )}
                  {downloadUrl && (
                    <a href={downloadUrl} download>
                      <Button variant="primary" icon={<Download className="w-4 h-4" />}>
                        Download File
                      </Button>
                    </a>
                  )}
                </div>
              )}

              {/* Action Button */}
              {!isProcessing && job?.status !== 'completed' && !downloadUrl && (
                <Button
                  variant="primary"
                  fullWidth
                  className="py-3 shadow-lg shadow-gold-500/20"
                  onClick={handleExecuteTool}
                >
                  Execute {toolMeta.name}
                </Button>
              )}
            </div>
          )}
        </Card>

        {/* Security badge */}
        <div className="flex items-center justify-center gap-2 text-xs text-muted-500 py-4">
          <Shield className="w-4 h-4 text-gold-400" />
          <span>256-bit encrypted transfer. Files are auto-deleted after processing.</span>
        </div>
      </div>
    </AppShell>
  );
}
