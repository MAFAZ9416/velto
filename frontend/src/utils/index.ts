/**
 * VELTO Conversion — Utility Functions
 */

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Merge Tailwind class names safely */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format file size in human-readable units */
export function formatFileSize(bytes: number | null | undefined): string {
  if (bytes == null || bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const value = bytes / Math.pow(1024, i);
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

/** Format date to readable string */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/** Format date with time */
export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Format relative time */
export function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(dateStr);
}

/** Get file extension from filename */
export function getFileExtension(filename: string): string {
  const parts = filename.split('.');
  return parts.length > 1 ? parts.pop()!.toLowerCase() : '';
}

/** Detect source format from file extension */
export function detectSourceFormat(filename: string): string | null {
  const ext = `.${getFileExtension(filename)}`;
  const formatMap: Record<string, string> = {
    '.pdf': 'pdf',
    '.docx': 'docx',
    '.doc': 'docx',
    '.xlsx': 'xlsx',
    '.xls': 'xlsx',
    '.pptx': 'pptx',
    '.ppt': 'pptx',
    '.jpg': 'jpg',
    '.jpeg': 'jpg',
    '.png': 'png',
    '.csv': 'csv',
    '.webp': 'webp',
    '.bmp': 'bmp',
    '.tiff': 'tiff',
    '.tif': 'tiff',
    '.gif': 'gif',
    '.txt': 'txt',
    '.html': 'html',
    '.htm': 'html',
    '.md': 'md',
    '.markdown': 'md',
  };
  return formatMap[ext] || null;
}

/** Get available target formats for a given source format */
export function getTargetFormats(
  sourceFormat: string,
  supportedFormats: Array<{ source: string; target: string }>
): string[] {
  return supportedFormats
    .filter((f) => f.source === sourceFormat)
    .map((f) => f.target);
}

/** Calculate password strength (0-4) */
export function getPasswordStrength(password: string): {
  score: number;
  label: string;
  color: string;
} {
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^a-zA-Z\d]/.test(password)) score++;
  score = Math.min(score, 4);

  const labels = ['Very Weak', 'Weak', 'Fair', 'Strong', 'Very Strong'];
  const colors = [
    'bg-red-500',
    'bg-orange-500',
    'bg-yellow-500',
    'bg-emerald-400',
    'bg-emerald-500',
  ];

  return {
    score,
    label: labels[score],
    color: colors[score],
  };
}

/** Guest conversion counter using localStorage */
const GUEST_KEY = 'velto_guest_conversions';
const GUEST_MAX = 3;

export function getGuestConversionsRemaining(): number {
  try {
    const stored = localStorage.getItem(GUEST_KEY);
    if (!stored) return GUEST_MAX;
    const { count, date } = JSON.parse(stored);
    const today = new Date().toISOString().split('T')[0];
    if (date !== today) return GUEST_MAX;
    return Math.max(0, GUEST_MAX - count);
  } catch {
    return GUEST_MAX;
  }
}

export function recordGuestConversion(): void {
  try {
    const today = new Date().toISOString().split('T')[0];
    const stored = localStorage.getItem(GUEST_KEY);
    let count = 1;
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed.date === today) {
        count = parsed.count + 1;
      }
    }
    localStorage.setItem(GUEST_KEY, JSON.stringify({ count, date: today }));
  } catch {
    // Fail silently
  }
}

/** Truncate a filename for display */
export function truncateFilename(name: string, maxLen = 30): string {
  if (name.length <= maxLen) return name;
  const ext = getFileExtension(name);
  const baseName = name.slice(0, name.length - ext.length - 1);
  const truncated = baseName.slice(0, maxLen - ext.length - 4);
  return `${truncated}...${ext ? `.${ext}` : ''}`;
}
