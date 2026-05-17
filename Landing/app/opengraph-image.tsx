import { ImageResponse } from 'next/og'

export const runtime = 'edge'
export const alt = 'Scribblit — Smart notebook for ideas, notes, and daily planning'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#09090b',
          fontFamily: 'sans-serif',
          position: 'relative',
        }}
      >
        {/* Subtle grid pattern */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundImage:
              'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.06) 1px, transparent 0)',
            backgroundSize: '40px 40px',
          }}
        />

        {/* Content */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10,
          }}
        >
          {/* Logo */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: '40px',
            }}
          >
            <svg
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
              <path d="M14 2v4a2 2 0 0 0 2 2h4" />
              <path d="M10 9H8" />
              <path d="M16 13H8" />
              <path d="M16 17H8" />
            </svg>
            <span
              style={{
                fontSize: 36,
                fontWeight: 700,
                color: 'white',
                letterSpacing: '-0.02em',
              }}
            >
              Scribblit
            </span>
          </div>

          {/* Headline */}
          <div
            style={{
              fontSize: 64,
              fontWeight: 800,
              color: 'white',
              textAlign: 'center',
              lineHeight: 1.1,
              letterSpacing: '-0.03em',
              maxWidth: '800px',
            }}
          >
            Ideas. Notes. Clarity.
          </div>
          <div
            style={{
              fontSize: 48,
              fontWeight: 800,
              color: 'rgba(255,255,255,0.5)',
              textAlign: 'center',
              lineHeight: 1.2,
              letterSpacing: '-0.02em',
              marginTop: '8px',
            }}
          >
            Wherever your mind goes.
          </div>

          {/* Tagline */}
          <div
            style={{
              fontSize: 20,
              color: 'rgba(255,255,255,0.4)',
              marginTop: '28px',
              textAlign: 'center',
              maxWidth: '560px',
              lineHeight: 1.5,
            }}
          >
            Smart notebook for note-taking, idea tracking, and daily planning.
          </div>
        </div>

        {/* Bottom bar */}
        <div
          style={{
            position: 'absolute',
            bottom: 30,
            display: 'flex',
            alignItems: 'center',
            gap: '24px',
            color: 'rgba(255,255,255,0.25)',
            fontSize: 16,
          }}
        >
          <span>scribblit.app</span>
          <span>{'|'}</span>
          <span>Android</span>
          <span>{'|'}</span>
          <span>iOS</span>
          <span>{'|'}</span>
          <span>Web</span>
          <span>{'|'}</span>
          <span>Desktop</span>
        </div>
      </div>
    ),
    { ...size }
  )
}
