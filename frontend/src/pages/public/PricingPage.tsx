/**
 * VELTO — Pricing Page
 * Premium black + gold pricing plans with monthly/annual billing toggle, plan breakdown & FAQs.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Check, Zap, Crown, Shield, HelpCircle, ArrowRight, Sparkles } from 'lucide-react';
import PublicLayout from '../../components/layout/PublicLayout';
import SeoHead from '../../components/seo/SeoHead';
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
      a: "VELTO supports formats including PDF, Word (DOCX), Excel (XLSX), PowerPoint (PPTX), Images (PNG, JPG, WEBP, TIFF, BMP, GIF), Text, CSV, HTML, and Markdown."
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
      <SeoHead />
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

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {/* Free Tier */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="rounded-2xl bg-obsidian-900 border border-obsidian-800 p-8 flex flex-col justify-between hover:border-obsidian-700 transition-all shadow-xl"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-muted-400 uppercase tracking-wider">Guest & Free</span>
                <span className="p-2 rounded-lg bg-obsidian-800 text-muted-300">
                  <Zap className="w-5 h-5" />
                </span>
              </div>
              <h2 className="text-2xl font-bold text-ivory-100 mt-3">Free Tier</h2>
              <p className="text-xs text-muted-400 mt-1">Essential file conversion for quick everyday tasks.</p>
              
              <div className="mt-6 flex items-baseline">
                <span className="text-4xl font-extrabold text-ivory-100">$0</span>
                <span className="text-muted-400 text-sm ml-2">/ forever</span>
              </div>

              <ul className="mt-8 space-y-3 text-sm text-muted-300 border-t border-obsidian-800 pt-6">
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>Up to 5 conversions per day</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>Max file size: 25 MB</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>Standard engine processing speed</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>SSL encrypted file transfer</span>
                </li>
              </ul>
            </div>

            <div className="mt-8">
              <Link to="/register">
                <Button variant="secondary" fullWidth>Get Started Free</Button>
              </Link>
            </div>
          </motion.div>

          {/* Pro Tier (Featured) */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2 }}
            className="relative rounded-2xl bg-gradient-to-b from-obsidian-850 to-obsidian-900 border-2 border-gold-500/60 p-8 flex flex-col justify-between shadow-2xl shadow-gold-500/10 transform md:-translate-y-2"
          >
            <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gold-500 text-obsidian-950 font-extrabold text-[11px] uppercase tracking-wider shadow-md">
              Most Popular
            </div>

            <div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gold-400 uppercase tracking-wider">Pro Individual</span>
                <span className="p-2 rounded-lg bg-gold-500/10 text-gold-400 border border-gold-500/30">
                  <Crown className="w-5 h-5" />
                </span>
              </div>
              <h2 className="text-2xl font-bold text-ivory-100 mt-3">Pro Plan</h2>
              <p className="text-xs text-muted-400 mt-1">For power users and professionals needing speed & scale.</p>
              
              <div className="mt-6 flex items-baseline">
                <span className="text-4xl font-extrabold text-ivory-100">{isAnnual ? '$9' : '$12'}</span>
                <span className="text-muted-400 text-sm ml-2">/ month</span>
              </div>

              <ul className="mt-8 space-y-3 text-sm text-ivory-200 border-t border-obsidian-800/80 pt-6">
                <li className="flex items-center gap-3 font-medium">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>Unlimited daily conversions</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>Max file size: 500 MB</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>High-speed priority processing queue</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>Batch conversion (up to 50 files)</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>OCR scanner text extraction</span>
                </li>
              </ul>
            </div>

            <div className="mt-8">
              <Link to="/register">
                <Button variant="primary" fullWidth iconRight={<ArrowRight className="w-4 h-4" />}>
                  Start Pro Trial
                </Button>
              </Link>
            </div>
          </motion.div>

          {/* Business Tier */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.3 }}
            className="rounded-2xl bg-obsidian-900 border border-obsidian-800 p-8 flex flex-col justify-between hover:border-obsidian-700 transition-all shadow-xl"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-muted-400 uppercase tracking-wider">Teams & Enterprise</span>
                <span className="p-2 rounded-lg bg-obsidian-800 text-muted-300">
                  <Shield className="w-5 h-5" />
                </span>
              </div>
              <h2 className="text-2xl font-bold text-ivory-100 mt-3">Business</h2>
              <p className="text-xs text-muted-400 mt-1">Dedicated enterprise infrastructure with API access.</p>
              
              <div className="mt-6 flex items-baseline">
                <span className="text-4xl font-extrabold text-ivory-100">{isAnnual ? '$29' : '$35'}</span>
                <span className="text-muted-400 text-sm ml-2">/ month</span>
              </div>

              <ul className="mt-8 space-y-3 text-sm text-muted-300 border-t border-obsidian-800 pt-6">
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>Everything in Pro Plan</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>Max file size: 2 GB</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>REST API access & Webhooks</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-gold-400 flex-shrink-0" />
                  <span>Dedicated cloud processing nodes</span>
                </li>
              </ul>
            </div>

            <div className="mt-8">
              <Link to="/register">
                <Button variant="secondary" fullWidth>Contact Enterprise</Button>
              </Link>
            </div>
          </motion.div>
        </div>

        {/* FAQs */}
        <div className="mt-24 max-w-4xl mx-auto border-t border-obsidian-800/80 pt-16">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-ivory-100 flex items-center justify-center gap-2">
              <HelpCircle className="w-6 h-6 text-gold-400" />
              Frequently Asked Questions
            </h2>
            <p className="text-sm text-muted-400 mt-2">Have questions? We have answers.</p>
          </div>

          <div className="space-y-4">
            {faqs.map((faq, idx) => (
              <div
                key={idx}
                className="rounded-xl bg-obsidian-900 border border-obsidian-800 overflow-hidden"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                  className="w-full px-6 py-4 text-left text-sm sm:text-base font-bold text-ivory-100 flex items-center justify-between focus:outline-none"
                >
                  <span>{faq.q}</span>
                  <span className="text-gold-400 text-lg ml-4">{openFaq === idx ? '−' : '+'}</span>
                </button>
                {openFaq === idx && (
                  <div className="px-6 pb-5 pt-1 text-sm text-muted-400 leading-relaxed border-t border-obsidian-800/50">
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
