/**
 * VELTO Layout — AppShell (Authenticated layout wrapper)
 */

import Sidebar from './Sidebar';
import TopBar from './TopBar';
import BottomNav from './BottomNav';

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-velto-black">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen lg:min-w-0">
        <TopBar />
        <main className="flex-1 p-4 lg:p-6 pb-24 lg:pb-6">
          {children}
        </main>
        <BottomNav />
      </div>
    </div>
  );
}
