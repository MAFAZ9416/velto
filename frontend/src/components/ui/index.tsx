/**
 * VELTO UI — Card, Badge, Modal, Select, ProgressBar, Skeleton, EmptyState
 */

import React, { useEffect } from 'react';
import { cn } from '../../utils';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import type { JobStatus } from '../../types';

// ── Card ──────────────────────────────────────────────────────────────────────

interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  gold?: boolean;
  onClick?: () => void;
}

export function Card({ children, className, hover = false, gold = false, onClick }: CardProps) {
  return (
    <div
      className={cn(
        'bg-velto-surface border rounded-xl p-5 transition-all duration-200',
        gold ? 'border-velto-border' : 'border-velto-surface-4',
        hover && 'hover:border-velto-border hover:shadow-[0_0_20px_rgba(212,175,55,0.04)] cursor-pointer',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {children}
    </div>
  );
}

// ── Badge ─────────────────────────────────────────────────────────────────────

const statusColors: Record<string, string> = {
  completed: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  failed: 'bg-red-500/10 text-red-400 border-red-500/20',
  cancelled: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
  processing: 'bg-velto-gold/10 text-velto-gold border-velto-gold/20',
  started: 'bg-velto-gold/10 text-velto-gold border-velto-gold/20',
  pending: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
  queued: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  retrying: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  cancel_requested: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
  expired: 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20',
};

interface BadgeProps {
  status?: JobStatus | string;
  children?: React.ReactNode;
  className?: string;
  variant?: 'status' | 'gold' | 'neutral';
}

export function Badge({ status, children, className, variant = 'status' }: BadgeProps) {
  const colorClass =
    variant === 'gold'
      ? 'bg-velto-gold/10 text-velto-gold border-velto-gold/20'
      : variant === 'neutral'
      ? 'bg-velto-surface-3 text-velto-muted border-velto-surface-4'
      : status
      ? statusColors[status] || statusColors.pending
      : statusColors.pending;

  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium border',
        colorClass,
        className
      )}
    >
      {children || (status ? status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ') : '')}
    </span>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────────

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  maxWidth?: string;
}

export function Modal({ isOpen, onClose, title, children, maxWidth = 'max-w-md' }: ModalProps) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            className={cn(
              'relative bg-velto-surface border border-velto-surface-4 rounded-xl shadow-2xl w-full',
              maxWidth
            )}
            role="dialog"
            aria-modal="true"
            aria-label={title}
          >
            {title && (
              <div className="flex items-center justify-between p-5 border-b border-velto-surface-4">
                <h3 className="text-lg font-semibold text-velto-ivory">{title}</h3>
                <button
                  onClick={onClose}
                  className="text-velto-dim hover:text-velto-muted transition-colors p-1 rounded-lg hover:bg-velto-surface-3"
                  aria-label="Close dialog"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            )}
            <div className="p-5">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

// ── Select ────────────────────────────────────────────────────────────────────

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  label?: string;
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  error?: string;
  className?: string;
  id?: string;
}

export function Select({ label, options, value, onChange, placeholder, error, className, id }: SelectProps) {
  const selectId = id || label?.toLowerCase().replace(/\s+/g, '-');

  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={selectId} className="block text-sm font-medium text-velto-text">
          {label}
        </label>
      )}
      <select
        id={selectId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          'w-full bg-velto-surface-2 border border-velto-surface-4 rounded-lg px-4 py-3 text-[15px] text-velto-ivory',
          'focus:border-velto-gold focus:ring-2 focus:ring-velto-gold/15 focus:outline-none',
          'hover:border-velto-surface-5 transition-all duration-200 cursor-pointer appearance-none',
          error && 'border-red-500/50',
          className
        )}
        aria-invalid={!!error}
      >
        {placeholder && (
          <option value="" disabled className="text-velto-dim bg-velto-surface-2">
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} className="bg-velto-surface-2">
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}

// ── ProgressBar ───────────────────────────────────────────────────────────────

interface ProgressBarProps {
  value: number;
  max?: number;
  showLabel?: boolean;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
  className?: string;
}

export function ProgressBar({
  value,
  max = 100,
  showLabel = false,
  label,
  size = 'md',
  animated = true,
  className,
}: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const heights = { sm: 'h-1', md: 'h-2', lg: 'h-3' };

  return (
    <div className={cn('w-full', className)}>
      {(showLabel || label) && (
        <div className="flex justify-between items-center mb-1.5">
          {label && <span className="text-sm text-velto-muted">{label}</span>}
          {showLabel && <span className="text-sm font-medium text-velto-gold">{Math.round(percentage)}%</span>}
        </div>
      )}
      <div className={cn('w-full bg-velto-surface-3 rounded-full overflow-hidden', heights[size])}>
        <div
          className={cn(
            'h-full rounded-full velto-gold-gradient transition-all duration-500 ease-out',
            animated && percentage < 100 && 'relative overflow-hidden after:absolute after:inset-0 after:bg-gradient-to-r after:from-transparent after:via-white/15 after:to-transparent after:animate-[velto-shimmer_2s_ease-in-out_infinite]'
          )}
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        />
      </div>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

interface SkeletonProps {
  className?: string;
  width?: string;
  height?: string;
}

export function Skeleton({ className, width, height }: SkeletonProps) {
  return (
    <div
      className={cn('velto-shimmer rounded-lg', className)}
      style={{ width, height }}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="bg-velto-surface border border-velto-surface-4 rounded-xl p-5 space-y-4">
      <Skeleton className="h-4 w-2/3" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-4/5" />
      <div className="flex gap-2 pt-2">
        <Skeleton className="h-8 w-20 rounded-md" />
        <Skeleton className="h-8 w-20 rounded-md" />
      </div>
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      <div className="flex gap-4 pb-3 border-b border-velto-surface-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 py-2">
          {[1, 2, 3, 4, 5].map((j) => (
            <Skeleton key={j} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

// ── EmptyState ────────────────────────────────────────────────────────────────

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 px-6 text-center', className)}>
      {icon && (
        <div className="mb-5 text-velto-dim">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-velto-ivory mb-2">{title}</h3>
      {description && (
        <p className="text-velto-muted max-w-md mb-6">{description}</p>
      )}
      {action}
    </div>
  );
}

// ── PasswordStrength ──────────────────────────────────────────────────────────

import { getPasswordStrength } from '../../utils';

interface PasswordStrengthProps {
  password: string;
}

export function PasswordStrength({ password }: PasswordStrengthProps) {
  if (!password) return null;

  const { score, label } = getPasswordStrength(password);
  const colors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-emerald-400', 'bg-emerald-500'];

  return (
    <div className="space-y-1.5">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={cn(
              'h-1 flex-1 rounded-full transition-all duration-300',
              i <= score - 1 ? colors[score] : 'bg-velto-surface-4'
            )}
          />
        ))}
      </div>
      <p className={cn('text-xs', score <= 1 ? 'text-red-400' : score === 2 ? 'text-yellow-400' : 'text-emerald-400')}>
        {label}
      </p>
    </div>
  );
}
