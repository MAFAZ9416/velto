/**
 * VELTO Conversion — Tool SEO Registry
 * Single source of truth for supported conversion landing pages, keyword mappings,
 * FAQs, how-it-works steps, and structured data generation.
 *
 * ONLY contains conversion pairs supported by VELTO engines.
 */

import { SITE_CONFIG } from './site';

export interface ToolFaq {
  question: string;
  answer: string;
}

export interface ToolSeoConfig {
  slug: string;
  sourceFormat: string;
  targetFormat: string;
  sourceLabel: string;
  targetLabel: string;
  category: 'pdf' | 'document' | 'spreadsheet' | 'presentation' | 'image' | 'archive';
  name: string;
  h1: string;
  title: string;
  description: string;
  keywords: string[];
  intro: string;
  features: string[];
  steps: string[];
  faqs: ToolFaq[];
  relatedSlugs: string[];
}

export const SUPPORTED_TOOLS: Record<string, ToolSeoConfig> = {
  // ── PDF CONVERTERS ──────────────────────────────────────────────────────────
  'pdf-to-word': {
    slug: 'pdf-to-word',
    sourceFormat: 'pdf',
    targetFormat: 'docx',
    sourceLabel: 'PDF',
    targetLabel: 'Word (DOCX)',
    category: 'pdf',
    name: 'PDF to Word Converter',
    h1: 'PDF to Word Converter',
    title: 'PDF to Word Converter – Convert PDF to Word Online | VELTO',
    description:
      'Convert PDF files to editable Word (DOCX) documents online with VELTO Conversion. Fast, layout-preserving, and secure PDF to Word converter.',
    keywords: [
      'PDF to Word',
      'PDF to Word converter',
      'PDF to DOCX',
      'PDF to DOCX converter',
      'convert PDF to Word',
      'convert PDF to DOCX',
      'PDF to Word online',
      'free PDF to Word converter',
      'free PDF to DOCX converter',
      'online PDF to Word converter',
      'online PDF to DOCX converter',
      'VELTO PDF converter',
    ],
    intro:
      'Transform your static PDF documents into fully editable Microsoft Word (DOCX) files effortlessly. VELTO preserves your formatting, tables, headings, and image layouts.',
    features: [
      'Accurate layout preservation for text, tables, and images',
      'Fast online cloud conversion without software installation',
      'Encrypted SSL upload with automatic file cleanup after processing',
      'Supports standard PDF versions and scanned document structures',
    ],
    steps: [
      'Upload your PDF file using the dropzone or click to select.',
      'Click the convert button to start processing your document.',
      'Download your formatted Microsoft Word (.docx) document instantly.',
    ],
    faqs: [
      {
        question: 'What is a PDF to Word converter?',
        answer:
          'A PDF to Word converter takes portable document format (PDF) files and converts their contents into editable Microsoft Word (.docx) documents, allowing you to edit text, tables, and images.',
      },
      {
        question: 'How do I convert a PDF to Word online?',
        answer:
          'Simply drag and drop your PDF file into VELTO, verify the format, click convert, and download your converted Word file in seconds.',
      },
      {
        question: 'Will VELTO preserve my PDF document formatting?',
        answer:
          'Yes, VELTO uses advanced layout structure reconstruction to preserve paragraphs, table borders, fonts, and inline images.',
      },
      {
        question: 'Are my uploaded files safe and private?',
        answer:
          'Absolutely. All transfers are encrypted via TLS 1.3, and uploaded files are automatically deleted after processing.',
      },
    ],
    relatedSlugs: ['word-to-pdf', 'pdf-to-excel', 'pdf-to-jpg', 'pdf-to-png', 'pdf-to-pptx'],
  },

  'pdf-to-docx': {
    slug: 'pdf-to-docx',
    sourceFormat: 'pdf',
    targetFormat: 'docx',
    sourceLabel: 'PDF',
    targetLabel: 'DOCX',
    category: 'pdf',
    name: 'PDF to DOCX Converter',
    h1: 'PDF to DOCX Converter',
    title: 'PDF to DOCX Converter – Convert PDF to DOCX Online | VELTO',
    description:
      'Convert PDF files to Microsoft Word DOCX format quickly and securely online with VELTO Conversion.',
    keywords: [
      'PDF to DOCX',
      'PDF to DOCX converter',
      'convert PDF to DOCX',
      'PDF to DOCX online',
      'free PDF to DOCX converter',
      'online PDF to DOCX converter',
      'VELTO conversion',
    ],
    intro:
      'Convert your PDF files into Microsoft Word DOCX format in seconds. Maintain clear typography, headers, and document formatting with VELTO.',
    features: [
      'Direct conversion from PDF to native Word DOCX format',
      'Preserves multi-column text and tables',
      'No registration required for quick conversions',
      'Protected by 256-bit encryption',
    ],
    steps: [
      'Select or drop your PDF document.',
      'Initiate the conversion to DOCX.',
      'Save your editable DOCX document to your device.',
    ],
    faqs: [
      {
        question: 'What is the difference between DOC and DOCX?',
        answer:
          'DOCX is the modern OpenXML format used by Microsoft Word 2007 and newer. It offers better layout stability, smaller file sizes, and universal compatibility.',
      },
      {
        question: 'Can I convert scanned PDFs to DOCX?',
        answer:
          'Yes, VELTO extracts structural elements and text content so you can edit the document in Microsoft Word.',
      },
    ],
    relatedSlugs: ['pdf-to-word', 'docx-to-pdf', 'pdf-to-xlsx'],
  },

  'word-to-pdf': {
    slug: 'word-to-pdf',
    sourceFormat: 'docx',
    targetFormat: 'pdf',
    sourceLabel: 'Word (DOCX)',
    targetLabel: 'PDF',
    category: 'document',
    name: 'Word to PDF Converter',
    h1: 'Word to PDF Converter',
    title: 'Word to PDF Converter – Convert Word to PDF Online | VELTO',
    description:
      'Convert Word documents (DOCX) to professional PDF files online with VELTO Conversion. Simple, instant, and high-fidelity Word to PDF tool.',
    keywords: [
      'Word to PDF',
      'Word to PDF converter',
      'DOCX to PDF',
      'DOCX to PDF converter',
      'convert Word to PDF',
      'convert DOCX to PDF',
      'Word to PDF online',
      'free Word to PDF converter',
      'free DOCX to PDF converter',
      'online Word to PDF converter',
      'VELTO document converter',
    ],
    intro:
      'Convert Word documents into fixed-layout, publication-ready PDF files. Perfect for sharing resumes, contracts, business reports, and legal forms.',
    features: [
      'Creates high-resolution, vector-accurate PDF files from Word',
      'Preserves exact fonts, margins, tables, and page pagination',
      'Universal compatibility across mobile, desktop, and e-readers',
      'Zero installation needed — converts right in your browser',
    ],
    steps: [
      'Choose your Word (.docx) file from your computer or phone.',
      'Click convert to transform your document into PDF.',
      'Download your read-only, professional PDF file.',
    ],
    faqs: [
      {
        question: 'Why convert Word documents to PDF?',
        answer:
          'PDF format ensures your document looks identical on every device, operating system, and printer without unintended font changes or line shifts.',
      },
      {
        question: 'Is Word to PDF conversion free on VELTO?',
        answer:
          'Yes, VELTO provides free online conversions for standard files without requiring any software downloads.',
      },
    ],
    relatedSlugs: ['pdf-to-word', 'docx-to-pdf', 'docx-to-jpg', 'docx-to-png'],
  },

  'docx-to-pdf': {
    slug: 'docx-to-pdf',
    sourceFormat: 'docx',
    targetFormat: 'pdf',
    sourceLabel: 'DOCX',
    targetLabel: 'PDF',
    category: 'document',
    name: 'DOCX to PDF Converter',
    h1: 'DOCX to PDF Converter',
    title: 'DOCX to PDF Converter – Convert DOCX to PDF Online | VELTO',
    description:
      'Convert DOCX files to PDF online with VELTO Conversion. Clean formatting, instant conversion, and secure handling.',
    keywords: [
      'DOCX to PDF',
      'DOCX to PDF converter',
      'convert DOCX to PDF',
      'DOCX to PDF online',
      'free DOCX to PDF converter',
      'online DOCX to PDF converter',
    ],
    intro:
      'Turn Microsoft Word DOCX files into standardized PDF documents with high fidelity and quick cloud processing.',
    features: [
      'High-speed document conversion pipeline',
      'Retains embedded pictures, formatting, and layout structure',
      '100% web-based without plugin requirements',
    ],
    steps: [
      'Select your .docx document file.',
      'Click start conversion.',
      'Download your ready-to-view PDF.',
    ],
    faqs: [
      {
        question: 'Does converting DOCX to PDF lock the text?',
        answer:
          'Converting to PDF creates a viewable document representation while keeping text selectable and searchable.',
      },
    ],
    relatedSlugs: ['word-to-pdf', 'pdf-to-word', 'docx-to-png'],
  },

  'pdf-to-excel': {
    slug: 'pdf-to-excel',
    sourceFormat: 'pdf',
    targetFormat: 'xlsx',
    sourceLabel: 'PDF',
    targetLabel: 'Excel (XLSX)',
    category: 'pdf',
    name: 'PDF to Excel Converter',
    h1: 'PDF to Excel Converter',
    title: 'PDF to Excel Converter – Convert PDF to Excel Online | VELTO',
    description:
      'Extract tables and financial data from PDF to editable Excel (XLSX) spreadsheets online with VELTO Conversion.',
    keywords: [
      'PDF to Excel',
      'PDF to Excel converter',
      'PDF to XLSX',
      'PDF to XLSX converter',
      'convert PDF to Excel',
      'convert PDF to XLSX',
      'PDF to Excel online',
      'free PDF to Excel converter',
      'online PDF to Excel converter',
      'VELTO file converter',
    ],
    intro:
      'Extract spreadsheet tables, financial data, and structured metrics from PDF files directly into Microsoft Excel (.xlsx) format.',
    features: [
      'Extracts structured data into separate cells and columns',
      'Eliminates manual data entry and copying',
      'Fast processing engine built for business reports and invoices',
    ],
    steps: [
      'Upload the PDF containing tables or rows of data.',
      'Click convert to extract structured data into Excel.',
      'Download your editable Microsoft Excel spreadsheet.',
    ],
    faqs: [
      {
        question: 'How does PDF to Excel conversion work?',
        answer:
          'VELTO analyzes table borders, column spacing, and text cells in the PDF to build matching rows and columns in an XLSX file.',
      },
    ],
    relatedSlugs: ['excel-to-pdf', 'pdf-to-word', 'csv-to-xlsx'],
  },

  'excel-to-pdf': {
    slug: 'excel-to-pdf',
    sourceFormat: 'xlsx',
    targetFormat: 'pdf',
    sourceLabel: 'Excel (XLSX)',
    targetLabel: 'PDF',
    category: 'spreadsheet',
    name: 'Excel to PDF Converter',
    h1: 'Excel to PDF Converter',
    title: 'Excel to PDF Converter – Convert Excel to PDF Online | VELTO',
    description:
      'Convert Excel sheets (XLSX) to clean, printable PDF documents online with VELTO Conversion.',
    keywords: [
      'Excel to PDF',
      'Excel to PDF converter',
      'XLSX to PDF',
      'XLSX to PDF converter',
      'convert Excel to PDF',
      'convert XLSX to PDF',
      'Excel to PDF online',
      'free Excel to PDF converter',
      'online Excel to PDF converter',
    ],
    intro:
      'Turn complex Microsoft Excel spreadsheets into clean, print-friendly PDF reports suitable for distribution and archiving.',
    features: [
      'Preserves spreadsheet formatting and grid structure',
      'Fit columns neatly onto PDF pages',
      'Ensures numeric formats and formulas render accurately',
    ],
    steps: [
      'Upload your Excel (.xlsx) spreadsheet.',
      'Click convert to generate your PDF document.',
      'Download your crisp, formatted PDF file.',
    ],
    faqs: [
      {
        question: 'Will formulas be hidden in the PDF?',
        answer:
          'Yes, the generated PDF shows calculated values and visually formatted cells without exposing underlying sheet formulas.',
      },
    ],
    relatedSlugs: ['pdf-to-excel', 'xlsx-to-pdf', 'xlsx-to-png'],
  },

  'xlsx-to-pdf': {
    slug: 'xlsx-to-pdf',
    sourceFormat: 'xlsx',
    targetFormat: 'pdf',
    sourceLabel: 'XLSX',
    targetLabel: 'PDF',
    category: 'spreadsheet',
    name: 'XLSX to PDF Converter',
    h1: 'XLSX to PDF Converter',
    title: 'XLSX to PDF Converter – Convert XLSX to PDF Online | VELTO',
    description:
      'Convert XLSX spreadsheet files to PDF online with VELTO Conversion. Quick, secure, and accurate layout rendering.',
    keywords: [
      'XLSX to PDF',
      'XLSX to PDF converter',
      'convert XLSX to PDF',
      'XLSX to PDF online',
      'free XLSX to PDF converter',
    ],
    intro:
      'Convert Microsoft Excel XLSX workbooks into portable PDF documents for easy sharing across platforms.',
    features: [
      'Universal device compatibility',
      'Retains numbers, dates, and header styling',
      'Instant cloud processing',
    ],
    steps: [
      'Select your XLSX workbook.',
      'Run the PDF conversion.',
      'Download your PDF output.',
    ],
    faqs: [
      {
        question: 'Can I view the output PDF on mobile phones?',
        answer:
          'Yes, PDFs generated by VELTO are optimized for viewing on iOS, Android, and desktop devices.',
      },
    ],
    relatedSlugs: ['excel-to-pdf', 'pdf-to-excel', 'xlsx-to-jpg'],
  },

  'pdf-to-powerpoint': {
    slug: 'pdf-to-powerpoint',
    sourceFormat: 'pdf',
    targetFormat: 'pptx',
    sourceLabel: 'PDF',
    targetLabel: 'PowerPoint (PPTX)',
    category: 'pdf',
    name: 'PDF to PowerPoint Converter',
    h1: 'PDF to PowerPoint Converter',
    title: 'PDF to PowerPoint Converter – Convert PDF to PPTX Online | VELTO',
    description:
      'Convert PDF slides to editable Microsoft PowerPoint (PPTX) presentations online with VELTO Conversion.',
    keywords: [
      'PDF to PowerPoint',
      'PDF to PPTX',
      'PDF to PowerPoint converter',
      'PDF to PPTX converter',
      'convert PDF to PowerPoint',
      'convert PDF to PPTX',
      'online PDF to PPTX converter',
    ],
    intro:
      'Reclaim your slide decks. Convert PDF presentation files into editable Microsoft PowerPoint (.pptx) slides.',
    features: [
      'Converts PDF pages into individual editable slides',
      'Preserves vector graphics, diagrams, and text blocks',
      'Ideal for reusing existing presentation decks',
    ],
    steps: [
      'Upload your PDF presentation deck.',
      'Convert PDF pages into PowerPoint slides.',
      'Download your editable PPTX file.',
    ],
    faqs: [
      {
        question: 'Will each PDF page become a slide?',
        answer:
          'Yes, each page in your input PDF is converted into a distinct slide in the target PowerPoint presentation.',
      },
    ],
    relatedSlugs: ['powerpoint-to-pdf', 'pptx-to-pdf', 'pdf-to-word'],
  },

  'powerpoint-to-pdf': {
    slug: 'powerpoint-to-pdf',
    sourceFormat: 'pptx',
    targetFormat: 'pdf',
    sourceLabel: 'PowerPoint (PPTX)',
    targetLabel: 'PDF',
    category: 'presentation',
    name: 'PowerPoint to PDF Converter',
    h1: 'PowerPoint to PDF Converter',
    title: 'PowerPoint to PDF Converter – Convert PPTX to PDF Online | VELTO',
    description:
      'Convert PowerPoint presentations (PPTX) to clean PDF documents online with VELTO Conversion.',
    keywords: [
      'PowerPoint to PDF',
      'PPTX to PDF',
      'PowerPoint to PDF converter',
      'PPTX to PDF converter',
      'convert PowerPoint to PDF',
      'convert PPTX to PDF',
      'free PowerPoint to PDF converter',
    ],
    intro:
      'Export Microsoft PowerPoint presentations into compact PDF files for handouts, lectures, and email attachments.',
    features: [
      'Retains slide aspect ratios and high-definition imagery',
      'Locks layouts so fonts and themes remain intact',
      'Fast, reliable cloud conversion engine',
    ],
    steps: [
      'Upload your .pptx presentation file.',
      'Click convert to produce the PDF file.',
      'Download your shareable presentation PDF.',
    ],
    faqs: [
      {
        question: 'Are embedded slide fonts preserved?',
        answer:
          'Yes, VELTO renders typography into fixed-layout PDF representations so font substitution does not distort slides.',
      },
    ],
    relatedSlugs: ['pdf-to-powerpoint', 'pptx-to-pdf', 'pptx-to-jpg'],
  },

  'pptx-to-pdf': {
    slug: 'pptx-to-pdf',
    sourceFormat: 'pptx',
    targetFormat: 'pdf',
    sourceLabel: 'PPTX',
    targetLabel: 'PDF',
    category: 'presentation',
    name: 'PPTX to PDF Converter',
    h1: 'PPTX to PDF Converter',
    title: 'PPTX to PDF Converter – Convert PPTX to PDF Online | VELTO',
    description:
      'Convert PPTX files to PDF documents online with VELTO Conversion. Quick, secure, and presentation-ready.',
    keywords: [
      'PPTX to PDF',
      'PPTX to PDF converter',
      'convert PPTX to PDF',
      'PPTX to PDF online',
      'free PPTX to PDF converter',
    ],
    intro:
      'Convert PPTX presentation files to standard PDF format instantly using VELTO cloud conversion.',
    features: [
      'High slide resolution',
      'Preserves vector graphics and background colors',
      'Works in all modern browsers',
    ],
    steps: [
      'Select your PPTX file.',
      'Start the conversion process.',
      'Download your output PDF file.',
    ],
    faqs: [
      {
        question: 'Can I view the output PDF on devices without PowerPoint?',
        answer:
          'Yes! PDF files can be opened natively on smartphones, tablets, and computers without Microsoft Office.',
      },
    ],
    relatedSlugs: ['powerpoint-to-pdf', 'pdf-to-powerpoint', 'pptx-to-png'],
  },

  'pdf-to-jpg': {
    slug: 'pdf-to-jpg',
    sourceFormat: 'pdf',
    targetFormat: 'jpg',
    sourceLabel: 'PDF',
    targetLabel: 'JPG Image',
    category: 'pdf',
    name: 'PDF to JPG Converter',
    h1: 'PDF to JPG Converter',
    title: 'PDF to JPG Converter – Convert PDF to JPG Online | VELTO',
    description:
      'Convert PDF document pages into high-resolution JPG images online with VELTO Conversion.',
    keywords: [
      'PDF to JPG',
      'PDF to JPG converter',
      'convert PDF to JPG',
      'PDF to image',
      'PDF to image converter',
      'PDF pages to JPG',
      'PDF to JPG online',
      'free PDF to JPG converter',
      'VELTO image converter',
    ],
    intro:
      'Extract PDF pages as individual high-quality JPG image files suitable for web publishing, sharing, or social media.',
    features: [
      'Converts each page of your PDF into an individual JPG image',
      'High DPI resolution rendering for crisp text and graphics',
      'Fast image extraction with cloud acceleration',
    ],
    steps: [
      'Upload your PDF document file.',
      'Click convert to extract pages as JPG images.',
      'Download your converted JPG image file.',
    ],
    faqs: [
      {
        question: 'Does PDF to JPG decrease text sharpness?',
        answer:
          'VELTO renders PDF pages at high pixel density so text remains sharp and legible in the output JPG image.',
      },
    ],
    relatedSlugs: ['pdf-to-png', 'jpg-to-pdf', 'pdf-to-word'],
  },

  'pdf-to-png': {
    slug: 'pdf-to-png',
    sourceFormat: 'pdf',
    targetFormat: 'png',
    sourceLabel: 'PDF',
    targetLabel: 'PNG Image',
    category: 'pdf',
    name: 'PDF to PNG Converter',
    h1: 'PDF to PNG Converter',
    title: 'PDF to PNG Converter – Convert PDF to PNG Online | VELTO',
    description:
      'Convert PDF pages to lossless PNG images online with VELTO Conversion. Perfect for diagrams, text, and graphics.',
    keywords: [
      'PDF to PNG',
      'PDF to PNG converter',
      'convert PDF to PNG',
      'PDF to PNG online',
      'free PDF to PNG converter',
      'online PDF to PNG converter',
    ],
    intro:
      'Convert PDF document pages into clear, lossless PNG images. Ideal for graphics, charts, screenshots, and line art.',
    features: [
      'Lossless PNG rasterization preserving fine graphic details',
      'Transparent background support where applicable',
      'Ideal for embedding PDF pages into presentations and websites',
    ],
    steps: [
      'Select your PDF file.',
      'Convert PDF pages into PNG image format.',
      'Download your high-grade PNG file.',
    ],
    faqs: [
      {
        question: 'Why choose PNG over JPG for PDF pages?',
        answer:
          'PNG uses lossless compression, making it better for diagrams, scanned text, and line art without compression artifacts.',
      },
    ],
    relatedSlugs: ['pdf-to-jpg', 'png-to-pdf', 'pdf-to-word'],
  },

  // ── IMAGE CONVERTERS ────────────────────────────────────────────────────────
  'jpg-to-png': {
    slug: 'jpg-to-png',
    sourceFormat: 'jpg',
    targetFormat: 'png',
    sourceLabel: 'JPG',
    targetLabel: 'PNG',
    category: 'image',
    name: 'JPG to PNG Converter',
    h1: 'JPG to PNG Converter',
    title: 'JPG to PNG Converter – Convert JPG to PNG Online | VELTO',
    description:
      'Convert JPG photos to PNG format online with VELTO Conversion. Preserve quality with lossless PNG output.',
    keywords: [
      'JPG to PNG',
      'JPG to PNG converter',
      'convert JPG to PNG',
      'JPG to PNG online',
      'free JPG to PNG converter',
      'online JPG to PNG converter',
      'JPG conversion',
    ],
    intro:
      'Convert JPEG images into PNG files online. PNG format supports lossless storage and high clarity.',
    features: [
      'Instant browser-based image conversion',
      'Preserves original color profile and dimensions',
      'Supports batch image formats',
    ],
    steps: [
      'Upload your JPG picture.',
      'Click convert to transform to PNG.',
      'Download your PNG image.',
    ],
    faqs: [
      {
        question: 'Why convert JPG to PNG?',
        answer:
          'PNG is a lossless format, preventing further quality degradation when editing or re-saving images multiple times.',
      },
    ],
    relatedSlugs: ['png-to-jpg', 'jpg-to-webp', 'jpg-to-pdf', 'jpg-to-zip'],
  },

  'png-to-jpg': {
    slug: 'png-to-jpg',
    sourceFormat: 'png',
    targetFormat: 'jpg',
    sourceLabel: 'PNG',
    targetLabel: 'JPG',
    category: 'image',
    name: 'PNG to JPG Converter',
    h1: 'PNG to JPG Converter',
    title: 'PNG to JPG Converter – Convert PNG to JPG Online | VELTO',
    description:
      'Convert PNG images to compact JPG format online with VELTO Conversion. Reduce file size for web and sharing.',
    keywords: [
      'PNG to JPG',
      'PNG to JPG converter',
      'convert PNG to JPG',
      'PNG to JPG online',
      'free PNG to JPG converter',
      'online PNG to JPG converter',
    ],
    intro:
      'Compress and convert heavy PNG files into lightweight JPG pictures optimized for web pages and messaging apps.',
    features: [
      'Significantly reduces image file size',
      'Optimized image compression ratios',
      'High compatibility across all platforms',
    ],
    steps: [
      'Select your PNG image.',
      'Convert image to JPG.',
      'Download your optimized JPG file.',
    ],
    faqs: [
      {
        question: 'What happens to transparency when converting PNG to JPG?',
        answer:
          'Since JPG does not support transparent layers, transparent areas are automatically filled with a clean white background.',
      },
    ],
    relatedSlugs: ['jpg-to-png', 'png-to-webp', 'png-to-pdf', 'png-to-zip'],
  },

  'jpg-to-pdf': {
    slug: 'jpg-to-pdf',
    sourceFormat: 'jpg',
    targetFormat: 'pdf',
    sourceLabel: 'JPG Image',
    targetLabel: 'PDF',
    category: 'image',
    name: 'JPG to PDF Converter',
    h1: 'JPG to PDF Converter',
    title: 'JPG to PDF Converter – Convert JPG to PDF Online | VELTO',
    description:
      'Convert JPG images and photos into standard PDF documents online with VELTO Conversion.',
    keywords: [
      'JPG to PDF',
      'JPG to PDF converter',
      'convert JPG to PDF',
      'convert JPG online',
      'JPG to PDF online',
      'free JPG to PDF converter',
      'image to PDF',
    ],
    intro:
      'Combine or convert JPG photos into professional PDF documents. Perfect for submitting photo ID copies, forms, and photo reports.',
    features: [
      'Converts image formats directly into standard A4 PDF pages',
      'Preserves image crispness and color balance',
      '100% secure file handling',
    ],
    steps: [
      'Upload your JPG image file.',
      'Click convert to create your PDF document.',
      'Download your new PDF document.',
    ],
    faqs: [
      {
        question: 'Can I print the output PDF file?',
        answer:
          'Yes, the generated PDF file maintains accurate resolution for home and commercial printing.',
      },
    ],
    relatedSlugs: ['png-to-pdf', 'pdf-to-jpg', 'jpg-to-png'],
  },

  'png-to-pdf': {
    slug: 'png-to-pdf',
    sourceFormat: 'png',
    targetFormat: 'pdf',
    sourceLabel: 'PNG Image',
    targetLabel: 'PDF',
    category: 'image',
    name: 'PNG to PDF Converter',
    h1: 'PNG to PDF Converter',
    title: 'PNG to PDF Converter – Convert PNG to PDF Online | VELTO',
    description:
      'Convert PNG images to PDF documents online with VELTO Conversion. Clean, fast, and high quality.',
    keywords: [
      'PNG to PDF',
      'PNG to PDF converter',
      'convert PNG to PDF',
      'PNG to PDF online',
      'free PNG to PDF converter',
    ],
    intro:
      'Convert PNG files into portable PDF documents. Great for screenshots, designs, and digital artwork.',
    features: [
      'Clean PDF page generation from PNG images',
      'Maintains fine graphical details and clarity',
      'Browser-based conversion with instant download',
    ],
    steps: [
      'Choose your PNG picture file.',
      'Convert PNG to PDF format.',
      'Download your PDF document.',
    ],
    faqs: [
      {
        question: 'Is there a limit on image dimensions?',
        answer:
          'VELTO automatically scales large PNG images so they fit neatly onto standard PDF document pages.',
      },
    ],
    relatedSlugs: ['jpg-to-pdf', 'pdf-to-png', 'png-to-jpg'],
  },

  'jpg-to-webp': {
    slug: 'jpg-to-webp',
    sourceFormat: 'jpg',
    targetFormat: 'webp',
    sourceLabel: 'JPG',
    targetLabel: 'WebP',
    category: 'image',
    name: 'JPG to WebP Converter',
    h1: 'JPG to WebP Converter',
    title: 'JPG to WebP Converter – Convert JPG to WebP Online | VELTO',
    description:
      'Convert JPG images to modern WebP format online with VELTO Conversion. Speed up website loading times.',
    keywords: [
      'JPG to WEBP',
      'JPG to WEBP converter',
      'convert JPG to WEBP',
      'JPG to WEBP online',
      'free JPG to WEBP converter',
    ],
    intro:
      'Convert JPEG images into Google WebP format. WebP provides superior lossy compression for fast-loading web images.',
    features: [
      'Up to 30% smaller file sizes than JPG',
      'Boosts web page speed and SEO Core Web Vitals',
      'Lossy and lossless WebP rendering',
    ],
    steps: [
      'Upload your JPG image.',
      'Convert to WebP format.',
      'Download your web-optimized WebP file.',
    ],
    faqs: [
      {
        question: 'Why convert images to WebP?',
        answer:
          'WebP files are significantly smaller than JPG while maintaining equivalent visual quality, speeding up site performance.',
      },
    ],
    relatedSlugs: ['webp-to-jpg', 'png-to-webp', 'jpg-to-png'],
  },

  'webp-to-jpg': {
    slug: 'webp-to-jpg',
    sourceFormat: 'webp',
    targetFormat: 'jpg',
    sourceLabel: 'WebP',
    targetLabel: 'JPG',
    category: 'image',
    name: 'WebP to JPG Converter',
    h1: 'WebP to JPG Converter',
    title: 'WebP to JPG Converter – Convert WebP to JPG Online | VELTO',
    description:
      'Convert WebP web images to standard JPG format online with VELTO Conversion. Compatible with all image viewers.',
    keywords: [
      'WEBP converter',
      'WEBP to JPG',
      'WEBP to JPG converter',
      'convert WEBP online',
      'convert WEBP to JPG',
      'free WEBP to JPG converter',
    ],
    intro:
      'Convert web-based WebP images into universal JPG format so you can open, edit, and share them anywhere.',
    features: [
      'Universal compatibility with offline photo editors and software',
      'Fast single-click conversion',
      'Retains photo brightness and clarity',
    ],
    steps: [
      'Upload your WebP file.',
      'Click convert to transform into JPG.',
      'Download your standard JPG photo.',
    ],
    faqs: [
      {
        question: 'Why can’t some older programs open WebP files?',
        answer:
          'WebP is a newer image format created by Google. Converting WebP to JPG restores compatibility with legacy software and devices.',
      },
    ],
    relatedSlugs: ['jpg-to-webp', 'webp-to-png', 'jpg-to-png'],
  },

  'webp-to-png': {
    slug: 'webp-to-png',
    sourceFormat: 'webp',
    targetFormat: 'png',
    sourceLabel: 'WebP',
    targetLabel: 'PNG',
    category: 'image',
    name: 'WebP to PNG Converter',
    h1: 'WebP to PNG Converter',
    title: 'WebP to PNG Converter – Convert WebP to PNG Online | VELTO',
    description:
      'Convert WebP images to PNG with transparency support online with VELTO Conversion.',
    keywords: [
      'WEBP to PNG',
      'WEBP to PNG converter',
      'convert WEBP to PNG',
      'WEBP to PNG online',
      'free WEBP to PNG converter',
    ],
    intro:
      'Convert WebP graphics into lossless PNG images while maintaining alpha transparency layers.',
    features: [
      'Preserves transparent backgrounds and alpha channels',
      'Ideal for web graphic design and logo assets',
      'Encrypted processing pipeline',
    ],
    steps: [
      'Upload your WebP image file.',
      'Convert to PNG format.',
      'Download your PNG picture.',
    ],
    faqs: [
      {
        question: 'Will transparency be kept in the output PNG?',
        answer:
          'Yes, VELTO preserves alpha channel transparency when converting WebP images to PNG format.',
      },
    ],
    relatedSlugs: ['webp-to-jpg', 'png-to-webp', 'png-to-jpg'],
  },

  'png-to-webp': {
    slug: 'png-to-webp',
    sourceFormat: 'png',
    targetFormat: 'webp',
    sourceLabel: 'PNG',
    targetLabel: 'WebP',
    category: 'image',
    name: 'PNG to WebP Converter',
    h1: 'PNG to WebP Converter',
    title: 'PNG to WebP Converter – Convert PNG to WebP Online | VELTO',
    description:
      'Convert PNG images to WebP format online with VELTO Conversion. Smaller file sizes with transparency.',
    keywords: [
      'PNG to WEBP',
      'PNG to WEBP converter',
      'convert PNG to WEBP',
      'PNG to WEBP online',
      'free PNG to WEBP converter',
    ],
    intro:
      'Transform heavy PNG graphics into WebP files to reduce webpage payload while maintaining transparent backgrounds.',
    features: [
      'Reduces PNG image file sizes dramatically',
      'Supports transparent PNG graphics',
      'Fast cloud conversion engine',
    ],
    steps: [
      'Select your PNG image.',
      'Initiate WebP conversion.',
      'Download your WebP file.',
    ],
    faqs: [
      {
        question: 'Is WebP supported by all modern browsers?',
        answer:
          'Yes, Chrome, Safari, Firefox, Edge, and modern mobile browsers natively support WebP images.',
      },
    ],
    relatedSlugs: ['webp-to-png', 'jpg-to-webp', 'png-to-jpg'],
  },

  'bmp-to-png': {
    slug: 'bmp-to-png',
    sourceFormat: 'bmp',
    targetFormat: 'png',
    sourceLabel: 'BMP',
    targetLabel: 'PNG',
    category: 'image',
    name: 'BMP to PNG Converter',
    h1: 'BMP to PNG Converter',
    title: 'BMP to PNG Converter – Convert BMP to PNG Online | VELTO',
    description:
      'Convert uncompressed BMP bitmaps to compressed PNG images online with VELTO Conversion.',
    keywords: [
      'BMP converter',
      'BMP to PNG',
      'BMP to PNG converter',
      'convert BMP online',
      'free BMP to PNG converter',
    ],
    intro:
      'Convert raw Windows bitmap (BMP) files into compressed PNG format without losing visual detail.',
    features: [
      'Reduces bulky BMP file sizes without quality loss',
      'Compatible with web and graphic software',
      'Instant conversion',
    ],
    steps: [
      'Upload your .bmp image file.',
      'Convert to PNG.',
      'Download your compressed PNG image.',
    ],
    faqs: [
      {
        question: 'Why are BMP files so large?',
        answer:
          'BMP files store pixel data uncompressed. Converting BMP to PNG uses lossless compression to make files much smaller.',
      },
    ],
    relatedSlugs: ['bmp-to-jpg', 'png-to-jpg', 'jpg-to-png'],
  },

  'bmp-to-jpg': {
    slug: 'bmp-to-jpg',
    sourceFormat: 'bmp',
    targetFormat: 'jpg',
    sourceLabel: 'BMP',
    targetLabel: 'JPG',
    category: 'image',
    name: 'BMP to JPG Converter',
    h1: 'BMP to JPG Converter',
    title: 'BMP to JPG Converter – Convert BMP to JPG Online | VELTO',
    description:
      'Convert BMP bitmap images to standard JPG format online with VELTO Conversion.',
    keywords: [
      'BMP to JPG',
      'BMP to JPG converter',
      'convert BMP to JPG',
      'free BMP to JPG converter',
    ],
    intro:
      'Convert legacy BMP bitmap files into compact JPEG photos suitable for digital storage and sharing.',
    features: [
      'Drastically reduces file size',
      'Broad compatibility',
      'Quick web conversion',
    ],
    steps: [
      'Upload your BMP file.',
      'Convert to JPG format.',
      'Download your JPEG image.',
    ],
    faqs: [
      {
        question: 'Can I open the JPG on any device?',
        answer:
          'Yes, JPG is universally supported across every operating system and photo viewer.',
      },
    ],
    relatedSlugs: ['bmp-to-png', 'jpg-to-png', 'png-to-jpg'],
  },

  'tiff-to-png': {
    slug: 'tiff-to-png',
    sourceFormat: 'tiff',
    targetFormat: 'png',
    sourceLabel: 'TIFF',
    targetLabel: 'PNG',
    category: 'image',
    name: 'TIFF to PNG Converter',
    h1: 'TIFF to PNG Converter',
    title: 'TIFF to PNG Converter – Convert TIFF to PNG Online | VELTO',
    description:
      'Convert scanned TIFF documents and photos into PNG format online with VELTO Conversion.',
    keywords: [
      'TIFF converter',
      'TIFF to PNG',
      'TIFF to PNG converter',
      'convert TIFF online',
      'free TIFF to PNG converter',
    ],
    intro:
      'Convert high-resolution TIFF images into web-ready PNG files while preserving sharp detail.',
    features: [
      'Handles scanned documents and desktop graphics',
      'Lossless image conversion',
      'Zero software required',
    ],
    steps: [
      'Upload your TIFF image.',
      'Convert to PNG.',
      'Download your PNG picture.',
    ],
    faqs: [
      {
        question: 'Can TIFF files be displayed directly on websites?',
        answer:
          'No, web browsers cannot display raw TIFF files. Converting TIFF to PNG allows them to be viewed natively on web pages.',
      },
    ],
    relatedSlugs: ['tiff-to-jpg', 'png-to-jpg', 'jpg-to-png'],
  },

  'tiff-to-jpg': {
    slug: 'tiff-to-jpg',
    sourceFormat: 'tiff',
    targetFormat: 'jpg',
    sourceLabel: 'TIFF',
    targetLabel: 'JPG',
    category: 'image',
    name: 'TIFF to JPG Converter',
    h1: 'TIFF to JPG Converter',
    title: 'TIFF to JPG Converter – Convert TIFF to JPG Online | VELTO',
    description:
      'Convert multi-megabyte TIFF images into compact JPG photos online with VELTO Conversion.',
    keywords: [
      'TIFF to JPG',
      'TIFF to JPG converter',
      'convert TIFF to JPG',
      'free TIFF to JPG converter',
    ],
    intro:
      'Convert heavy TIFF image scans into lightweight JPG pictures for easy emailing and viewing.',
    features: [
      'Massive file size reduction',
      'High visual clarity',
      'Secure document pipeline',
    ],
    steps: [
      'Upload your .tiff image.',
      'Convert to JPG format.',
      'Download your JPEG photo.',
    ],
    faqs: [
      {
        question: 'Is my TIFF document file private?',
        answer:
          'Yes, VELTO encrypts file transfers and deletes files immediately after processing.',
      },
    ],
    relatedSlugs: ['tiff-to-png', 'jpg-to-png', 'png-to-jpg'],
  },

  'gif-to-png': {
    slug: 'gif-to-png',
    sourceFormat: 'gif',
    targetFormat: 'png',
    sourceLabel: 'GIF',
    targetLabel: 'PNG',
    category: 'image',
    name: 'GIF to PNG Converter',
    h1: 'GIF to PNG Converter',
    title: 'GIF to PNG Converter – Convert GIF to PNG Online | VELTO',
    description:
      'Convert static or animated GIF frames into crisp PNG images online with VELTO Conversion.',
    keywords: [
      'GIF converter',
      'GIF to PNG',
      'GIF to PNG converter',
      'convert GIF online',
      'free GIF to PNG converter',
    ],
    intro:
      'Extract static graphics or convert GIF images into crisp PNG format with full color resolution.',
    features: [
      'Expands 256-color GIF limit to 24-bit PNG color depth',
      'Preserves transparent background areas',
      'Fast online execution',
    ],
    steps: [
      'Upload your GIF file.',
      'Convert GIF to PNG format.',
      'Download your high-color PNG file.',
    ],
    faqs: [
      {
        question: 'Will color depth improve when converting GIF to PNG?',
        answer:
          'PNG supports millions of colors compared to GIF’s 256-color palette, resulting in smoother gradients and sharper graphics.',
      },
    ],
    relatedSlugs: ['gif-to-jpg', 'png-to-jpg', 'jpg-to-png'],
  },

  'gif-to-jpg': {
    slug: 'gif-to-jpg',
    sourceFormat: 'gif',
    targetFormat: 'jpg',
    sourceLabel: 'GIF',
    targetLabel: 'JPG',
    category: 'image',
    name: 'GIF to JPG Converter',
    h1: 'GIF to JPG Converter',
    title: 'GIF to JPG Converter – Convert GIF to JPG Online | VELTO',
    description:
      'Convert GIF files to JPEG images online with VELTO Conversion. Simple and fast.',
    keywords: [
      'GIF to JPG',
      'GIF to JPG converter',
      'convert GIF to JPG',
      'free GIF to JPG converter',
    ],
    intro:
      'Convert GIF image files into standard JPEG pictures for universal compatibility.',
    features: [
      'Fast single-click conversion',
      'Compact file output',
      '100% web based',
    ],
    steps: [
      'Select your GIF file.',
      'Convert to JPG format.',
      'Download your JPEG image.',
    ],
    faqs: [
      {
        question: 'Can I convert any GIF file?',
        answer:
          'Yes, VELTO processes static and animated GIF files, outputting a high-quality JPEG image.',
      },
    ],
    relatedSlugs: ['gif-to-png', 'jpg-to-png', 'png-to-jpg'],
  },

  // ── ARCHIVE & SPECIAL CONVERTERS ────────────────────────────────────────────
  'jpg-to-zip': {
    slug: 'jpg-to-zip',
    sourceFormat: 'jpg',
    targetFormat: 'zip',
    sourceLabel: 'JPG',
    targetLabel: 'ZIP Archive',
    category: 'archive',
    name: 'JPG to ZIP Converter',
    h1: 'JPG to ZIP Converter',
    title: 'JPG to ZIP Converter – Compress JPG into ZIP Online | VELTO',
    description:
      'Package and compress JPG images into a clean ZIP archive online with VELTO Conversion.',
    keywords: [
      'ZIP converter',
      'JPG to ZIP',
      'convert JPG to ZIP',
      'image to ZIP',
      'create ZIP online',
      'online file compression',
    ],
    intro:
      'Bundle and compress your JPG files into a single ZIP archive for easy sharing and backup.',
    features: [
      'Bundles files into a compressed ZIP file',
      'Saves bandwidth when sharing multiple photos',
      'Instant archive creation',
    ],
    steps: [
      'Upload your JPG image.',
      'Click convert to create the ZIP file.',
      'Download your ZIP archive.',
    ],
    faqs: [
      {
        question: 'Why compress images into a ZIP archive?',
        answer:
          'ZIP archives bundle files together into a single downloadable file, preventing email attachment limits.',
      },
    ],
    relatedSlugs: ['png-to-zip', 'webp-to-zip', 'jpg-to-pdf'],
  },

  'png-to-zip': {
    slug: 'png-to-zip',
    sourceFormat: 'png',
    targetFormat: 'zip',
    sourceLabel: 'PNG',
    targetLabel: 'ZIP Archive',
    category: 'archive',
    name: 'PNG to ZIP Converter',
    h1: 'PNG to ZIP Converter',
    title: 'PNG to ZIP Converter – Compress PNG into ZIP Online | VELTO',
    description:
      'Bundle PNG images into a ZIP archive online with VELTO Conversion. Fast and secure archive tool.',
    keywords: [
      'PNG to ZIP',
      'convert PNG to ZIP',
      'PNG archive',
      'create ZIP online',
    ],
    intro:
      'Compress your PNG images into a organized ZIP archive file for quick download and transfer.',
    features: [
      'Creates standard ZIP files',
      'Lossless container storage',
      'Protected cloud processing',
    ],
    steps: [
      'Select your PNG image.',
      'Package file into ZIP archive.',
      'Download your ZIP file.',
    ],
    faqs: [
      {
        question: 'Can I extract the ZIP file on Mac and Windows?',
        answer:
          'Yes, standard ZIP archives created by VELTO open natively on Windows, macOS, iOS, Android, and Linux.',
      },
    ],
    relatedSlugs: ['jpg-to-zip', 'webp-to-zip', 'png-to-pdf'],
  },

  'webp-to-zip': {
    slug: 'webp-to-zip',
    sourceFormat: 'webp',
    targetFormat: 'zip',
    sourceLabel: 'WebP',
    targetLabel: 'ZIP Archive',
    category: 'archive',
    name: 'WebP to ZIP Converter',
    h1: 'WebP to ZIP Converter',
    title: 'WebP to ZIP Converter – Compress WebP into ZIP Online | VELTO',
    description:
      'Compress WebP web graphics into a ZIP archive online with VELTO Conversion.',
    keywords: [
      'WEBP to ZIP',
      'convert WEBP to ZIP',
      'create ZIP online',
    ],
    intro:
      'Package your WebP files into a compressed ZIP file for easy storage and sharing.',
    features: [
      'Fast ZIP compression',
      'Organizes web image assets',
      'Secure transfer',
    ],
    steps: [
      'Upload WebP image file.',
      'Convert to ZIP archive.',
      'Download compressed ZIP.',
    ],
    faqs: [
      {
        question: 'How fast is ZIP creation?',
        answer:
          'ZIP archives are created in seconds using VELTO high-performance cloud storage.',
      },
    ],
    relatedSlugs: ['jpg-to-zip', 'png-to-zip', 'webp-to-jpg'],
  },

  'txt-to-pdf': {
    slug: 'txt-to-pdf',
    sourceFormat: 'txt',
    targetFormat: 'pdf',
    sourceLabel: 'TXT',
    targetLabel: 'PDF',
    category: 'document',
    name: 'TXT to PDF Converter',
    h1: 'TXT to PDF Converter',
    title: 'TXT to PDF Converter – Convert Text to PDF Online | VELTO',
    description:
      'Convert plain text (TXT) files into formatted PDF documents online with VELTO Conversion.',
    keywords: [
      'TXT to PDF',
      'convert TXT to PDF',
      'text to PDF converter',
      'convert text online',
    ],
    intro:
      'Convert plain text files into clean, printable PDF documents with custom typography and layout styling.',
    features: [
      'Formats plain text cleanly onto PDF pages',
      'Prevents font distortion and line wrapping errors',
      'Fast online execution',
    ],
    steps: [
      'Upload your .txt file.',
      'Click convert to transform into PDF.',
      'Download your PDF document.',
    ],
    faqs: [
      {
        question: 'Will special characters and line breaks be preserved?',
        answer:
          'Yes, VELTO maintains UTF-8 encoding so text characters, code snippets, and line spaces render accurately.',
      },
    ],
    relatedSlugs: ['txt-to-docx', 'md-to-pdf', 'html-to-pdf'],
  },

  'txt-to-docx': {
    slug: 'txt-to-docx',
    sourceFormat: 'txt',
    targetFormat: 'docx',
    sourceLabel: 'TXT',
    targetLabel: 'Word (DOCX)',
    category: 'document',
    name: 'TXT to Word Converter',
    h1: 'TXT to Word Converter',
    title: 'TXT to Word Converter – Convert Text to DOCX Online | VELTO',
    description:
      'Convert plain text (TXT) files into Microsoft Word (DOCX) documents online with VELTO Conversion.',
    keywords: [
      'TXT to DOCX',
      'TXT to Word',
      'convert TXT to Word',
      'convert text to DOCX',
    ],
    intro:
      'Turn raw text files into Microsoft Word DOCX documents so you can add styling, headings, and images.',
    features: [
      'Direct conversion from plain text to Word DOCX',
      'Maintains original paragraphs',
      'Fully editable output file',
    ],
    steps: [
      'Select your TXT file.',
      'Convert text to Word DOCX.',
      'Download your Word document.',
    ],
    faqs: [
      {
        question: 'Can I edit the converted Word file?',
        answer:
          'Yes, the output is a native Microsoft Word DOCX file that you can format freely.',
      },
    ],
    relatedSlugs: ['txt-to-pdf', 'md-to-docx', 'html-to-docx'],
  },

  'html-to-pdf': {
    slug: 'html-to-pdf',
    sourceFormat: 'html',
    targetFormat: 'pdf',
    sourceLabel: 'HTML',
    targetLabel: 'PDF',
    category: 'document',
    name: 'HTML to PDF Converter',
    h1: 'HTML to PDF Converter',
    title: 'HTML to PDF Converter – Convert HTML to PDF Online | VELTO',
    description:
      'Convert HTML web pages and code to PDF documents online with VELTO Conversion.',
    keywords: [
      'HTML to PDF',
      'convert HTML to PDF',
      'HTML to PDF converter',
      'webpage to PDF',
    ],
    intro:
      'Render HTML files and web documents into clean, vectorized PDF pages with intact CSS styling.',
    features: [
      'Accurate CSS and HTML layout rendering',
      'Ideal for saving receipts, web reports, and documentation',
      'Encrypted processing pipeline',
    ],
    steps: [
      'Upload your HTML file.',
      'Convert HTML structure to PDF.',
      'Download your PDF document.',
    ],
    faqs: [
      {
        question: 'Does HTML to PDF render CSS styles?',
        answer:
          'Yes, VELTO renders inline CSS and styled HTML elements into the resulting PDF page.',
      },
    ],
    relatedSlugs: ['html-to-docx', 'md-to-pdf', 'txt-to-pdf'],
  },

  'html-to-docx': {
    slug: 'html-to-docx',
    sourceFormat: 'html',
    targetFormat: 'docx',
    sourceLabel: 'HTML',
    targetLabel: 'Word (DOCX)',
    category: 'document',
    name: 'HTML to Word Converter',
    h1: 'HTML to Word Converter',
    title: 'HTML to Word Converter – Convert HTML to DOCX Online | VELTO',
    description:
      'Convert HTML web files to editable Microsoft Word (DOCX) documents online with VELTO Conversion.',
    keywords: [
      'HTML to DOCX',
      'HTML to Word',
      'convert HTML to Word',
      'convert HTML to DOCX',
    ],
    intro:
      'Convert HTML code and web articles into editable Microsoft Word documents for offline editing.',
    features: [
      'Extracts headings, paragraphs, and list structures',
      'Creates native Microsoft Word files',
      'Fast online tool',
    ],
    steps: [
      'Upload your HTML document.',
      'Convert to DOCX format.',
      'Download your Word file.',
    ],
    faqs: [
      {
        question: 'Are web links preserved in the Word document?',
        answer:
          'Yes, hyperlinks in your HTML file are converted into active Word hyperlinks.',
      },
    ],
    relatedSlugs: ['html-to-pdf', 'txt-to-docx', 'md-to-docx'],
  },

  'md-to-pdf': {
    slug: 'md-to-pdf',
    sourceFormat: 'md',
    targetFormat: 'pdf',
    sourceLabel: 'Markdown (MD)',
    targetLabel: 'PDF',
    category: 'document',
    name: 'Markdown to PDF Converter',
    h1: 'Markdown to PDF Converter',
    title: 'Markdown to PDF Converter – Convert MD to PDF Online | VELTO',
    description:
      'Convert Markdown (.md) documents to styled PDF files online with VELTO Conversion.',
    keywords: [
      'MD to PDF',
      'Markdown to PDF',
      'convert Markdown to PDF',
      'convert MD to PDF',
    ],
    intro:
      'Transform developer documentation, READMEs, and Markdown notes into beautifully rendered PDF files.',
    features: [
      'Renders Markdown headers, code blocks, lists, and tables',
      'Clean typography and page pagination',
      'Fast online execution',
    ],
    steps: [
      'Upload your Markdown (.md) file.',
      'Render Markdown into PDF.',
      'Download your PDF document.',
    ],
    faqs: [
      {
        question: 'Are code blocks formatted in the output PDF?',
        answer:
          'Yes, code blocks and inline code syntax are styled cleanly in the generated PDF.',
      },
    ],
    relatedSlugs: ['md-to-docx', 'txt-to-pdf', 'html-to-pdf'],
  },

  'md-to-docx': {
    slug: 'md-to-docx',
    sourceFormat: 'md',
    targetFormat: 'docx',
    sourceLabel: 'Markdown (MD)',
    targetLabel: 'Word (DOCX)',
    category: 'document',
    name: 'Markdown to Word Converter',
    h1: 'Markdown to Word Converter',
    title: 'Markdown to Word Converter – Convert MD to DOCX Online | VELTO',
    description:
      'Convert Markdown (.md) files into editable Microsoft Word (DOCX) documents online with VELTO Conversion.',
    keywords: [
      'MD to DOCX',
      'Markdown to Word',
      'convert Markdown to Word',
      'convert MD to DOCX',
    ],
    intro:
      'Convert Markdown technical notes and README files into Microsoft Word documents.',
    features: [
      'Converts Markdown syntax into Word heading styles',
      'Preserves lists, bolding, italics, and quotes',
      'Fully editable DOCX output',
    ],
    steps: [
      'Upload your .md file.',
      'Convert Markdown to DOCX.',
      'Download your Microsoft Word document.',
    ],
    faqs: [
      {
        question: 'Can I edit the output file in Word?',
        answer:
          'Yes, headings and text styles map directly to standard Microsoft Word styles.',
      },
    ],
    relatedSlugs: ['md-to-pdf', 'txt-to-docx', 'html-to-docx'],
  },
};

/**
 * Supported alias map pointing to primary tool configs.
 */
export const TOOL_ALIASES: Record<string, string> = {
  'pdf-to-excel': 'pdf-to-excel',
  'pdf-to-xlsx': 'pdf-to-excel',
  'excel-to-pdf': 'excel-to-pdf',
  'xlsx-to-pdf': 'xlsx-to-pdf',
  'pdf-to-powerpoint': 'pdf-to-powerpoint',
  'pdf-to-pptx': 'pdf-to-powerpoint',
  'powerpoint-to-pdf': 'powerpoint-to-pdf',
  'pptx-to-pdf': 'pptx-to-pdf',
  'word-to-jpg': 'docx-to-jpg',
  'word-to-png': 'docx-to-png',
  'excel-to-jpg': 'xlsx-to-jpg',
  'excel-to-png': 'xlsx-to-png',
  'powerpoint-to-jpg': 'pptx-to-jpg',
  'powerpoint-to-png': 'pptx-to-png',
  'csv-to-excel': 'csv-to-xlsx',
};

/**
 * Returns tool SEO config by slug or alias slug.
 */
export function getToolConfig(slug: string): ToolSeoConfig | null {
  const normalizedSlug = slug.toLowerCase().trim();
  if (SUPPORTED_TOOLS[normalizedSlug]) {
    return SUPPORTED_TOOLS[normalizedSlug];
  }
  const targetSlug = TOOL_ALIASES[normalizedSlug];
  if (targetSlug && SUPPORTED_TOOLS[targetSlug]) {
    return SUPPORTED_TOOLS[targetSlug];
  }
  return null;
}

/**
 * Generates JSON-LD structured data for a tool page (SoftwareApplication + BreadcrumbList + FAQPage).
 */
export function getToolStructuredData(config: ToolSeoConfig) {
  const pageUrl = `${SITE_CONFIG.domain}/tools/${config.slug}`;

  const softwareAppSchema = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    '@id': `${pageUrl}#application`,
    name: config.name,
    operatingSystem: 'All (Web Browser)',
    applicationCategory: 'BusinessApplication',
    offers: {
      '@type': 'Offer',
      price: '0.00',
      priceCurrency: 'USD',
      availability: 'https://schema.org/InStock',
    },
    url: pageUrl,
    description: config.description,
    provider: {
      '@type': 'Organization',
      name: SITE_CONFIG.brandName,
      url: SITE_CONFIG.domain,
    },
  };

  const breadcrumbSchema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      {
        '@type': 'ListItem',
        position: 1,
        name: 'Home',
        item: SITE_CONFIG.domain,
      },
      {
        '@type': 'ListItem',
        position: 2,
        name: 'Tools',
        item: `${SITE_CONFIG.domain}/tools`,
      },
      {
        '@type': 'ListItem',
        position: 3,
        name: config.name,
        item: pageUrl,
      },
    ],
  };

  const faqSchema =
    config.faqs && config.faqs.length > 0
      ? {
          '@context': 'https://schema.org',
          '@type': 'FAQPage',
          mainEntity: config.faqs.map((faq) => ({
            '@type': 'Question',
            name: faq.question,
            acceptedAnswer: {
              '@type': 'Answer',
              text: faq.answer,
            },
          })),
        }
      : null;

  return faqSchema ? [softwareAppSchema, breadcrumbSchema, faqSchema] : [softwareAppSchema, breadcrumbSchema];
}
