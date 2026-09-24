/**
 * VELTO Layout — Desktop Sidebar
 */

import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '../../utils';
import {
  LayoutDashboard,
  ArrowRightLeft,
  FolderOpen,
  Wrench,
  User,
  Settings,
  Crown,
  HardDrive,
  Zap,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { formatFileSize } from '../../utils';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/convert', label: 'Convert', icon: ArrowRightLeft },
  { to: '/conversions', label: 'My Conversions', icon: FolderOpen },
  { to: '/tools', label: 'Tools', icon: Wrench },
  { to: '/account', label: 'Account', icon: User },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  const location = useLocation();
  const { profile } = useAuth();

  const storageUsed = profile?.storage_used_bytes || 0;
  const storageLimit = profile?.storage_limit_bytes || 524_288_000;
  const storagePercent = Math.min(100, (storageUsed / storageLimit) * 100);
  const conversionsUsed = profile?.daily_conversion_count || 0;
  const conversionsLimit = profile?.daily_conversion_limit || 50;

  return (
    <aside className="hidden lg:flex flex-col w-64 bg-velto-black-2 border-r border-velto-surface-4 h-screen sticky top-0 overflow-y-auto">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-velto-surface-4">
        <NavLink to="/dashboard" className="flex items-center gap-2 group">
          <div className="h-8 w-8 rounded-lg velto-gold-gradient flex items-center justify-center">
            <Zap className="h-4 w-4 text-velto-black" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-lg font-bold tracking-wide text-velto-ivory">
              VELTO
            </span>
            <span className="text-sm font-light text-velto-dim">
              Conversion
            </span>
          </div>
        </NavLink>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1" aria-label="Main navigation">
        {navItems.map(({ to, label, icon: Icon }) => {
          const isActive = location.pathname === to || location.pathname.startsWith(`${to}/`);
          return (
            <NavLink
              key={to}
              to={to}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group relative',
                isActive
                  ? 'text-velto-gold bg-velto-gold/8'
                  : 'text-velto-muted hover:text-velto-ivory hover:bg-velto-surface-3'
              )}
            >
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-velto-gold rounded-r" />
              )}
              <Icon className={cn('h-[18px] w-[18px]', isActive ? 'text-velto-gold' : 'text-velto-dim group-hover:text-velto-muted')} />
              {label}
            </NavLink>
          );
        })}
      </nav>

      {/* Usage & Plan */}
      <div className="px-4 pb-5 space-y-3">
        <div className="bg-velto-surface rounded-lg p-3.5 space-y-3 border border-velto-surface-4">
          {/* Storage */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-1.5 text-xs text-velto-muted">
                <HardDrive className="h-3 w-3" />
                Storage
              </div>
              <span className="text-xs text-velto-dim">
                {formatFileSize(storageUsed)} / {formatFileSize(storageLimit)}
              </span>
            </div>
            <div className="h-1 bg-velto-surface-3 rounded-full overflow-hidden">
              <div
                className="h-full velto-gold-gradient rounded-full transition-all"
                style={{ width: `${storagePercent}%` }}
              />
            </div>
          </div>

          {/* Conversions */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-1.5 text-xs text-velto-muted">
                <ArrowRightLeft className="h-3 w-3" />
                Daily
              </div>
              <span className="text-xs text-velto-dim">
                {conversionsUsed} / {conversionsLimit}
              </span>
            </div>
            <div className="h-1 bg-velto-surface-3 rounded-full overflow-hidden">
              <div
                className="h-full velto-gold-gradient rounded-full transition-all"
                style={{ width: `${Math.min(100, (conversionsUsed / conversionsLimit) * 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Upgrade */}
        <button className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-velto-gold/10 text-velto-gold text-sm font-medium border border-velto-gold/20 hover:bg-velto-gold/15 transition-colors">
          <Crown className="h-4 w-4" />
          Upgrade to Pro
        </button>
      </div>
    </aside>
  );
}
