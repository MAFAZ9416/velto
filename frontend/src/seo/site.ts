/**
 * VELTO Conversion — Master Site SEO Configuration
 * Central configuration for domain, brand metadata, and structured data schemas.
 */

export const SITE_CONFIG = {
  domain: 'https://velto-brown.vercel.app',
  brandName: 'VELTO Conversion',
  brandShortName: 'VELTO',
  tagline: 'Convert. Transform. Done.',
  defaultTitle: 'VELTO Conversion – Free Online File Converter',
  titleTemplate: '%s | VELTO',
  defaultDescription:
    'Convert PDF, Word, Excel, PowerPoint, images and more online with VELTO Conversion. Fast, secure, and easy-to-use online file conversion tools for your documents.',
  defaultOgImage: 'https://velto-brown.vercel.app/og-image.png',
  twitterHandle: '@VeltoConversion',
  
  // Verification Token Placeholders for GSC and Bing
  googleSearchConsoleToken: import.meta.env.VITE_GSC_VERIFICATION || '',
  bingWebmasterToken: import.meta.env.VITE_BING_VERIFICATION || '',
};

/**
 * Generates JSON-LD WebSite and Organization schema for the website root.
 */
export function getSiteStructuredData() {
  return [
    {
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      '@id': `${SITE_CONFIG.domain}/#website`,
      url: SITE_CONFIG.domain,
      name: SITE_CONFIG.brandName,
      alternateName: ['VELTO', 'VELTO Converter', 'VELTO Online Converter'],
      description: SITE_CONFIG.defaultDescription,
      potentialAction: {
        '@type': 'SearchAction',
        target: {
          '@type': 'EntryPoint',
          urlTemplate: `${SITE_CONFIG.domain}/tools?q={search_term_string}`,
        },
        'query-input': 'required name=search_term_string',
      },
    },
    {
      '@context': 'https://schema.org',
      '@type': 'Organization',
      '@id': `${SITE_CONFIG.domain}/#organization`,
      name: SITE_CONFIG.brandName,
      url: SITE_CONFIG.domain,
      logo: `${SITE_CONFIG.domain}/favicon.svg`,
      sameAs: [],
    },
  ];
}
