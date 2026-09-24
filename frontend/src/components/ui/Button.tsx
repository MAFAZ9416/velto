/**
 * VELTO UI — Button Component
 * Premium button with gold, secondary, ghost, and danger variants.
 */

import React from 'react';
import { cn } from '../../utils';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
  fullWidth?: boolean;
}

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  iconRight,
  fullWidth = false,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  const baseClasses =
    'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-velto-gold focus-visible:ring-offset-2 focus-visible:ring-offset-velto-black disabled:opacity-50 disabled:cursor-not-allowed select-none';

  const variants = {
    primary:
      'bg-velto-gold text-velto-black hover:bg-velto-gold-light active:bg-velto-gold-muted shadow-sm hover:shadow-md',
    secondary:
      'bg-velto-surface-3 text-velto-ivory border border-velto-surface-4 hover:border-velto-border hover:bg-velto-surface-hover',
    ghost:
      'text-velto-muted hover:text-velto-ivory hover:bg-velto-surface-3',
    danger:
      'bg-velto-error/10 text-red-400 border border-red-500/20 hover:bg-velto-error/20 hover:border-red-500/40',
  };

  const sizes = {
    sm: 'text-sm px-3 py-1.5 gap-1.5',
    md: 'text-sm px-5 py-2.5 gap-2',
    lg: 'text-base px-7 py-3 gap-2.5',
  };

  return (
    <button
      className={cn(
        baseClasses,
        variants[variant],
        sizes[size],
        fullWidth && 'w-full',
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : icon ? (
        <span className="shrink-0">{icon}</span>
      ) : null}
      {children}
      {iconRight && !loading && (
        <span className="shrink-0">{iconRight}</span>
      )}
    </button>
  );
}
