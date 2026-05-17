"use client"

import { motion, useInView } from "motion/react"
import { useRef } from "react"
import Image from "next/image"

const platforms = [
  {
    title: "Scribblit for Android",
    description:
      "Take notes on the go with fast, secure sync across all your devices. Capture thoughts instantly and access them anytime.",
    image: "/images/platform-android.jpg?v=3",
  },
  {
    title: "Scribblit for iOS",
    description:
      "Jot down notes, organize with folders, and collaborate on shared projects — all from your iPhone or iPad.",
    image: "/images/platform-ios.jpg?v=3",
  },
  {
    title: "Scribblit for Windows / Linux",
    description:
      "Work smarter on desktop. Enjoy seamless syncing, keyboard shortcuts, and distraction-free writing.",
    image: "/images/platform-desktop.jpg?v=3",
  },
  {
    title: "Scribblit for Web",
    description:
      "Access your notes anywhere with a responsive web app that loads in under 3 seconds.",
    image: "/images/platform-web.jpg?v=3",
  },
]

export function Platforms() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} id="platforms" className="bg-background py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-6">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="mb-14"
        >
          <h2 className="max-w-md font-display text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            <span className="text-balance">
              Ideas. Notes. Clarity.
              <br />
              Wherever your mind goes.
            </span>
          </h2>
        </motion.div>

        {/* Platform Cards Grid */}
        <div className="grid gap-6 sm:grid-cols-2">
          {platforms.map((platform, i) => (
            <motion.div
              key={platform.title}
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.15 * i }}
              className="group overflow-hidden rounded-2xl border border-border bg-card transition-shadow hover:shadow-lg"
            >
              <div className="relative aspect-[16/10] overflow-hidden bg-secondary">
                <Image
                  src={platform.image}
                  alt={platform.title}
                  fill
                  unoptimized
                  className="object-cover transition-transform duration-500 group-hover:scale-105"
                />
              </div>
              <div className="px-6 py-5">
                <h3 className="font-display text-lg font-semibold text-foreground">
                  {platform.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {platform.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
