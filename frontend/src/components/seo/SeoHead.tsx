/**
 * VELTO Conversion — Dynamic SEO Head Component
 * Updates document.title, meta tags, canonical link, OpenGraph tags,
 * Twitter cards, robots directives, and JSON-LD structured data on route changes.
 */

import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { getSeoMetadata } from '../../seo/metadata';
import { SITE_CONFIG } from '../../seo/site';

interface SeoHeadProps {
  title?: string;
  description?: string;
  canonicalUrl?: string;
  keywords?: string[];
  noindex?: boolean;
  ogType?: 'website' | 'article';
  ogImage?: string;
  structuredData?: any[];
}

export default function SeoHead(props: SeoHeadProps) {
  const location = useLocation();
  const defaultMeta = getSeoMetadata(location.pathname);

  const title = props.title || defaultMeta.title;
  const description = props.description || defaultMeta.description;
  const canonicalUrl = props.canonicalUrl || defaultMeta.canonicalUrl;
  const keywords = props.keywords || defaultMeta.keywords;
  const noindex = props.noindex !== undefined ? props.noindex : defaultMeta.noindex;
  const ogType = props.ogType || defaultMeta.ogType;
  const ogImage = props.ogImage || defaultMeta.ogImage;
  const structuredData = props.structuredData || defaultMeta.structuredData;

  useEffect(() => {
    // 1. Title
    document.title = title;

    // Helper function to update or create a meta tag
    const setMetaTag = (attrName: 'name' | 'property', attrValue: string, content: string) => {
      let element = document.querySelector(`meta[${attrName}="${attrValue}"]`);
      if (!element) {
        element = document.createElement('meta');
        element.setAttribute(attrName, attrValue);
        document.head.appendChild(element);
      }
      element.setAttribute('content', content);
    };

    // Helper function to update canonical link
    const setCanonicalLink = (url: string) => {
      let element = document.querySelector('link[rel="canonical"]');
      if (!element) {
        element = document.createElement('link');
        element.setAttribute('rel', 'canonical');
        document.head.appendChild(element);
      }
      element.setAttribute('href', url);
    };

    // 2. Primary Meta Tags
    setMetaTag('name', 'description', description);
    if (keywords && keywords.length > 0) {
      setMetaTag('name', 'keywords', keywords.join(', '));
    }

    // 3. Robots meta
    setMetaTag('name', 'robots', noindex ? 'noindex, nofollow' : 'index, follow');

    // 4. Canonical URL
    setCanonicalLink(canonicalUrl);

    // 5. OpenGraph Meta Tags
    setMetaTag('property', 'og:title', title);
    setMetaTag('property', 'og:description', description);
    setMetaTag('property', 'og:url', canonicalUrl);
    setMetaTag('property', 'og:type', ogType);
    setMetaTag('property', 'og:site_name', SITE_CONFIG.brandName);
    setMetaTag('property', 'og:image', ogImage);

    // 6. Twitter Card Meta Tags
    setMetaTag('name', 'twitter:card', 'summary_large_image');
    setMetaTag('name', 'twitter:title', title);
    setMetaTag('name', 'twitter:description', description);
    setMetaTag('name', 'twitter:image', ogImage);
    if (SITE_CONFIG.twitterHandle) {
      setMetaTag('name', 'twitter:site', SITE_CONFIG.twitterHandle);
    }

    // 7. Structured Data (JSON-LD)
    const existingScripts = document.querySelectorAll('script[data-velto-seo="true"]');
    existingScripts.forEach((s) => s.remove());

    if (structuredData && structuredData.length > 0) {
      structuredData.forEach((schemaObj, index) => {
        const script = document.createElement('script');
        script.type = 'application/ld+json';
        script.setAttribute('data-velto-seo', 'true');
        script.setAttribute('data-schema-id', String(index));
        script.textContent = JSON.stringify(schemaObj);
        document.head.appendChild(script);
      });
    }
  }, [title, description, canonicalUrl, keywords, noindex, ogType, ogImage, structuredData, location.pathname]);

  return null;
}
