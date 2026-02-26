const SITE_URL = 'https://elcereal.com';

export function siteUrl(path: string): string {
  return `${SITE_URL}${path}`;
}

export interface SEOProps {
  title: string;
  description: string;
  canonical?: string;
  type?: 'website' | 'article';
  image?: string;
  noindex?: boolean;
}

export interface BreadcrumbItem {
  name: string;
  url: string;
}

export function generateBreadcrumbSchema(items: BreadcrumbItem[]): string {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: siteUrl(item.url),
    })),
  };
  return JSON.stringify(schema);
}

export function generateOrganizationSchema(): string {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'Precios Cereales',
    url: siteUrl('/'),
    description: 'Portal de referencia con precios actualizados de cereales en todas las lonjas de España.',
    sameAs: [],
  };
  return JSON.stringify(schema);
}

export function generateWebSiteSchema(): string {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'Precios Cereales',
    url: siteUrl('/'),
    description: 'Precios actualizados de cereales en todas las lonjas de España. Trigo, cebada, maíz, avena, girasol, colza y más.',
    publisher: {
      '@type': 'Organization',
      name: 'Precios Cereales',
    },
  };
  return JSON.stringify(schema);
}

export function generateProductSchema(cereal: { nombre: string; slug: string }, precioMedio: { media: number; min: number; max: number; count: number }, fechaFin: string): string {
  const nextWeek = new Date(fechaFin);
  nextWeek.setDate(nextWeek.getDate() + 7);

  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: cereal.nombre,
    category: 'Cereales',
    description: `Precio del ${cereal.nombre.toLowerCase()} en las lonjas de España. Cotización actualizada.`,
    url: siteUrl(`/precios/${cereal.slug}/`),
    offers: {
      '@type': 'AggregateOffer',
      priceCurrency: 'EUR',
      lowPrice: precioMedio.min.toFixed(2),
      highPrice: precioMedio.max.toFixed(2),
      offerCount: precioMedio.count,
      priceValidUntil: nextWeek.toISOString().split('T')[0],
      unitText: 'tonelada',
    },
  };
  return JSON.stringify(schema);
}

export function generateFAQSchema(faqs: { question: string; answer: string }[]): string {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map(faq => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer,
      },
    })),
  };
  return JSON.stringify(schema);
}

export function generateLocalBusinessSchema(lonja: { nombre: string; slug: string; ciudad: string; direccion: string; telefono: string; web: string }): string {
  const schema: Record<string, unknown> = {
    '@context': 'https://schema.org',
    '@type': 'LocalBusiness',
    name: lonja.nombre,
    description: `${lonja.nombre} - Cotizaciones y precios de cereales en ${lonja.ciudad}.`,
    address: {
      '@type': 'PostalAddress',
      addressLocality: lonja.ciudad,
      addressCountry: 'ES',
      streetAddress: lonja.direccion,
    },
    url: siteUrl(`/lonjas/${lonja.slug}/`),
  };

  if (lonja.telefono) schema.telephone = lonja.telefono;
  if (lonja.web) schema.sameAs = [lonja.web];

  return JSON.stringify(schema);
}
