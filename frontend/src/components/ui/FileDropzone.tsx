/**
 * VELTO UI — FileDropzone Component
 * Premium drag-and-drop file upload with gold accents.
 */

import React, { useCallback, useRef, useState } from 'react';
import { cn } from '../../utils';
import { Upload, FileText, X, Image, FileSpreadsheet, File } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { formatFileSize, getFileExtension } from '../../utils';

interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  maxSize?: number;
  selectedFile?: File | null;
  onClear?: () => void;
  className?: string;
  compact?: boolean;
}

const FORMAT_ICONS: Record<string, React.ReactNode> = {
  pdf: <FileText className="h-8 w-8" />,
  docx: <FileText className="h-8 w-8" />,
  doc: <FileText className="h-8 w-8" />,
  xlsx: <FileSpreadsheet className="h-8 w-8" />,
  xls: <FileSpreadsheet className="h-8 w-8" />,
  csv: <FileSpreadsheet className="h-8 w-8" />,
  jpg: <Image className="h-8 w-8" />,
  jpeg: <Image className="h-8 w-8" />,
  png: <Image className="h-8 w-8" />,
  webp: <Image className="h-8 w-8" />,
  gif: <Image className="h-8 w-8" />,
  bmp: <Image className="h-8 w-8" />,
  tiff: <Image className="h-8 w-8" />,
};

export default function FileDropzone({
  onFileSelect,
  accept,
  maxSize = 52_428_800,
  selectedFile,
  onClear,
  className,
  compact = false,
}: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      setError(null);
      if (maxSize && file.size > maxSize) {
        setError(`File is too large. Maximum size is ${formatFileSize(maxSize)}.`);
        return;
      }
      onFileSelect(file);
    },
    [maxSize, onFileSelect]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      if (inputRef.current) inputRef.current.value = '';
    },
    [handleFile]
  );

  if (selectedFile) {
    const ext = getFileExtension(selectedFile.name);
    const icon = FORMAT_ICONS[ext] || <File className="h-8 w-8" />;

    return (
      <AnimatePresence mode="wait">
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.97 }}
          className={cn(
            'bg-velto-surface border border-velto-border rounded-xl p-5 flex items-center gap-4',
            className
          )}
        >
          <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-velto-gold/10 text-velto-gold flex items-center justify-center">
            {icon}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-velto-ivory font-medium truncate">{selectedFile.name}</p>
            <p className="text-sm text-velto-muted">
              {formatFileSize(selectedFile.size)} • {ext.toUpperCase()}
            </p>
          </div>
          {onClear && (
            <button
              onClick={onClear}
              className="flex-shrink-0 p-2 rounded-lg text-velto-dim hover:text-velto-muted hover:bg-velto-surface-3 transition-colors"
              aria-label="Remove file"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </motion.div>
      </AnimatePresence>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload file"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        className={cn(
          'relative border-2 border-dashed rounded-xl transition-all duration-300 cursor-pointer group',
          compact ? 'p-6' : 'p-10',
          isDragging
            ? 'border-velto-gold bg-velto-gold/5 shadow-[0_0_30px_rgba(212,175,55,0.08)]'
            : 'border-velto-surface-4 hover:border-velto-border hover:bg-velto-surface/50'
        )}
      >
        <div className="flex flex-col items-center text-center">
          <div
            className={cn(
              'rounded-xl p-3 mb-4 transition-colors duration-300',
              isDragging
                ? 'bg-velto-gold/15 text-velto-gold'
                : 'bg-velto-surface-3 text-velto-dim group-hover:text-velto-gold group-hover:bg-velto-gold/10'
            )}
          >
            <Upload className={compact ? 'h-6 w-6' : 'h-8 w-8'} />
          </div>
          <p className="text-velto-ivory font-medium mb-1">
            {isDragging ? 'Drop your file here' : 'Upload your file'}
          </p>
          <p className="text-sm text-velto-muted mb-3">
            Drag & drop or{' '}
            <span className="text-velto-gold">browse</span>
          </p>
          <p className="text-xs text-velto-dim">
            PDF • DOCX • XLSX • JPG • PNG • and more
          </p>
          <p className="text-xs text-velto-dim mt-0.5">
            Max {formatFileSize(maxSize)}
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept={accept}
          onChange={handleInputChange}
          aria-hidden="true"
        />
      </div>
      {error && (
        <p className="text-sm text-red-400 text-center">{error}</p>
      )}
    </div>
  );
}
