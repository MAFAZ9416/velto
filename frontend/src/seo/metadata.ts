/**
 * VELTO Conversion — Metadata Resolver
 * Resolves title, description, canonical, OG metadata, keywords, and indexability rules
 * for any given pathname in the application.
 */

import { SITE_CONFIG, getSiteStructuredData } from './site';
import { getToolConfig, getToolStructuredData } from './tools';

export interface PageSeoMetadata {
  title: string;
  description: string;
  canonicalUrl: string;
  keywords: string[];
  ogType: 'website' | 'article';
  ogImage: string;
  noindex: boolean;
  structuredData?: any[];
}

/**
 * Given a URL pathname (e.g. '/' or '/tools/pdf-to-word' or '/login'),
 * returns the complete PageSeoMetadata object.
 */
export function getSeoMetadata(pathname: string): PageSeoMetadata {
  const cleanPath = pathname.split('?')[0].split('#')[0].replace(/\/$/, '') || '/';

  // 1. Homepage
  if (cleanPath === '/') {
    return {
      title: 'VELTO Conversion – Free Online File Converter',
      description:
        'Convert PDF, Word, Excel, PowerPoint, images and documents online with VELTO Conversion. Fast, secure, easy-to-use online file converter tools.',
      canonicalUrl: `${SITE_CONFIG.domain}/`,
      keywords: [
        'VELTO',
        'VELTO Conversion',
        'file converter',
        'online file converter',
        'free file converter',
        'convert files online',
        'document converter',
        'online file conversion',
        'VELTO file converter',
        'universal file converter',
      ],
      ogType: 'website',
      ogImage: SITE_CONFIG.defaultOgImage,
      noindex: false,
      structuredData: getSiteStructuredData(),
    };
  }

  // 2. Tools Directory Page
  if (cleanPath === '/tools') {
    return {
      title: 'Online File Conversion Tools & PDF Utilities | VELTO',
      description:
        'Explore VELTO online file converter tools. Convert PDF to Word, Word to PDF, Excel to PDF, JPG to PNG, WebP converters and more in your browser.',
      canonicalUrl: `${SITE_CONFIG.domain}/tools`,
      keywords: [
        'file conversion tools',
        'online converter tools',
        'PDF tools',
        'document conversion tools',
        'image conversion tools',
        'VELTO conversion tools',
      ],
      ogType: 'website',
      ogImage: SITE_CONFIG.defaultOgImage,
      noindex: false,
    };
  }

  // 3. Pricing Page
  if (cleanPath === '/pricing') {
    return {
      title: 'Pricing & Plans – Flexible File Conversion | VELTO',
      description:
        'Choose the VELTO plan that fits your workflow. Free guest conversions, un-throttled batch processing, and high-speed document engines.',
      canonicalUrl: `${SITE_CONFIG.domain}/pricing`,
      keywords: [
        'VELTO pricing',
        'file converter plans',
        'free PDF converter',
        'pro file converter',
      ],
      ogType: 'website',
      ogImage: SITE_CONFIG.defaultOgImage,
      noindex: false,
    };
  }

  // 4. Dynamic Tool Landing Pages: /tools/:tool
  if (cleanPath.startsWith('/tools/')) {
    const slug = cleanPath.replace('/tools/', '');
    const toolConfig = getToolConfig(slug);

    if (toolConfig) {
      return {
        title: toolConfig.title,
        description: toolConfig.description,
        canonicalUrl: `${SITE_CONFIG.domain}/tools/${toolConfig.slug}`,
        keywords: toolConfig.keywords,
        ogType: 'website',
        ogImage: SITE_CONFIG.defaultOgImage,
        noindex: false,
        structuredData: getToolStructuredData(toolConfig),
      };
    } else {
      // If tool slug is unknown, page will render 404, so set noindex
      return {
        title: 'Tool Not Found | VELTO Conversion',
        description: 'The requested file conversion tool was not found on VELTO.',
        canonicalUrl: `${SITE_CONFIG.domain}${cleanPath}`,
        keywords: [],
        ogType: 'website',
        ogImage: SITE_CONFIG.defaultOgImage,
        noindex: true,
      };
    }
  }

  // 5. Auth pages — NOINDEX
  const authRoutes = ['/login', '/register', '/forgot-password', '/reset-password', '/verify-email'];
  if (authRoutes.some((route) => cleanPath.startsWith(route))) {
    return {
      title: 'Account Authentication | VELTO Conversion',
      description: 'Sign in or register for VELTO Conversion.',
      canonicalUrl: `${SITE_CONFIG.domain}${cleanPath}`,
      keywords: [],
      ogType: 'website',
      ogImage: SITE_CONFIG.defaultOgImage,
      noindex: true,
    };
  }

  // 6. App/Private protected pages — NOINDEX
  const privateRoutes = [
    '/dashboard',
    '/convert',
    '/conversions',
    '/account',
    '/settings',
    '/convert/processing',
    '/convert/result',
  ];
  if (privateRoutes.some((route) => cleanPath.startsWith(route))) {
    return {
      title: 'VELTO Conversion App',
      description: 'Private dashboard and conversion management area.',
      canonicalUrl: `${SITE_CONFIG.domain}${cleanPath}`,
      keywords: [],
      ogType: 'website',
      ogImage: SITE_CONFIG.defaultOgImage,
      noindex: true,
    };
  }

  // 7. Error pages (403, 500, 404) — NOINDEX, FOLLOW
  return {
    title: 'Page Not Found – 404 | VELTO Conversion',
    description: 'The requested page could not be found on VELTO Conversion.',
    canonicalUrl: `${SITE_CONFIG.domain}/404`,
    keywords: [],
    ogType: 'website',
    ogImage: SITE_CONFIG.defaultOgImage,
    noindex: true,
  };
}
