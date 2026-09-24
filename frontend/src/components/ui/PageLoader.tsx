/**
 * VELTO UI — PageLoader Component
 * Full-page loading spinner with VELTO branding.
 */

export default function PageLoader() {
  return (
    <div className="fixed inset-0 bg-velto-black flex items-center justify-center z-50">
      <div className="flex flex-col items-center gap-6">
        <div className="relative">
          <div className="h-12 w-12 rounded-full border-2 border-velto-surface-4" />
          <div className="absolute inset-0 h-12 w-12 rounded-full border-2 border-transparent border-t-velto-gold animate-spin" />
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-lg font-semibold tracking-wide text-velto-ivory">
            VELTO
          </span>
          <span className="text-lg font-light text-velto-muted">
            Conversion
          </span>
        </div>
      </div>
    </div>
  );
}
