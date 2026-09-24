/**
 * VELTO — Pricing Page
 * Premium black + gold pricing plans with monthly/annual billing toggle, plan breakdown & FAQs.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Check, Zap, Crown, Shield, HelpCircle, ArrowRight, Sparkles } from 'lucide-react';
import PublicLayout from '../../components/layout/PublicLayout';
import Button from '../../components/ui/Button';

export default function PricingPage() {
  const [isAnnual, setIsAnnual] = useState(true);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const faqs = [
    {
      q: "Are my files secure during conversion?",
      a: "Absolutely. All transfers use enterprise 256-bit SSL encryption. Guest files are automatically purged from our servers within 1 hour, and logged-in user files within 24 hours (unless stored in your Pro vault)."
    },
    {
      q: "What file formats are supported?",
      a: "VELTO supports over 50+ formats including PDF, Word (DOCX), Excel (XLSX), PowerPoint (PPTX), Images (PNG, JPG, WEBP, SVG, TIFF), Text, CSV, HTML, and Markdown."
    },
    {
      q: "Can I cancel my Pro subscription anytime?",
      a: "Yes, you can cancel your subscription at any time from your Account Settings with one click. You will retain access until the end of your current billing period."
    },
    {
      q: "Is OCR (Text Recognition) included?",
      a: "OCR text extraction is included in the Pro plan, supporting multi-language scanned document text extraction directly into searchable PDF or Word files."
    },
    {
      q: "What payment methods do you accept?",
      a: "We accept all major credit/debit cards (Visa, MasterCard, American Express), Apple Pay, Google Pay, and PayPal."
    }
  ];

  return (
    <PublicLayout>
      <div className="min-h-screen py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gold-500/10 border border-gold-500/20 text-gold-400 text-xs font-medium tracking-wide uppercase mb-4"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Simple, Transparent Pricing
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-4xl sm:text-5xl font-extrabold text-ivory-100 tracking-tight"
          >
            Convert without limits. <br />
            <span className="gold-text-gradient">Choose your plan.</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-4 text-lg text-muted-400"
          >
            Start free with essential tools, or upgrade to Pro for lightning-fast batch processing and unlimited files.
          </motion.p>

          {/* Monthly / Annual Toggle */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.3 }}
            className="mt-8 inline-flex items-center p-1 rounded-xl bg-obsidian-800 border border-obsidian-700"
          >
            <button
              onClick={() => setIsAnnual(false)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                !isAnnual
                  ? 'bg-obsidian-900 text-ivory-100 shadow-sm border border-obsidian-600'
                  : 'text-muted-400 hover:text-ivory-200'
              }`}
            >
              Monthly Billing
            </button>
            <button
              onClick={() => setIsAnnual(true)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-all flex items-center gap-2 ${
                isAnnual
                  ? 'bg-gold-500 text-obsidian-950 shadow-md font-semibold'
                  : 'text-muted-400 hover:text-ivory-200'
              }`}
            >
              Annual Billing
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                isAnnual ? 'bg-obsidian-950 text-gold-400' : 'bg-gold-500/20 text-gold-400'
              }`}>
                Save 20%
              </span>
            </button>
          </motion.div>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-5xl mx-auto items-stretch">
          {/* Free Plan */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="rounded-2xl bg-obsidian-900/80 border border-obsidian-800 p-8 flex flex-col justify-between hover:border-obsidian-700 transition-colors shadow-xl"
          >
            <div>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-bold text-ivory-100">Free Tier</h3>
                  <p className="text-sm text-muted-400 mt-1">For casual quick file conversions</p>
                </div>
                <div className="w-10 h-10 rounded-xl bg-obsidian-800 border border-obsidian-700 flex items-center justify-center text-muted-400">
                  <Zap className="w-5 h-5" />
                </div>
              </div>

              <div className="mt-6 mb-8">
                <div className="flex items-baseline">
                  <span className="text-4xl font-extrabold text-ivory-100">$0</span>
                  <span className="text-muted-400 text-sm ml-2">/ forever</span>
                </div>
                <p className="text-xs text-muted-500 mt-1">No credit card required</p>
              </div>

              <div className="space-y-4 text-sm text-ivory-300">
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-gold-500/10 text-gold-400 flex items-center justify-center mt-0.5 flex-shrink-0">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span>Max file size: <strong>50 MB</strong> per file</span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-gold-500/10 text-gold-400 flex items-center justify-center mt-0.5 flex-shrink-0">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span><strong>10 conversions</strong> per day</span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-gold-500/10 text-gold-400 flex items-center justify-center mt-0.5 flex-shrink-0">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span>Standard conversion engine speed</span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-gold-500/10 text-gold-400 flex items-center justify-center mt-0.5 flex-shrink-0">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span>All core document & image formats</span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-gold-500/10 text-gold-400 flex items-center justify-center mt-0.5 flex-shrink-0">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span>Single file upload at a time</span>
                </div>
              </div>
            </div>

            <div className="mt-8">
              <Link to="/register">
                <Button variant="secondary" fullWidth className="py-3">
                  Get Started Free
                </Button>
              </Link>
            </div>
          </motion.div>

          {/* Pro Plan */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="relative rounded-2xl bg-gradient-to-b from-obsidian-800 to-obsidian-900 border-2 border-gold-500/50 p-8 flex flex-col justify-between shadow-2xl shadow-gold-500/5"
          >
            {/* Popular Badge */}
            <div className="absolute -top-4 right-8 bg-gradient-to-r from-gold-500 to-amber-500 text-obsidian-950 px-4 py-1 rounded-full text-xs font-extrabold uppercase tracking-wider shadow-md flex items-center gap-1.5">
              <Crown className="w-3.5 h-3.5" />
              Most Popular
            </div>

            <div>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-bold text-ivory-100 flex items-center gap-2">
                    Pro Plan
                    <Sparkles className="w-4 h-4 text-gold-400" />
                  </h3>
                  <p className="text-sm text-muted-400 mt-1">For professionals & heavy document power users</p>
                </div>
                <div className="w-10 h-10 rounded-xl bg-gold-500/10 border border-gold-500/30 flex items-center justify-center text-gold-400">
                  <Crown className="w-5 h-5" />
                </div>
              </div>

              <div className="mt-6 mb-8">
                <div className="flex items-baseline">
                  <span className="text-4xl font-extrabold text-gold-400">
                    ${isAnnual ? '10' : '12'}
                  </span>
                  <span className="text-muted-400 text-sm ml-2">/ month</span>
                </div>
                <p className="text-xs text-gold-400/80 mt-1">
                  {isAnnual ? 'Billed annually ($120/year)' : 'Billed monthly'}
                </p>
              </div>

              <div className="space-y-4 text-sm text-ivory-200">
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-gold-500 text-obsidian-950 flex items-center justify-center mt-0.5 flex-shrink-0 font-bold">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span>Max file size: <strong>2 GB</strong> per file</span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-gold-500 text-obsidian-950 flex items-center justify-center mt-0.5 flex-shrink-0 font-bold">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span><strong>Unlimited</strong> conversions & exports</span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-gold-500 text-obsidian-950 flex items-center justify-center mt-0.5 flex-shrink-0 font-bold">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span><strong>Priority high-speed server queue</strong></span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-gold-500 text-obsidian-950 flex items-center justify-center mt-0.5 flex-shrink-0 font-bold">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span>Batch conversion (up to <strong>50 files</strong> at once)</span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-gold-500 text-obsidian-950 flex items-center justify-center mt-0.5 flex-shrink-0 font-bold">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span>Advanced OCR Text Extraction & PDF Utilities</span>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-gold-500 text-obsidian-950 flex items-center justify-center mt-0.5 flex-shrink-0 font-bold">
                    <Check className="w-3.5 h-3.5" />
                  </div>
                  <span>30-day cloud vault storage & 24/7 priority support</span>
                </div>
              </div>
            </div>

            <div className="mt-8">
              <Link to="/register">
                <Button variant="primary" fullWidth className="py-3 shadow-lg shadow-gold-500/20">
                  Upgrade to Pro <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>

        {/* Security Assurance Banner */}
        <div className="mt-16 rounded-2xl bg-obsidian-900 border border-obsidian-800 p-8 text-center max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-4 text-left">
            <div className="w-12 h-12 rounded-xl bg-gold-500/10 border border-gold-500/20 flex items-center justify-center text-gold-400 flex-shrink-0">
              <Shield className="w-6 h-6" />
            </div>
            <div>
              <h4 className="text-base font-bold text-ivory-100">Enterprise-Grade Security Included</h4>
              <p className="text-sm text-muted-400">All data is end-to-end encrypted with automatic server purging.</p>
            </div>
          </div>
          <Link to="/register">
            <Button variant="secondary" className="whitespace-nowrap">
              Try Pro Free for 14 Days
            </Button>
          </Link>
        </div>

        {/* FAQs */}
        <div className="mt-20 max-w-3xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-ivory-100 flex items-center justify-center gap-2">
              <HelpCircle className="w-6 h-6 text-gold-400" />
              Frequently Asked Questions
            </h2>
            <p className="text-sm text-muted-400 mt-1">Got questions? We've got answers.</p>
          </div>

          <div className="space-y-4">
            {faqs.map((faq, idx) => (
              <div
                key={idx}
                className="rounded-xl bg-obsidian-900 border border-obsidian-800 overflow-hidden"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                  className="w-full text-left p-5 flex items-center justify-between text-ivory-200 font-medium hover:text-gold-400 transition-colors"
                >
                  <span>{faq.q}</span>
                  <span className="text-gold-400 font-bold ml-4 text-lg">
                    {openFaq === idx ? '−' : '+'}
                  </span>
                </button>
                {openFaq === idx && (
                  <div className="px-5 pb-5 text-sm text-muted-300 leading-relaxed border-t border-obsidian-800/50 pt-3">
                    {faq.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </PublicLayout>
  );
}
