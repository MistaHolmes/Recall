import type { Metadata, Viewport } from 'next'
import { Inter, Space_Grotesk } from 'next/font/google'

import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-space-grotesk',
  display: 'swap',
})

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://recallbot.app'

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: 'Recall - AI-Powered Study Sessions & Collaboration.',
    template: '%s | Recall',
  },
  description:
    'Turn your Discord server into a dedicated learning environment with automatic quizzes, voice transcripts, and instant AI-generated session summaries.',
  keywords: [
    'discord bot',
    'study bot',
    'AI study',
    'recall bot',
    'learning environment',
    'AI quizzes',
    'voice transcripts',
    'session summaries',
    'productivity tool',
    'Recall',
  ],
  authors: [{ name: 'Recall', url: siteUrl }],
  creator: 'Recall',
  publisher: 'Recall',
  applicationName: 'Recall',
  category: 'Productivity',
  classification: 'Education & Productivity',
  referrer: 'origin-when-cross-origin',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: siteUrl,
    siteName: 'Recall',
    title: 'Recall — AI-Powered Study Sessions & Collaboration.',
    description:
      'Turn your Discord server into a dedicated learning environment with automatic quizzes, voice transcripts, and instant AI-generated session summaries.',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'Recall — AI-Powered Study Sessions',
        type: 'image/png',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Recall — AI-Powered Study Sessions & Collaboration.',
    description:
      'Turn your Discord server into a dedicated learning environment with automatic quizzes, voice transcripts, and instant AI-generated session summaries.',
    images: ['/og-image.png'],
    creator: '@scribblit',
    site: '@scribblit',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  alternates: {
    canonical: siteUrl,
  },
  icons: {
    icon: '/Recall-logo.png',
    shortcut: '/Recall-logo.png',
    apple: '/Recall-logo.png',
  },
  manifest: '/site.webmanifest',
}

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#09090b' },
  ],
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  colorScheme: 'light dark',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" dir="ltr">
      <head>
        <link rel="dns-prefetch" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body
        className={`${inter.variable} ${spaceGrotesk.variable} font-sans antialiased`}
      >
        {children}
      </body>
    </html>
  )
}
