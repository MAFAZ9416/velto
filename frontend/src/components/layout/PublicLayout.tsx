/**
 * VELTO Layout — Public Layout (for auth pages, landing, pricing)
 */

import { NavLink } from 'react-router-dom';
import { Zap } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface PublicLayoutProps {
  children: React.ReactNode;
  showNav?: boolean;
}

export default function PublicLayout({ children, showNav = true }: PublicLayoutProps) {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-velto-black flex flex-col">
      {showNav && (
        <header className="border-b border-velto-surface-4/50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <NavLink to="/" className="flex items-center gap-2 group">
                <div className="h-8 w-8 rounded-lg velto-gold-gradient flex items-center justify-center">
                  <Zap className="h-4 w-4 text-velto-black" />
                </div>
                <div className="flex items-baseline gap-1">
                  <span className="text-lg font-bold tracking-wide text-velto-ivory">
                    VELTO
                  </span>
                  <span className="text-sm font-light text-velto-dim hidden sm:inline">
                    Conversion
                  </span>
                </div>
              </NavLink>

              <nav className="flex items-center gap-1 sm:gap-2">
                <NavLink
                  to="/tools"
                  className="px-3 py-2 text-sm text-velto-muted hover:text-velto-ivory transition-colors rounded-lg hover:bg-velto-surface-3"
                >
                  Tools
                </NavLink>
                <NavLink
                  to="/pricing"
                  className="px-3 py-2 text-sm text-velto-muted hover:text-velto-ivory transition-colors rounded-lg hover:bg-velto-surface-3"
                >
                  Pricing
                </NavLink>
                {isAuthenticated ? (
                  <NavLink
                    to="/dashboard"
                    className="ml-1 px-4 py-2 text-sm font-medium text-velto-black bg-velto-gold rounded-lg hover:bg-velto-gold-light transition-colors"
                  >
                    Dashboard
                  </NavLink>
                ) : (
                  <>
                    <NavLink
                      to="/login"
                      className="px-3 py-2 text-sm text-velto-muted hover:text-velto-ivory transition-colors rounded-lg hover:bg-velto-surface-3"
                    >
                      Log In
                    </NavLink>
                    <NavLink
                      to="/register"
                      className="ml-1 px-4 py-2 text-sm font-medium text-velto-black bg-velto-gold rounded-lg hover:bg-velto-gold-light transition-colors"
                    >
                      Sign Up
                    </NavLink>
                  </>
                )}
              </nav>
            </div>
          </div>
        </header>
      )}
      <main className="flex-1">{children}</main>
    </div>
  );
}
