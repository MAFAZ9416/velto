/**
 * VELTO Conversion — Root Application Component
 *
 * Mounts the AuthProvider and the full routing tree.
 * This replaces the Vite starter template that was here previously.
 */

import { AuthProvider } from './context/AuthContext';
import AppRoutes from './routes';

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
