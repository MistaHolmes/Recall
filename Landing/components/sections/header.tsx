"use client"

import { motion } from "motion/react"

import Link from "next/link"

export function Header() {
  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="fixed top-4 left-4 right-4 z-50 mx-auto max-w-6xl rounded-2xl bg-background/80 backdrop-blur-md border border-border shadow-lg"
    >
      <div className="flex items-center justify-between px-6 py-3">
        <Link href="/" className="flex items-center gap-2">
          <img src="https://r2.abhashbehera.online/R2-uploader/uploads/1779010671379_Logo-Transparent.png" alt="Recall Logo" className="h-8 w-8 object-contain" />
          <span className="font-display text-xl font-bold text-foreground">
            Recall
          </span>
        </Link>
        <div className="flex items-center gap-3">
          <Link
            href="https://discord.com/invite/wSETGkV9HY"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full bg-foreground px-5 py-2 text-sm font-medium text-background transition-opacity hover:opacity-90"
          >
            Invite to Server
          </Link>
        </div>
      </div>
    </motion.header>
  )
}
