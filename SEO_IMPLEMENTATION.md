# VELTO CONVERSION — PRODUCTION SEO MASTER IMPLEMENTATION

## Executive Summary

VELTO Conversion is an enterprise-grade file conversion platform designed for document, spreadsheet, presentation, image, and text transformation.

This document details the complete production SEO architecture implemented across the VELTO application, covering:
1. **Technical SEO Infrastructure**
2. **Dynamic Converter Landing Pages**
3. **Keyword Mapping & Topic Distribution**
4. **Structured Data Schemas (JSON-LD)**
5. **Crawlability & Indexability Rules**
6. **Social Sharing & OpenGraph Protocols**
7. **Search Console & Webmaster Readiness**
8. **Scalable Procedure for Adding New Tools**

---

## 1. SEO Architecture & Directory Structure

```
frontend/
├── index.html                  # HTML template with default meta tags, language, OpenGraph defaults
├── vercel.json                 # Vercel SPA rewrites for direct /tools/* routing
├── public/
│   ├── robots.txt              # Production robots instructions & sitemap link
│   ├── sitemap.xml             # Production XML sitemap listing indexable URLs
│   ├── favicon.svg             # Brand vector icon
│   └── og-image.svg            # Branded social sharing card asset
└── src/
    ├── seo/
    │   ├── site.ts             # Site-wide brand metadata & WebSite/Organization JSON-LD
    │   ├── tools.ts            # Supported conversion pairs registry, FAQs, features, steps, schemas
    │   └── metadata.ts         # Central URL path metadata resolver (titles, canonicals, noindex)
    ├── components/
    │   └── seo/
    │       └── SeoHead.tsx     # React component managing head tags dynamically per route
    └── pages/
        ├── public/
        │   ├── HomePage.tsx    # Optimized homepage targeting core brand & online file converter terms
        │   └── PricingPage.tsx # Pricing page metadata & structured pricing details
        ├── tools/
        │   ├── ToolsPage.tsx   # Tools directory with internal links to landing pages
        │   └── ToolDetailPage.tsx # Dynamic landing page for /tools/:tool
        └── errors/
            └── NotFoundPage.tsx # SEO-safe 404 page with noindex & popular converter links
```

---

## 2. Route Indexability Matrix

| Path | Indexability | Target Keyword Intent | Canonical URL |
| :--- | :--- | :--- | :--- |
| `/` | `INDEX, FOLLOW` | Brand, Online File Converter, Free Converter | `https://velto-brown.vercel.app/` |
| `/tools` | `INDEX, FOLLOW` | Conversion Tools Directory, PDF Utilities | `https://velto-brown.vercel.app/tools` |
| `/tools/pdf-to-word` | `INDEX, FOLLOW` | PDF to Word, PDF to DOCX, Convert PDF to Word | `https://velto-brown.vercel.app/tools/pdf-to-word` |
| `/tools/word-to-pdf` | `INDEX, FOLLOW` | Word to PDF, DOCX to PDF, Convert Word to PDF | `https://velto-brown.vercel.app/tools/word-to-pdf` |
| `/tools/pdf-to-excel` | `INDEX, FOLLOW` | PDF to Excel, PDF to XLSX, Extract PDF Tables | `https://velto-brown.vercel.app/tools/pdf-to-excel` |
| `/tools/excel-to-pdf` | `INDEX, FOLLOW` | Excel to PDF, XLSX to PDF, Spreadsheet PDF | `https://velto-brown.vercel.app/tools/excel-to-pdf` |
| `/tools/pdf-to-powerpoint` | `INDEX, FOLLOW` | PDF to PowerPoint, PDF to PPTX | `https://velto-brown.vercel.app/tools/pdf-to-powerpoint` |
| `/tools/powerpoint-to-pdf` | `INDEX, FOLLOW` | PowerPoint to PDF, PPTX to PDF | `https://velto-brown.vercel.app/tools/powerpoint-to-pdf` |
| `/tools/pdf-to-jpg` | `INDEX, FOLLOW` | PDF to JPG, PDF pages to image | `https://velto-brown.vercel.app/tools/pdf-to-jpg` |
| `/tools/pdf-to-png` | `INDEX, FOLLOW` | PDF to PNG, Lossless PDF rendering | `https://velto-brown.vercel.app/tools/pdf-to-png` |
| `/tools/jpg-to-png` | `INDEX, FOLLOW` | JPG to PNG, Transparent image conversion | `https://velto-brown.vercel.app/tools/jpg-to-png` |
| `/tools/png-to-jpg` | `INDEX, FOLLOW` | PNG to JPG, Compress image size | `https://velto-brown.vercel.app/tools/png-to-jpg` |
| `/tools/webp-to-jpg` | `INDEX, FOLLOW` | WebP to JPG, Convert web images | `https://velto-brown.vercel.app/tools/webp-to-jpg` |
| `/tools/jpg-to-pdf` | `INDEX, FOLLOW` | JPG to PDF, Photos to document | `https://velto-brown.vercel.app/tools/jpg-to-pdf` |
| `/pricing` | `INDEX, FOLLOW` | VELTO Pricing, Free vs Pro conversion | `https://velto-brown.vercel.app/pricing` |
| `/login` | `NOINDEX, NOFOLLOW` | Auth page (Protected) | `https://velto-brown.vercel.app/login` |
| `/register` | `NOINDEX, NOFOLLOW` | Auth page (Protected) | `https://velto-brown.vercel.app/register` |
| `/dashboard` | `NOINDEX, NOFOLLOW` | User dashboard (Private) | `https://velto-brown.vercel.app/dashboard` |
| `/convert` | `NOINDEX, NOFOLLOW` | Authenticated converter workspace | `https://velto-brown.vercel.app/convert` |
| `/conversions` | `NOINDEX, NOFOLLOW` | Conversion history (Private data) | `https://velto-brown.vercel.app/conversions` |
| `/account` | `NOINDEX, NOFOLLOW` | Account settings (Private data) | `https://velto-brown.vercel.app/account` |
| `/convert/processing` | `NOINDEX, NOFOLLOW` | Processing state (Private job ID) | `https://velto-brown.vercel.app/convert/processing` |
| `/convert/result/*` | `NOINDEX, NOFOLLOW` | Download result page (Private data) | `https://velto-brown.vercel.app/convert/result/*` |
| `*` (404 Error) | `NOINDEX, FOLLOW` | Error handling | `https://velto-brown.vercel.app/404` |

---

## 3. Keyword-to-Page Mapping

### A. Homepage (`/`)
- **Primary Keywords**: VELTO Conversion, VELTO converter, online file converter, free online file converter, file conversion online, document converter online.
- **Title**: `VELTO Conversion – Free Online File Converter`
- **Description**: `Convert PDF, Word, Excel, PowerPoint, images and documents online with VELTO Conversion. Fast, secure, easy-to-use online file converter tools.`

### B. PDF to Word (`/tools/pdf-to-word`)
- **Primary Keywords**: PDF to Word, PDF to Word converter, PDF to DOCX, convert PDF to Word, online PDF to Word converter, free PDF to Word converter.
- **Title**: `PDF to Word Converter – Convert PDF to Word Online | VELTO`
- **Description**: `Convert PDF files to editable Word (DOCX) documents online with VELTO Conversion. Fast, layout-preserving, and secure PDF to Word converter.`

### C. Word to PDF (`/tools/word-to-pdf`)
- **Primary Keywords**: Word to PDF, Word to PDF converter, DOCX to PDF, convert Word to PDF, online Word to PDF converter, free Word to PDF converter.
- **Title**: `Word to PDF Converter – Convert Word to PDF Online | VELTO`
- **Description**: `Convert Word documents (DOCX) to professional PDF files online with VELTO Conversion. Simple, instant, and high-fidelity Word to PDF tool.`

### D. PDF to Excel (`/tools/pdf-to-excel`)
- **Primary Keywords**: PDF to Excel, PDF to Excel converter, PDF to XLSX, extract PDF tables to Excel.
- **Title**: `PDF to Excel Converter – Convert PDF to Excel Online | VELTO`
- **Description**: `Extract tables and financial data from PDF to editable Excel (XLSX) spreadsheets online with VELTO Conversion.`

### E. Image Converters (`/tools/jpg-to-png`, `/tools/png-to-jpg`, `/tools/webp-to-jpg`)
- **Primary Keywords**: JPG to PNG, PNG to JPG, WEBP to JPG, image format converter online, convert image online.
- **Titles**: Format-specific titles formatted like `{Source} to {Target} Converter – Convert {Source} to {Target} Online | VELTO`.

---

## 4. Structured Data Implementation (JSON-LD)

VELTO injects schema objects into the document head dynamically using native `<script type="application/ld+json">`:

### 1. WebSite & Organization Schema (Homepage)
```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "@id": "https://velto-brown.vercel.app/#website",
  "url": "https://velto-brown.vercel.app",
  "name": "VELTO Conversion",
  "alternateName": ["VELTO", "VELTO Converter"],
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://velto-brown.vercel.app/tools?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
```

### 2. SoftwareApplication Schema (Converter Pages)
```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "PDF to Word Converter",
  "operatingSystem": "All (Web Browser)",
  "applicationCategory": "BusinessApplication",
  "offers": {
    "@type": "Offer",
    "price": "0.00",
    "priceCurrency": "USD"
  },
  "url": "https://velto-brown.vercel.app/tools/pdf-to-word"
}
```

### 3. BreadcrumbList Schema (Navigation)
```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://velto-brown.vercel.app" },
    { "@type": "ListItem", "position": 2, "name": "Tools", "item": "https://velto-brown.vercel.app/tools" },
    { "@type": "ListItem", "position": 3, "name": "PDF to Word Converter", "item": "https://velto-brown.vercel.app/tools/pdf-to-word" }
  ]
}
```

### 4. FAQPage Schema (Visible Accordion FAQs)
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is a PDF to Word converter?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "A PDF to Word converter takes portable document format (PDF) files and converts their contents into editable Microsoft Word (.docx) documents."
      }
    }
  ]
}
```

---

## 5. Google Search Console & Bing Setup

### Google Search Console (GSC)
1. Add property `https://velto-brown.vercel.app`.
2. Submit sitemap: `https://velto-brown.vercel.app/sitemap.xml`.
3. HTML tag verification placeholder supported via `VITE_GSC_VERIFICATION` in `.env`.

### Bing Webmaster Tools
1. Add site `https://velto-brown.vercel.app`.
2. Submit sitemap: `https://velto-brown.vercel.app/sitemap.xml`.
3. Verification placeholder supported via `VITE_BING_VERIFICATION` in `.env`.

---

## 6. Procedures for Adding a New Converter Landing Page

When VELTO adds a new conversion pair (e.g. `source_format` -> `target_format`) to `backend/apps/conversions/formats.py`:

1. Add the tool configuration object in `frontend/src/seo/tools.ts` under `SUPPORTED_TOOLS`:
```typescript
'newformat-to-target': {
  slug: 'newformat-to-target',
  sourceFormat: 'newformat',
  targetFormat: 'target',
  sourceLabel: 'NewFormat',
  targetLabel: 'Target',
  category: 'document',
  name: 'NewFormat to Target Converter',
  h1: 'NewFormat to Target Converter',
  title: 'NewFormat to Target Converter – Convert Online | VELTO',
  description: 'Convert NewFormat files to Target online with VELTO Conversion.',
  keywords: ['NewFormat to Target', 'convert NewFormat'],
  intro: 'Convert NewFormat to Target seamlessly with VELTO.',
  features: ['High quality conversion', 'Instant cloud processing'],
  steps: ['Upload file', 'Click convert', 'Download file'],
  faqs: [{ question: 'How long does it take?', answer: 'Conversions complete in seconds.' }],
  relatedSlugs: ['pdf-to-word', 'word-to-pdf']
}
```
2. Add the URL `<url><loc>https://velto-brown.vercel.app/tools/newformat-to-target</loc>...</url>` to `frontend/public/sitemap.xml`.
3. Build and test: `npm run build`. The landing page will automatically resolve with proper layout, interactive dropzone, breadcrumbs, structured data, and internal links!

---

## 7. Verification Checklist

- [x] TypeScript build passes (`npm run build`)
- [x] Canonical origin set to absolute production URL (`https://velto-brown.vercel.app`)
- [x] Every indexable landing page has exactly ONE H1 tag
- [x] Dynamic tool routes resolve with proper dropzone & SEO copy
- [x] Guest conversion flow works directly on tool landing pages
- [x] Authenticated conversion flow works directly on tool landing pages
- [x] Robots.txt disallows private dashboard/conversions/auth pages
- [x] Sitemap disallows private pages and lists all public converter tools
- [x] Vercel SPA routing configured via `vercel.json`
- [x] No private user data or secrets exposed in metadata or schemas
