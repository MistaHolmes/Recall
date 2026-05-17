"use client"

import { motion, useInView } from "motion/react"
import { useRef, useState, useEffect } from "react"
import {
  MessageSquare,
  Hash,
  ChevronRight,
  Bot,
  User,
} from "lucide-react"

// Custom Typewriter Effect
function TypewriterText({ text, delay = 0, onComplete }: { text: string, delay?: number, onComplete?: () => void }) {
  const [displayed, setDisplayed] = useState("")
  const onCompleteRef = useRef(onComplete)
  useEffect(() => { onCompleteRef.current = onComplete }, [onComplete])

  useEffect(() => {
    let i = 0
    let t: NodeJS.Timeout
    const start = setTimeout(() => {
      t = setInterval(() => {
        setDisplayed(text.substring(0, i + 1))
        i++
        if (i === text.length) {
          clearInterval(t)
          if (onCompleteRef.current) onCompleteRef.current()
        }
      }, 15) // Faster typing for SSE
    }, delay * 1000)
    return () => { clearTimeout(start); clearInterval(t) }
  }, [text, delay])

  return <span>{displayed}</span>
}

export function NotesPreview() {
  const ref = useRef(null)
  const [step, setStep] = useState(0)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} id="features" aria-labelledby="features-heading" className="bg-background pt-20 md:pt-28 pb-10 md:pb-16">
      <div className="mx-auto max-w-6xl px-6">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="mb-12"
        >
          <h2 id="features-heading" className="font-display text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            <span className="text-balance">AI-Powered Study Sessions.</span>
          </h2>
          <p className="mt-4 max-w-lg text-base leading-relaxed text-muted-foreground">
            Turn your Discord server into a dedicated learning environment with automatic quizzes, voice transcripts, and instant AI-generated session summaries.
          </p>
        </motion.div>

        {/* Discord Mock */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="overflow-hidden rounded-2xl border border-border bg-[#313338] shadow-lg font-sans"
        >
          {/* Discord Header */}
          <div className="flex items-center gap-2 border-b border-[#1E1F22] bg-[#313338] px-4 py-3 shadow-sm">
            <Hash className="h-5 w-5 text-muted-foreground" />
            <span className="font-semibold text-white text-md">study-group</span>
          </div>

          {/* Chat Content */}
          <div className="flex flex-col gap-6 px-4 py-6 md:px-6 md:py-8 h-[550px] overflow-y-auto">
            {/* User Message */}
            <div className="flex gap-4">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-blue-500">
                <User className="h-6 w-6 text-white" />
              </div>
              <div className="flex flex-col">
                <div className="flex items-baseline gap-2">
                  <span className="font-medium text-white hover:underline cursor-pointer">Student</span>
                  <span className="text-xs text-zinc-400">Today at 10:45 AM</span>
                </div>
                <p className="text-zinc-200 mt-1 min-h-[24px]">
                  {isInView && <TypewriterText text="/study end" delay={0.5} onComplete={() => setStep(1)} />}
                </p>
              </div>
            </div>

            {/* Bot Message */}
            {step >= 1 && (
            <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} className="flex gap-4">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-green-600">
                <Bot className="h-6 w-6 text-white" />
              </div>
              <div className="flex flex-col w-full max-w-2xl">
                <div className="flex items-baseline gap-2">
                  <span className="font-medium text-white hover:underline cursor-pointer">Recall</span>
                  <span className="rounded bg-[#5865F2] px-1 py-0.5 text-[10px] font-semibold text-white uppercase ml-1">Bot</span>
                  <span className="text-xs text-zinc-400">Today at 10:45 AM</span>
                </div>

                {/* Embed */}
                <div className="mt-2 rounded-lg border-l-4 border-l-green-500 bg-[#2B2D31] p-4 overflow-hidden">
                  <h3 className="font-bold text-white mb-2 min-h-[28px]">
                     <TypewriterText text="📚 Session Ended: Kubernetes Networking" delay={0.5} onComplete={() => setStep(2)} />
                  </h3>

                  {step >= 2 && (
                  <div className="space-y-4">
                    <div>
                      <p className="font-semibold text-zinc-300 text-sm min-h-[20px]">
                        <TypewriterText text="## Key Takeaways" delay={0} onComplete={() => setStep(3)} />
                      </p>
                      {step >= 3 && (
                      <ul className="list-inside list-disc text-sm text-zinc-300 mt-1 space-y-1">
                        <motion.li initial={{opacity:0}} animate={{opacity:1}} transition={{delay:0.3}} onAnimationComplete={() => setStep(4)}>Connection-density operators scale based on active connections per pod.</motion.li>
                        {step >= 4 && <motion.li initial={{opacity:0}} animate={{opacity:1}} transition={{delay:0.3}} onAnimationComplete={() => setStep(5)}>StatefulAutoscaler is highly effective but lacks a definitive success conclusion in the uploaded paper.</motion.li>}
                      </ul>
                      )}
                    </div>
                    {step >= 5 && (
                    <div>
                      <p className="font-semibold text-zinc-300 text-sm min-h-[20px]">
                        <TypewriterText text="## Quiz Performance" delay={0.5} onComplete={() => setStep(6)} />
                      </p>
                      {step >= 6 && (
                      <ul className="list-inside list-disc text-sm text-zinc-300 mt-1 space-y-1">
                        <motion.li initial={{opacity:0}} animate={{opacity:1}} transition={{delay:0.3}} onAnimationComplete={() => setStep(7)}>Student: 3/3 correct (100%)</motion.li>
                        {step >= 7 && <motion.li initial={{opacity:0}} animate={{opacity:1}} transition={{delay:0.3}} onAnimationComplete={() => setStep(8)}>Jane: 2/3 correct (66%)</motion.li>}
                      </ul>
                      )}
                    </div>
                    )}
                  </div>
                  )}
                </div>
              </div>
            </motion.div>
            )}

            {/* Jane Message */}
            {step >= 8 && (
            <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{delay: 1.5}} className="flex gap-4 mt-2" onAnimationComplete={() => setStep(9)}>
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-pink-500">
                <User className="h-6 w-6 text-white" />
              </div>
              <div className="flex flex-col">
                <div className="flex items-baseline gap-2">
                  <span className="font-medium text-white hover:underline cursor-pointer">Jane</span>
                  <span className="text-xs text-zinc-400">Today at 10:46 AM</span>
                </div>
                <p className="text-zinc-200 mt-1 min-h-[24px]">
                  {step >= 9 && <TypewriterText text="Perfect. Update the session memory." delay={0} onComplete={() => setStep(10)} />}
                </p>
              </div>
            </motion.div>
            )}

            {/* Bot Message */}
            {step >= 10 && (
            <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{delay: 1}} className="flex gap-4 mt-2" onAnimationComplete={() => setStep(11)}>
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-green-600">
                <Bot className="h-6 w-6 text-white" />
              </div>
              <div className="flex flex-col">
                <div className="flex items-baseline gap-2">
                  <span className="font-medium text-white hover:underline cursor-pointer">Recall</span>
                  <span className="rounded bg-[#5865F2] px-1 py-0.5 text-[10px] font-semibold text-white uppercase ml-1">Bot</span>
                  <span className="text-xs text-zinc-400">Today at 10:46 AM</span>
                </div>
                <p className="text-zinc-200 mt-1 min-h-[24px]">
                  {step >= 11 && <TypewriterText text="✅ Synced! The session summary has been been added to the memory !!!" delay={0} />}
                </p>
              </div>
            </motion.div>
            )}

          </div>
          {/* Discord Input Area */}
          <div className="bg-[#313338] px-4 pb-4">
            <div className="flex items-center gap-3 rounded-lg bg-[#383A40] px-4 py-2.5">
              <span className="text-zinc-400 text-sm flex-1">Message #study-group</span>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
