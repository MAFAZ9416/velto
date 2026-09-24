/**
 * VELTO Layout — Top Bar (Mobile header + desktop search/notifications)
 */

import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { cn } from '../../utils';
import {
  Bell,
  LogOut,
  Menu,
  Search,
  X,
  Zap,
  LayoutDashboard,
  ArrowRightLeft,
  FolderOpen,
  Wrench,
  User,
  Settings,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const mobileMenuItems = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/convert', label: 'Convert', icon: ArrowRightLeft },
  { to: '/conversions', label: 'My Conversions', icon: FolderOpen },
  { to: '/tools', label: 'Tools', icon: Wrench },
  { to: '/account', label: 'Account', icon: User },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function TopBar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <>
      <header className="sticky top-0 z-30 bg-velto-black-2/90 backdrop-blur-lg border-b border-velto-surface-4">
        <div className="flex items-center justify-between h-14 px-4 lg:px-6">
          {/* Mobile: Logo + Menu */}
          <div className="flex items-center gap-3 lg:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-velto-muted hover:text-velto-ivory hover:bg-velto-surface-3 transition-colors"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <NavLink to="/dashboard" className="flex items-center gap-1.5">
              <div className="h-6 w-6 rounded-md velto-gold-gradient flex items-center justify-center">
                <Zap className="h-3.5 w-3.5 text-velto-black" />
              </div>
              <span className="font-bold text-sm text-velto-ivory">VELTO</span>
            </NavLink>
          </div>

          {/* Desktop: Search */}
          <div className="hidden lg:flex items-center flex-1 max-w-md">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-velto-dim" />
              <input
                type="search"
                placeholder="Search conversions..."
                className="w-full bg-velto-surface-2 border border-velto-surface-4 rounded-lg pl-9 pr-4 py-2 text-sm text-velto-ivory placeholder:text-velto-dim focus:border-velto-gold/50 focus:ring-1 focus:ring-velto-gold/15 transition-colors"
              />
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-2">
            <button
              className="p-2 rounded-lg text-velto-dim hover:text-velto-muted hover:bg-velto-surface-3 transition-colors relative"
              aria-label="Notifications"
            >
              <Bell className="h-5 w-5" />
            </button>
            <div className="hidden lg:flex items-center gap-3 ml-2 pl-3 border-l border-velto-surface-4">
              <span className="text-sm text-velto-muted truncate max-w-[160px]">
                {user?.email}
              </span>
              <button
                onClick={handleLogout}
                className="p-2 rounded-lg text-velto-dim hover:text-red-400 hover:bg-red-500/10 transition-colors"
                aria-label="Log out"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 z-20 pt-14">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
          />
          <nav className="relative bg-velto-black-2 border-b border-velto-surface-4 p-4 space-y-1 shadow-2xl">
            {mobileMenuItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'text-velto-gold bg-velto-gold/8'
                      : 'text-velto-muted hover:text-velto-ivory hover:bg-velto-surface-3'
                  )
                }
              >
                <Icon className="h-5 w-5" />
                {label}
              </NavLink>
            ))}
            <hr className="border-velto-surface-4 my-2" />
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                handleLogout();
              }}
              className="flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-red-400 hover:bg-red-500/10 transition-colors w-full"
            >
              <LogOut className="h-5 w-5" />
              Log Out
            </button>
          </nav>
        </div>
      )}
    </>
  );
}
