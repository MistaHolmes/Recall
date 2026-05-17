"use client"

import { useState } from "react"
import { motion } from "motion/react"
import { FloatingPaths } from "@/components/ui/floating-paths"
import Image from "next/image"
import { Users } from "lucide-react"

export function Hero() {

  const subtitleText =
    "Upload PDFs, auto-generate quizzes, transcribe voice chats, and schedule group sessions — your ultimate AI study companion."

  return (
    <section className="relative overflow-hidden px-4 pt-24 pb-0 md:px-6 lg:px-8 bg-background">
      {/* Animated Background Paths in the empty section */}
      <div className="absolute inset-0 z-0 pointer-events-none -top-32 h-[120%]">
        <FloatingPaths position={1} />
        <FloatingPaths position={-1} />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl overflow-hidden rounded-3xl bg-foreground shadow-2xl">
        {/* Mountain Image - positioned at bottom */}
        <div className="pointer-events-none absolute inset-0">
          <Image
            src="/images/hero-mountains.jpg?v=2"
            alt=""
            fill
            className="object-cover object-bottom opacity-100"
            priority
            unoptimized
          />
          <div className="absolute inset-0 bg-foreground/30" />
        </div>

        {/* Content */}
        <div className="relative z-10 flex flex-col items-center px-6 pt-16 pb-40 text-center md:pt-20 md:pb-52 lg:pt-24 lg:pb-64">
          {/* Social Proof Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary-foreground/30 bg-primary-foreground/10 px-4 py-1.5 backdrop-blur-sm shadow-sm"
          >
            <Users className="h-3.5 w-3.5 text-primary-foreground" />
            <span className="text-xs font-semibold text-primary-foreground">
              Supercharging Study Groups
            </span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.3 }}
            className="mx-auto max-w-3xl font-display text-4xl font-bold leading-[1.1] tracking-tight text-primary-foreground md:text-6xl lg:text-7xl"
          >
            <span className="text-balance">
              Learn Better. Together.
              <br />
              Right inside Discord.
            </span>
          </motion.h1>

          {/* Highlighted Subheadline */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="mx-auto mt-6 max-w-xl text-center"
          >
            <span
              className="leading-loose text-primary-foreground/80 transition-all duration-300 [box-decoration-break:clone] bg-primary-foreground/15 px-1.5 py-0.5 rounded-sm font-sans text-base md:text-lg"
            >
              {subtitleText}
            </span>
          </motion.div>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.9 }}
            className="mt-8 flex flex-wrap items-center justify-center gap-4"
          >
            <a
              href="https://discord.com/invite/wSETGkV9HY"
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-full bg-primary-foreground px-7 py-3 text-sm font-medium text-foreground transition-opacity hover:opacity-90"
            >
              Add to Discord
            </a>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
