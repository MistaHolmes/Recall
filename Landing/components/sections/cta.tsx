"use client"

import { motion, useInView } from "motion/react"
import { useRef } from "react"
import { ArrowRight } from "lucide-react"

export function CTA() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} id="cta" aria-labelledby="cta-heading" className="bg-background py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="relative overflow-hidden rounded-2xl border border-border bg-secondary px-8 py-14 text-center md:px-16"
        >
          {/* Subtle decorative dots */}
          <div className="pointer-events-none absolute inset-0 opacity-[0.03]" style={{
            backgroundImage: "radial-gradient(circle, hsl(var(--foreground)) 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }} />

          <h2 id="cta-heading" className="relative font-display text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            Ready to Supercharge Your Study Group?
          </h2>
          <p className="relative mx-auto mt-4 max-w-md text-base leading-relaxed text-muted-foreground">
            Invite Recall to your server today and transform the way you learn collaboratively.
          </p>
          <div className="relative mt-8 flex flex-wrap items-center justify-center gap-4">
            <a
              href="https://discord.com/invite/wSETGkV9HY"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-full bg-foreground px-7 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Invite to Discord
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
