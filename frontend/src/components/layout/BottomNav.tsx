/**
 * VELTO Layout — Mobile Bottom Navigation
 */

import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '../../utils';
import {
  LayoutDashboard,
  ArrowRightLeft,
  FolderOpen,
  Wrench,
  User,
} from 'lucide-react';

const items = [
  { to: '/dashboard', label: 'Home', icon: LayoutDashboard },
  { to: '/convert', label: 'Convert', icon: ArrowRightLeft },
  { to: '/conversions', label: 'Files', icon: FolderOpen },
  { to: '/tools', label: 'Tools', icon: Wrench },
  { to: '/account', label: 'Account', icon: User },
];

export default function BottomNav() {
  const location = useLocation();

  return (
    <nav
      className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-velto-black-2/95 backdrop-blur-lg border-t border-velto-surface-4 pb-safe"
      aria-label="Mobile navigation"
    >
      <div className="flex items-center justify-around px-2 py-1.5">
        {items.map(({ to, label, icon: Icon }) => {
          const isActive = location.pathname === to || location.pathname.startsWith(`${to}/`);
          return (
            <NavLink
              key={to}
              to={to}
              className={cn(
                'flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-lg min-w-[56px] transition-colors',
                isActive ? 'text-velto-gold' : 'text-velto-dim'
              )}
            >
              <div className="relative">
                <Icon className="h-5 w-5" />
                {isActive && (
                  <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-4 h-0.5 bg-velto-gold rounded-full" />
                )}
              </div>
              <span className="text-[10px] font-medium">{label}</span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
