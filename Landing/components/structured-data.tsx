const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://scribblit.app'

export function StructuredData() {
  const organizationSchema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'Scribblit',
    url: siteUrl,
    logo: `${siteUrl}/og-image.png`,
    description:
      'Combine note-taking, idea tracking, and daily planning in one smart notebook.',
    sameAs: [
      'https://twitter.com/scribblit',
      'https://linkedin.com/company/scribblit',
    ],
    foundingDate: '2024',
    contactPoint: {
      '@type': 'ContactPoint',
      contactType: 'customer support',
      url: `${siteUrl}/#contact`,
    },
  }

  const softwareSchema = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'Scribblit',
    applicationCategory: 'ProductivityApplication',
    operatingSystem: 'Android, iOS, Windows, Linux, Web',
    description:
      'Combine note-taking, idea tracking, and daily planning in one smart notebook — ready whenever inspiration hits.',
    url: siteUrl,
    offers: [
      {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'USD',
        name: 'Free',
        description: 'Create up to 50 notes, basic search & tagging, single device access.',
      },
      {
        '@type': 'Offer',
        price: '69.00',
        priceCurrency: 'USD',
        name: 'Pro',
        description:
          'Unlimited notes & notebooks, advanced search & tagging, real-time collaboration, cloud sync.',
      },
      {
        '@type': 'Offer',
        price: '149.00',
        priceCurrency: 'USD',
        name: 'Vision Pro',
        description:
          'Everything in Pro, team dashboards & shared workspaces, admin & permissions, priority support.',
      },
    ],
    aggregateRating: {
      '@type': 'AggregateRating',
      ratingValue: '4.8',
      ratingCount: '100000',
      bestRating: '5',
      worstRating: '1',
    },
    featureList: [
      'Smart Note Capture',
      'Adaptive Organization',
      'AI-Powered Summaries',
      'Real-Time Collaboration',
      'Cloud Sync Across Devices',
      'Cross-Platform Support',
    ],
  }

  const websiteSchema = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'Scribblit',
    url: siteUrl,
    description:
      'Capture thoughts instantly, organize with AI, and sync across all your devices.',
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: `${siteUrl}/search?q={search_term_string}`,
      },
      'query-input': 'required name=search_term_string',
    },
  }

  const faqSchema = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: [
      {
        '@type': 'Question',
        name: 'What platforms does Scribblit support?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Scribblit is available on Android, iOS, Windows, Linux, and the web. Your notes sync seamlessly across all platforms.',
        },
      },
      {
        '@type': 'Question',
        name: 'Is Scribblit free to use?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Yes, Scribblit offers a free plan with up to 50 notes, basic search & tagging, and single device access. Upgrade to Pro ($69) or Vision Pro ($149) for unlimited notes, collaboration, and more.',
        },
      },
      {
        '@type': 'Question',
        name: 'Does Scribblit support real-time collaboration?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Yes, with Scribblit Pro and Vision Pro plans, you can collaborate in real-time with your team, share workspaces, and manage permissions.',
        },
      },
    ],
  }

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />
    </>
  )
}
