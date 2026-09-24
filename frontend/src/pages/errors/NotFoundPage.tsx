/**
 * VELTO — 404 Not Found Page
 */

import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileQuestion, ArrowLeft, Home, Zap } from 'lucide-react';
import Button from '../../components/ui/Button';

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-obsidian-950 flex flex-col justify-between p-6">
      {/* Top Header */}
      <div className="max-w-7xl mx-auto w-full flex items-center justify-between py-4">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gold-500/10 border border-gold-500/30 flex items-center justify-center text-gold-400">
            <Zap className="w-4 h-4" />
          </div>
          <span className="font-extrabold text-xl tracking-tight text-ivory-100">
            VELTO<span className="text-gold-400">.</span>
          </span>
        </Link>
      </div>

      {/* Main Content */}
      <div className="max-w-md mx-auto text-center my-auto">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="w-24 h-24 rounded-3xl bg-gold-500/10 border border-gold-500/20 flex items-center justify-center text-gold-400 mx-auto mb-8 shadow-2xl shadow-gold-500/10"
        >
          <FileQuestion className="w-12 h-12" />
        </motion.div>

        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="gold-text-gradient font-black text-6xl tracking-widest block mb-2"
        >
          404
        </motion.span>

        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-2xl font-bold text-ivory-100 tracking-tight mb-3"
        >
          Page Not Found
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="text-muted-400 text-sm mb-8 leading-relaxed"
        >
          The page or converted file route you are looking for has been moved, deleted, or never existed.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="flex flex-col sm:flex-row items-center gap-3 justify-center"
        >
          <Link to="/" className="w-full sm:w-auto">
            <Button variant="primary" icon={<Home className="w-4 h-4" />} fullWidth>
              Return Home
            </Button>
          </Link>
          <button onClick={() => window.history.back()} className="w-full sm:w-auto">
            <Button variant="secondary" icon={<ArrowLeft className="w-4 h-4" />} fullWidth>
              Go Back
            </Button>
          </button>
        </motion.div>
      </div>

      {/* Footer */}
      <div className="text-center text-xs text-muted-600 py-4">
        &copy; {new Date().getFullYear()} VELTO Conversion. All rights reserved.
      </div>
    </div>
  );
}
