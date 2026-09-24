/**
 * VELTO — Tools Discovery Page
 * Categorized grid of document, image, PDF, and OCR tools with filter & search.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FileText,
  Image as ImageIcon,
  FileSpreadsheet,
  Layers,
  Split,
  Minimize2,
  RotateCw,
  Lock,
  Unlock,
  Eye,
  ScanLine,
  Search,
  Sparkles,
  ArrowRight,
  Zap,
} from 'lucide-react';
import AppShell from '../../components/layout/AppShell';

interface ToolItem {
  id: string;
  name: string;
  description: string;
  category: 'pdf' | 'document' | 'image' | 'ocr';
  icon: any;
  popular?: boolean;
  proOnly?: boolean;
  fromFormat?: string;
  toFormat?: string;
}

const TOOLS: ToolItem[] = [
  // PDF Tools
  {
    id: 'pdf-to-word',
    name: 'PDF to Word',
    description: 'Convert PDF files to editable DOCX documents with preserved layout.',
    category: 'pdf',
    icon: FileText,
    popular: true,
    fromFormat: 'pdf',
    toFormat: 'docx',
  },
  {
    id: 'word-to-pdf',
    name: 'Word to PDF',
    description: 'Convert DOCX files to professional standard PDF format instantly.',
    category: 'pdf',
    icon: FileText,
    popular: true,
    fromFormat: 'docx',
    toFormat: 'pdf',
  },
  {
    id: 'pdf-to-excel',
    name: 'PDF to Excel',
    description: 'Extract tables and spreadsheet data from PDF files into XLSX.',
    category: 'pdf',
    icon: FileSpreadsheet,
    fromFormat: 'pdf',
    toFormat: 'xlsx',
  },
  {
    id: 'pdf-merge',
    name: 'Merge PDF',
    description: 'Combine multiple PDF documents into a single organized file.',
    category: 'pdf',
    icon: Layers,
    popular: true,
  },
  {
    id: 'pdf-split',
    name: 'Split PDF',
    description: 'Separate single PDF into individual pages or page ranges.',
    category: 'pdf',
    icon: Split,
  },
  {
    id: 'pdf-compress',
    name: 'Compress PDF',
    description: 'Reduce PDF file size while maintaining optimum visual quality.',
    category: 'pdf',
    icon: Minimize2,
    popular: true,
  },
  {
    id: 'pdf-rotate',
    name: 'Rotate PDF',
    description: 'Rotate PDF pages clockwise or counter-clockwise.',
    category: 'pdf',
    icon: RotateCw,
  },
  {
    id: 'pdf-protect',
    name: 'Protect PDF',
    description: 'Encrypt your PDF with password security & custom permissions.',
    category: 'pdf',
    icon: Lock,
    proOnly: true,
  },
  {
    id: 'pdf-unlock',
    name: 'Unlock PDF',
    description: 'Remove password protection and restrictions from PDF files.',
    category: 'pdf',
    icon: Unlock,
    proOnly: true,
  },

  // Image Tools
  {
    id: 'jpg-to-png',
    name: 'JPG to PNG',
    description: 'Convert JPG images to PNG with transparency support.',
    category: 'image',
    icon: ImageIcon,
    popular: true,
    fromFormat: 'jpg',
    toFormat: 'png',
  },
  {
    id: 'png-to-jpg',
    name: 'PNG to JPG',
    description: 'Convert PNG images to compressed high quality JPG files.',
    category: 'image',
    icon: ImageIcon,
    fromFormat: 'png',
    toFormat: 'jpg',
  },
  {
    id: 'webp-to-jpg',
    name: 'WEBP to JPG',
    description: 'Convert modern WEBP web images into standard JPG files.',
    category: 'image',
    icon: ImageIcon,
    fromFormat: 'webp',
    toFormat: 'jpg',
  },
  {
    id: 'image-compress',
    name: 'Compress Image',
    description: 'Optimize image dimensions and quality for faster web loading.',
    category: 'image',
    icon: Minimize2,
  },

  // OCR Tools
  {
    id: 'ocr-pdf',
    name: 'OCR PDF Scanner',
    description: 'Extract text from scanned PDF documents into searchable text/Word.',
    category: 'ocr',
    icon: ScanLine,
    popular: true,
    proOnly: true,
  },
  {
    id: 'ocr-image',
    name: 'Image Text Extractor',
    description: 'Extract typed or handwritten text from photos and screenshots.',
    category: 'ocr',
    icon: Eye,
    proOnly: true,
  },
];

export default function ToolsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<'all' | 'pdf' | 'document' | 'image' | 'ocr'>('all');

  const filteredTools = TOOLS.filter((tool) => {
    const matchesCategory = activeCategory === 'all' || tool.category === activeCategory;
    const matchesSearch =
      tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <AppShell>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gold-500/10 border border-gold-500/20 text-gold-400 text-xs font-semibold uppercase tracking-wider mb-2">
              <Sparkles className="w-3.5 h-3.5" />
              VELTO Suite
            </div>
            <h1 className="text-3xl font-extrabold text-ivory-100 tracking-tight">
              File Conversion & PDF Tools
            </h1>
            <p className="text-muted-400 text-sm mt-1">
              Select a tool to convert, edit, compress, or extract text from your files.
            </p>
          </div>

          {/* Search Box */}
          <div className="relative w-full md:w-72">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-500" />
            <input
              type="text"
              placeholder="Search tools..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-obsidian-900 border border-obsidian-700 rounded-xl pl-10 pr-4 py-2 text-sm text-ivory-100 placeholder-muted-500 focus:outline-none focus:border-gold-500 transition-colors"
            />
          </div>
        </div>

        {/* Category Filters */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-obsidian-800 scrollbar-none">
          {[
            { id: 'all', label: 'All Tools' },
            { id: 'pdf', label: 'PDF Utilities' },
            { id: 'image', label: 'Image Tools' },
            { id: 'ocr', label: 'OCR & Text' },
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id as any)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
                activeCategory === cat.id
                  ? 'bg-gold-500 text-obsidian-950 shadow-md font-semibold'
                  : 'bg-obsidian-900 text-muted-400 border border-obsidian-800 hover:text-ivory-100 hover:border-obsidian-700'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Tools Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTools.map((tool, idx) => {
            const Icon = tool.icon;
            return (
              <motion.div
                key={tool.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: idx * 0.04 }}
              >
                <Link
                  to={tool.fromFormat && tool.toFormat ? `/convert?from=${tool.fromFormat}&to=${tool.toFormat}` : `/tools/${tool.id}`}
                  className="group relative rounded-2xl bg-obsidian-900 border border-obsidian-800 p-6 flex flex-col justify-between hover:border-gold-500/50 hover:bg-obsidian-850 transition-all shadow-lg hover:shadow-gold-500/5 block h-full"
                >
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-12 h-12 rounded-xl bg-obsidian-800 border border-obsidian-700 group-hover:border-gold-500/40 group-hover:bg-gold-500/10 flex items-center justify-center text-gold-400 transition-colors">
                        <Icon className="w-6 h-6" />
                      </div>

                      <div className="flex items-center gap-1.5">
                        {tool.popular && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-gold-500/10 border border-gold-500/30 text-gold-400 uppercase tracking-wider">
                            Popular
                          </span>
                        )}
                        {tool.proOnly && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 border border-amber-500/30 text-amber-400 uppercase tracking-wider flex items-center gap-1">
                            <Zap className="w-2.5 h-2.5" /> Pro
                          </span>
                        )}
                      </div>
                    </div>

                    <h3 className="text-lg font-bold text-ivory-100 group-hover:text-gold-400 transition-colors flex items-center gap-2">
                      {tool.name}
                    </h3>
                    <p className="text-sm text-muted-400 mt-2 leading-relaxed">
                      {tool.description}
                    </p>
                  </div>

                  <div className="mt-6 pt-4 border-t border-obsidian-800/60 flex items-center justify-between text-xs text-gold-400 font-semibold group-hover:translate-x-1 transition-transform">
                    <span>Use tool</span>
                    <ArrowRight className="w-4 h-4" />
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>

        {filteredTools.length === 0 && (
          <div className="text-center py-16 bg-obsidian-900 rounded-2xl border border-obsidian-800">
            <Search className="w-10 h-10 text-muted-500 mx-auto mb-3" />
            <h3 className="text-base font-bold text-ivory-200">No tools found</h3>
            <p className="text-xs text-muted-500 mt-1">Try searching for another keyword or clear filter.</p>
          </div>
        )}
      </div>
    </AppShell>
  );
}
