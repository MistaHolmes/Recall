"use client"

import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence, useInView } from "motion/react"
import { FileText, Timer, Mic, Calendar, Hash, User, Bot, CheckCircle2, Clock, Terminal, ClipboardList } from "lucide-react"

// Custom Typewriter Effect
function TypewriterText({ text, delay = 0, onComplete }: { text: string, delay?: number, onComplete?: () => void }) {
  const [displayed, setDisplayed] = useState("")
  const onCompleteRef = useRef(onComplete)

  useEffect(() => {
    onCompleteRef.current = onComplete
  }, [onComplete])

  useEffect(() => {
    let i = 0;
    const t = setTimeout(() => {
      const interval = setInterval(() => {
        setDisplayed(text.substring(0, i + 1))
        i++
        if (i === text.length) {
          clearInterval(interval)
          if (onCompleteRef.current) onCompleteRef.current()
        }
      }, 30)
      return () => clearInterval(interval)
    }, delay * 1000)

    return () => clearTimeout(t)
  }, [text, delay])

  return <span>{displayed}<motion.span animate={{opacity: [1,0]}} transition={{repeat: Infinity, duration: 0.8}}>|</motion.span></span>
}

function RagMock({ setStepState }: { setStepState: (n: number) => void }) {
  const [step, setStep] = useState(0);
  useEffect(() => { setStepState(step); }, [step, setStepState]);
  
  useEffect(() => {
    if (step === 1) {
      const timer = setTimeout(() => setStep(2), 1500);
      return () => clearTimeout(timer);
    }
    if (step === 2) {
      const timer = setTimeout(() => setStep(3), 1500);
      return () => clearTimeout(timer);
    }
  }, [step]);
  
  return (
    <div className="flex flex-col gap-5 p-5 pb-16 text-sm font-sans">
       <div className="flex gap-3">
         <div className="h-8 w-8 rounded-full bg-blue-500 flex-shrink-0 flex items-center justify-center"><User className="h-5 w-5 text-white"/></div>
         <div>
           <div className="flex items-center gap-2"><span className="font-medium text-white hover:underline cursor-pointer">Student</span></div>
           <p className="text-zinc-300 mt-0.5">
             <TypewriterText text="/upload distributed_systems_notes.pdf" delay={0.5} onComplete={() => setStep(1)} />
           </p>
         </div>
       </div>

       {step >= 3 && (
         <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{delay: 0.5}} className="flex gap-3" onAnimationComplete={() => setStep(4)}>
            <div className="h-8 w-8 rounded-full bg-green-600 flex-shrink-0 flex items-center justify-center"><Bot className="h-5 w-5 text-white"/></div>
            <div className="w-full">
              <div className="flex items-center gap-2">
                <span className="font-medium text-white hover:underline cursor-pointer">Recall</span>
                <span className="rounded bg-[#5865F2] px-1 py-0.5 text-[10px] font-semibold text-white uppercase">Bot</span>
              </div>
              <p className="text-zinc-300 mt-0.5 text-sm flex items-center gap-1.5"><CheckCircle2 className="h-4 w-4 text-green-500" /> Uploaded distributed_systems_notes.pdf</p>
              <p className="text-zinc-400 text-xs mt-1">127 chunks indexed and ready for semantic search.</p>
            </div>
         </motion.div>
       )}

       {step >= 4 && (
          <motion.div initial={{opacity: 0}} animate={{opacity: 1}} transition={{delay: 0.5}} className="flex items-center justify-center my-2" onAnimationComplete={() => setStep(5)}>
             <div className="h-[1px] flex-1 bg-white/10" />
          </motion.div>
       )}

       {step >= 5 && (
         <motion.div initial={{opacity: 0}} animate={{opacity: 1}} transition={{delay: 0.5}} className="flex gap-3">
            <div className="h-8 w-8 rounded-full bg-blue-500 flex-shrink-0 flex items-center justify-center"><User className="h-5 w-5 text-white"/></div>
            <div>
              <div className="flex items-center gap-2"><span className="font-medium text-white hover:underline cursor-pointer">Student</span></div>
              <p className="text-zinc-300 mt-0.5">
                <TypewriterText text="/ask How does Raft leader election prevent split brain?" delay={0.2} onComplete={() => setStep(6)} />
              </p>
            </div>
         </motion.div>
       )}

       {step >= 6 && (
         <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{delay: 0.5}} className="flex gap-3">
            <div className="h-8 w-8 rounded-full bg-green-600 flex-shrink-0 flex items-center justify-center"><Bot className="h-5 w-5 text-white"/></div>
            <div className="w-full">
              <div className="flex items-center gap-2">
                <span className="font-medium text-white hover:underline cursor-pointer">Recall</span>
                <span className="rounded bg-[#5865F2] px-1 py-0.5 text-[10px] font-semibold text-white uppercase">Bot</span>
              </div>
              <div className="mt-2 rounded-lg border-l-4 border-l-blue-500 bg-[#2B2D31] p-4 shadow-md">
                <p className="text-zinc-300 text-sm leading-relaxed">Raft prevents split-brain scenarios by enforcing quorum-based leader election. A candidate node must receive votes from a majority of nodes before becoming leader.</p>
                <div className="mt-3 space-y-1">
                  <p className="text-xs text-zinc-400 font-medium uppercase tracking-wider">Sources:</p>
                  <div className="flex items-center gap-1.5 text-xs text-blue-400 bg-blue-500/10 rounded px-2 py-1 w-fit border border-blue-500/20">
                    <FileText className="h-3 w-3"/> distributed_systems_notes.pdf — p.14
                  </div>
                </div>
              </div>
            </div>
         </motion.div>
       )}
    </div>
  )
}

function RagTerminal({ step }: { step: number }) {
  return (
    <div className="font-mono text-xs space-y-1.5 text-zinc-300">
       {step >= 0 && <div className="text-zinc-500">[System]: Ready for commands...</div>}
       {step >= 1 && <div className="text-[#A6E22E] font-semibold">{">"} Processing file upload: distributed_systems_notes.pdf...</div>}
       {step >= 2 && <div>
          [PDFLoader]: Extracting text from 42 pages...<br/>
          [TextSplitter]: Splitting by RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)<br/>
          [OpenAI]: Generating embeddings (model=text-embedding-3-small, dim=1536)<br/>
          [ChromaDB]: Indexed 127 chunks. Ready for vector search.
       </div>}
       {step >= 5 && <div className="text-[#A6E22E] font-semibold mt-4">{">"} Query received: "How does Raft leader election prevent split brain?"</div>}
       {step >= 6 && <div className="mb-2">
          [ChromaDB]: Performing cosine similarity search (top_k=4)...<br/>
          [Retrieval]: Found matching contexts (score: 0.89, 0.84, 0.76)<br/>
          [Langchain]: Assembling RAG prompt template<br/>
          [Groq]: Synthesizing answer using Llama-3-8B...<br/>
          [System]: Response dispatched (latency: 412ms).
       </div>}
       {step >= 7 && <div className="text-[#A6E22E] font-semibold mt-4">{">"} Query received: "What about the timeout phase?"</div>}
       {step >= 8 && <div>
          [ChromaDB]: Performing cosine similarity search (top_k=4)...<br/>
          [Retrieval]: Found matching contexts (score: 0.91, 0.82)<br/>
          [Langchain]: Assembling RAG prompt template<br/>
          [Groq]: Synthesizing answer using Llama-3-8B...<br/>
          [System]: Response dispatched (latency: 350ms).
       </div>}
    </div>
  )
}

function QuizMock({ setStepState }: { setStepState: (n: any) => void }) {
  const [step, setStep] = useState(0);
  const [selections, setSelections] = useState<string[]>([]);
  const [currentSelection, setCurrentSelection] = useState<string | null>(null);

  useEffect(() => { setStepState({ step, selections }); }, [step, selections, setStepState]);

  const handleSelect = (opt: string) => {
    if (currentSelection === opt) {
      setCurrentSelection(null);
      setSelections(prev => [...prev, `Deselected ${opt}`]);
    } else {
      setCurrentSelection(opt);
      setSelections(prev => [...prev, opt]);
    }
    setStep(prev => (prev < 3 ? 3 : prev));
  };

  const getBtnClass = (opt: string) => {
    const base = "text-left px-3 py-2.5 rounded text-sm border transition-colors relative overflow-hidden ";
    if (!currentSelection) return base + "bg-[#383A40] text-zinc-300 border-transparent hover:bg-[#404249]";
    if (opt === "B") return base + "bg-[#23A559]/20 border-[#23A559] text-white";
    if (currentSelection === opt) return base + "bg-red-500/20 border-red-500 text-white";
    return base + "bg-[#383A40] text-zinc-500 border-transparent opacity-50";
  };

  return (
    <div className="flex flex-col gap-5 p-5 pb-16 text-sm font-sans">
       <motion.div initial={{opacity: 0}} animate={{opacity: 1}} transition={{delay: 0.5}} className="flex gap-3" onAnimationComplete={() => setStep(1)}>
          <div className="h-8 w-8 rounded-full bg-green-600 flex-shrink-0 flex items-center justify-center"><Bot className="h-5 w-5 text-white"/></div>
          <div className="w-full">
            <div className="flex items-center gap-2">
              <span className="font-medium text-white hover:underline cursor-pointer">Recall</span>
              <span className="rounded bg-[#5865F2] px-1 py-0.5 text-[10px] font-semibold text-white uppercase">Bot</span>
            </div>
            <p className="text-zinc-300 mt-1">🍅 Pomodoro #3 complete.</p>
            <p className="text-zinc-400 mt-0.5 text-xs">Time for a quick knowledge check.</p>
          </div>
       </motion.div>

       {step >= 1 && (
         <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{delay: 1}} className="flex gap-3" onAnimationComplete={() => setStep(2)}>
            <div className="h-8 w-8 rounded-full bg-green-600 flex-shrink-0 flex items-center justify-center"><Bot className="h-5 w-5 text-white"/></div>
            <div className="w-full">
              <div className="flex items-center gap-2">
                <span className="font-medium text-white hover:underline cursor-pointer">Recall</span>
                <span className="rounded bg-[#5865F2] px-1 py-0.5 text-[10px] font-semibold text-white uppercase">Bot</span>
              </div>
              <div className="mt-1 rounded-lg border border-[#1E1F22] bg-[#2B2D31] p-4 shadow-md">
                <h4 className="font-semibold text-white mb-2 flex items-center gap-2">Quiz: Kubernetes Networking</h4>
                <p className="text-zinc-300 text-sm">Which component is responsible for maintaining network rules across cluster nodes?</p>
                
                <div className="flex flex-col gap-2 mt-4">
                  <button onClick={() => handleSelect("A")} className={getBtnClass("A")}>
                    🇦 kubelet
                  </button>
                  <button onClick={() => handleSelect("B")} className={getBtnClass("B")}>
                    🇧 kube-proxy
                    {currentSelection && <span className="absolute right-2 top-2.5 text-[10px] font-medium bg-[#23A559] text-white px-2 py-0.5 rounded-full">Correct</span>}
                  </button>
                  <button onClick={() => handleSelect("C")} className={getBtnClass("C")}>
                    🇨 etcd
                  </button>
                  <button onClick={() => handleSelect("D")} className={getBtnClass("D")}>
                    🇩 CoreDNS
                  </button>
                </div>
              </div>
            </div>
         </motion.div>
       )}

       {step >= 3 && currentSelection && (
         <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{delay: 0.5}} className="flex gap-3">
            <div className="h-8 w-8 rounded-full bg-green-600 flex-shrink-0 flex items-center justify-center"><Bot className="h-5 w-5 text-white"/></div>
            <div>
              <div className="flex items-center gap-2"><span className="font-medium text-white hover:underline cursor-pointer">Recall</span></div>
              <p className="text-zinc-300 mt-1 flex items-center gap-1.5">
                {currentSelection === "B" ? <CheckCircle2 className="h-4 w-4 text-green-500"/> : <span className="text-red-500 font-bold px-1">X</span>} 
                {currentSelection === "B" ? "Correct Answer: 🇧 kube-proxy" : "Incorrect. The correct answer was 🇧 kube-proxy."}
              </p>
              <p className="text-zinc-400 text-xs mt-1">
                {currentSelection === "B" ? "82% answered correctly. +10 points awarded." : "82% answered correctly. No points awarded."}
              </p>
            </div>
         </motion.div>
       )}

    </div>
  )
}

function QuizTerminal({ state }: { state: any }) {
  const step = typeof state === 'number' ? state : state?.step || 0;
  const selections = state?.selections || [];

  return (
    <div className="font-mono text-xs space-y-1.5 text-zinc-300">
       {step >= 0 && <div className="text-zinc-500">[APScheduler]: Triggering job 'pomodoro_break_timer'</div>}
       {step >= 1 && <div className="text-[#A6E22E] font-semibold">{">"} Generating context-aware quiz...</div>}
       {step >= 1 && <div>[VectorDB]: Fetched 3 recent context chunks.<br/>[Groq Llama-3]: Generated 1 MCQ question.<br/>[Discord.py]: Dispatched interactive message with 4 buttons.</div>}
       {selections.map((opt: string, i: number) => (
         <div key={i}>
           <div className="text-[#A6E22E] font-semibold mt-2">{">"} Received interaction event: ComponentType.BUTTON (custom_id: 'quiz_opt_{opt.replace('Deselected ', '')}')</div>
           <div>[Logic]: Validated answer. Correct = {opt === 'B' ? 'True' : 'False'}.<br/>{opt === 'B' ? "[Database]: UPDATE users SET points = points + 10 WHERE user_id = '123'" : "[Logic]: No points awarded."}</div>
         </div>
       ))}
    </div>
  )
}

function VoiceMock({ setStepState }: { setStepState: (n: number) => void }) {
  const [step, setStep] = useState(0);
  useEffect(() => { setStepState(step); }, [step, setStepState]);

  return (
    <div className="flex flex-col gap-5 p-5 pb-16 text-sm font-sans">
       <motion.div initial={{opacity: 0}} animate={{opacity: 1}} transition={{delay: 0.5}} className="flex gap-3 items-center rounded bg-[#2B2D31] p-3 border border-border/5" onAnimationComplete={() => setStep(1)}>
          <div className="h-8 w-8 rounded bg-[#23A559] flex items-center justify-center"><Mic className="h-5 w-5 text-white"/></div>
          <div className="flex-1">
            <p className="text-white font-medium text-sm">Study Room A</p>
            <div className="flex items-center gap-1 mt-1">
              {[1, 2, 3, 4, 5].map((i) => (
                <motion.div key={i} animate={{height: ["4px", "12px", "4px"]}} transition={{duration: 0.5 + i*0.1, repeat: Infinity, ease: "easeInOut"}} className="w-1 bg-green-500 rounded-full"/>
              ))}
              <span className="text-xs text-green-500 ml-2 font-medium">Recording audio...</span>
            </div>
          </div>
       </motion.div>

       {step >= 1 && (
         <motion.div initial={{opacity: 0}} animate={{opacity: 1}} transition={{delay: 1.5}} className="flex items-center justify-center my-1" onAnimationComplete={() => setStep(2)}>
            <div className="h-[1px] flex-1 bg-white/10" />
            <span className="text-xs text-zinc-500 font-medium mx-3 uppercase tracking-wider">Live Transcript</span>
            <div className="h-[1px] flex-1 bg-white/10" />
         </motion.div>
       )}

       {step >= 2 && (
         <motion.div initial={{opacity: 0}} animate={{opacity: 1}} transition={{delay: 0.5}} className="flex flex-col gap-5 ml-11" onAnimationComplete={() => setStep(3)}>
            <motion.div initial={{opacity: 0, x: -10}} animate={{opacity: 1, x: 0}} transition={{delay: 0.5}}>
              <span className="text-blue-400 font-medium hover:underline cursor-pointer">Rahul:</span>
              <p className="text-zinc-300 mt-1 leading-relaxed">StatefulSets maintain stable pod identities across restarts.</p>
            </motion.div>
            <motion.div initial={{opacity: 0, x: -10}} animate={{opacity: 1, x: 0}} transition={{delay: 2}}>
              <span className="text-purple-400 font-medium hover:underline cursor-pointer">Ananya:</span>
              <p className="text-zinc-300 mt-1 leading-relaxed">Wait, then how does autoscaling work with persistent volumes?</p>
            </motion.div>
            <motion.div initial={{opacity: 0, x: -10}} animate={{opacity: 1, x: 0}} transition={{delay: 4}}>
              <span className="text-yellow-400 font-medium hover:underline cursor-pointer">Arjun:</span>
              <p className="text-zinc-300 mt-1 leading-relaxed">The paper proposes a connection-aware autoscaler instead of CPU-based scaling.</p>
            </motion.div>
         </motion.div>
       )}

       {step >= 3 && (
         <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{delay: 4.5}} className="flex gap-3 mt-4 border-t border-white/5 pt-5">
            <div className="h-8 w-8 rounded-full bg-green-600 flex-shrink-0 flex items-center justify-center"><Bot className="h-5 w-5 text-white"/></div>
            <div>
              <div className="flex items-center gap-2"><span className="font-medium text-white hover:underline cursor-pointer">Recall</span></div>
              <p className="text-zinc-300 mt-1 flex items-center gap-1.5"><CheckCircle2 className="h-4 w-4 text-green-500"/> Transcript appended to session notes.</p>
            </div>
         </motion.div>
       )}
    </div>
  )
}

function VoiceTerminal({ step }: { step: number }) {
  return (
    <div className="font-mono text-xs space-y-1.5 text-zinc-300">
       {step >= 0 && <div className="text-zinc-500">[Discord Voice]: Client connected to VoiceChannel(id=89234).</div>}
       {step >= 0 && <div className="text-[#A6E22E] font-semibold">{">"} Initializing PyNaCl Audio Sink...</div>}
       {step >= 1 && <div>[Whisper ASR]: Model loaded. Awaiting audio frames...</div>}
       {step >= 2 && <div>[Whisper ASR]: Transcribed chunk (User: Rahul) - 3.2s<br/>[Whisper ASR]: Transcribed chunk (User: Ananya) - 2.8s<br/>[Whisper ASR]: Transcribed chunk (User: Arjun) - 4.1s</div>}
       {step >= 3 && <div className="text-[#A6E22E] font-semibold">{">"} Compiling session transcript...</div>}
       {step >= 3 && <div>[LLM Worker]: Generated summary. Writing to session_notes.md.</div>}
    </div>
  )
}

function SchedulerMock({ setStepState }: { setStepState: (n: number) => void }) {
  const [step, setStep] = useState(0);
  useEffect(() => { setStepState(step); }, [step, setStepState]);

  return (
    <div className="flex flex-col gap-5 p-5 pb-16 text-sm font-sans">
       <div className="flex gap-3">
          <div className="h-8 w-8 rounded-full bg-blue-500 flex-shrink-0 flex items-center justify-center"><User className="h-5 w-5 text-white"/></div>
          <div>
            <div className="flex items-center gap-2"><span className="font-medium text-white hover:underline cursor-pointer">Student</span></div>
            <p className="text-zinc-300 mt-0.5">
              <TypewriterText text='/schedule create topic: "Distributed Systems Revision" time: "Tomorrow 5pm"' delay={0.5} onComplete={() => setStep(1)} />
            </p>
          </div>
       </div>

       {step >= 1 && (
         <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{delay: 0.5}} className="flex gap-3" onAnimationComplete={() => setStep(2)}>
            <div className="h-8 w-8 rounded-full bg-green-600 flex-shrink-0 flex items-center justify-center"><Bot className="h-5 w-5 text-white"/></div>
            <div className="w-full">
              <div className="flex items-center gap-2">
                <span className="font-medium text-white hover:underline cursor-pointer">Recall</span>
                <span className="rounded bg-[#5865F2] px-1 py-0.5 text-[10px] font-semibold text-white uppercase">Bot</span>
              </div>
              <div className="mt-2 rounded-lg border-l-4 border-l-yellow-500 bg-[#2B2D31] p-4 shadow-md">
                <h4 className="font-semibold text-white mb-4 flex items-center gap-2"><Calendar className="h-4 w-4"/> Study Session Scheduled</h4>
                <div className="grid grid-cols-2 gap-y-4">
                  <div>
                    <p className="text-zinc-400 text-[11px] font-semibold uppercase tracking-wider">Topic</p>
                    <p className="text-zinc-200 text-sm mt-1">Distributed Systems Revision</p>
                  </div>
                  <div>
                    <p className="text-zinc-400 text-[11px] font-semibold uppercase tracking-wider">Starts In</p>
                    <p className="text-zinc-200 text-sm mt-1">2 hours 14 minutes</p>
                  </div>
                </div>
              </div>
            </div>
         </motion.div>
       )}

       {step >= 2 && (
         <motion.div initial={{opacity: 0}} animate={{opacity: 1}} transition={{delay: 1.5}} className="flex items-center justify-center my-3" onAnimationComplete={() => setStep(3)}>
            <div className="h-[1px] flex-1 bg-white/5" />
            <span className="text-xs text-zinc-500 font-medium mx-3 uppercase tracking-wider">Next day at 16:55 UTC</span>
            <div className="h-[1px] flex-1 bg-white/5" />
         </motion.div>
       )}

       {step >= 3 && (
         <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{delay: 0.5}} className="flex gap-3">
            <div className="h-8 w-8 rounded-full bg-green-600 flex-shrink-0 flex items-center justify-center"><Bot className="h-5 w-5 text-white"/></div>
            <div>
              <div className="flex items-center gap-2"><span className="font-medium text-white hover:underline cursor-pointer">Recall</span></div>
              <p className="text-zinc-300 mt-1 flex items-center gap-2">
                <Clock className="h-4 w-4 text-yellow-500"/>
                <span><span className="text-blue-400 bg-blue-500/10 px-1 rounded font-medium">@StudyGroup</span> Reminder: Session starts in 5 mins!</span>
              </p>
            </div>
         </motion.div>
       )}
    </div>
  )
}

function SchedulerTerminal({ step }: { step: number }) {
  return (
    <div className="font-mono text-xs space-y-1.5 text-zinc-300">
       {step >= 0 && <div className="text-zinc-500">[Command Router]: Received /schedule create</div>}
       {step >= 1 && <div className="text-[#A6E22E] font-semibold">{">"} Parsing natural language time: "Tomorrow 5pm"</div>}
       {step >= 1 && <div>[DateParser]: Resolved to 2026-05-18 17:00:00 UTC.<br/>[APScheduler]: Job 'study_reminder_881' added to cron registry.</div>}
       {step >= 2 && <div className="text-zinc-500">[System]: Sleeping...</div>}
       {step >= 3 && <div className="text-[#A6E22E] font-semibold">{">"} Event Fired: Job 'study_reminder_881'</div>}
       {step >= 3 && <div>[Discord.py]: Dispatched message to TextChannel(id=9928).</div>}
    </div>
  )
}

function SummaryMock({ setStepState }: { setStepState: (n: number) => void }) {
  const [step, setStep] = useState(0);
  useEffect(() => { setStepState(step); }, [step, setStepState]);

  return (
    <div className="flex flex-col gap-5 p-5 pb-16 text-sm font-sans">
       <div className="flex gap-3">
          <div className="h-8 w-8 rounded-full bg-blue-500 flex-shrink-0 flex items-center justify-center"><User className="h-5 w-5 text-white"/></div>
          <div>
            <div className="flex items-center gap-2"><span className="font-medium text-white hover:underline cursor-pointer">Student</span></div>
            <p className="text-zinc-300 mt-0.5">
              <TypewriterText text="/study end" delay={0.5} onComplete={() => setStep(1)} />
            </p>
          </div>
       </div>

       {step >= 1 && (
         <motion.div initial={{opacity: 0, y: 10}} animate={{opacity: 1, y: 0}} transition={{delay: 0.5}} className="flex gap-3" onAnimationComplete={() => setStep(2)}>
            <div className="h-8 w-8 rounded-full bg-green-600 flex-shrink-0 flex items-center justify-center"><Bot className="h-5 w-5 text-white"/></div>
            <div className="w-full">
              <div className="flex items-center gap-2">
                <span className="font-medium text-white hover:underline cursor-pointer">Recall</span>
                <span className="rounded bg-[#5865F2] px-1 py-0.5 text-[10px] font-semibold text-white uppercase">Bot</span>
              </div>
              <div className="mt-2 rounded-lg border border-[#1E1F22] bg-[#2B2D31] p-4 shadow-md">
                <h4 className="font-semibold text-white mb-2 flex items-center gap-2">📚 Session Ended: Kubernetes Networking</h4>
                
                <div className="mt-4">
                  <h5 className="font-semibold text-blue-400 text-[10px] uppercase tracking-wider mb-2">Key Takeaways</h5>
                  <ul className="list-disc list-outside ml-4 text-zinc-300 text-sm space-y-1">
                    <li>Connection-density operators scale based on active connections per pod.</li>
                    <li>StatefulAutoscaler is highly effective but lacks a definitive success conclusion in the uploaded paper.</li>
                  </ul>
                </div>
                
                <div className="mt-4 pt-4 border-t border-white/5">
                  <h5 className="font-semibold text-purple-400 text-[10px] uppercase tracking-wider mb-2">Quiz Performance</h5>
                  <div className="space-y-1.5 text-sm">
                    <div className="flex justify-between items-center text-zinc-300">
                      <span>Student</span>
                      <span className="text-green-400 font-medium">3/3 correct (100%)</span>
                    </div>
                    <div className="flex justify-between items-center text-zinc-300">
                      <span>Jane</span>
                      <span className="text-yellow-400 font-medium">2/3 correct (66%)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
         </motion.div>
       )}
    </div>
  )
}

function SummaryTerminal({ step }: { step: number }) {
  return (
    <div className="font-mono text-xs space-y-1.5 text-zinc-300">
       {step >= 0 && <div className="text-zinc-500">[Command Router]: Received /study end</div>}
       {step >= 1 && <div className="text-[#A6E22E] font-semibold">{">"} Compiling session analytics...</div>}
       {step >= 1 && <div>[VectorDB]: Retrieving transcript chunks & quiz logs.<br/>[Groq Llama-3]: Generating executive summary...<br/>[System]: Distributing points and calculating accuracy.<br/>[Discord.py]: Formatting and dispatching embed to channel.</div>}
       {step >= 2 && <div className="text-[#A6E22E] font-semibold mt-4">{">"} Session gracefully terminated.</div>}
    </div>
  )
}


const featuresData = [
  {
    id: "rag",
    icon: FileText,
    title: "RAG Document Q&A",
    subtitle: "Document-Grounded AI",
    description: "Upload course PDFs and ask context-aware questions. The backend automatically performs semantic chunking using Langchain and stores vectors in ChromaDB. Utilizing Groq's Llama 3 8B model, the bot delivers synthesized answers complete with exact document citations."
  },
  {
    id: "quizzes",
    icon: Timer,
    title: "Pomodoro & Quizzes",
    subtitle: "Automated Knowledge Checks",
    description: "Initiate structured Pomodoro timers. During breaks, the bot automatically fetches recent context from the vector database and generates dynamic Multiple Choice Questions (MCQs) to test participants and update the leaderboard."
  },
  {
    id: "voice",
    icon: Mic,
    title: "Voice Transcriptions",
    subtitle: "Real-Time Group Learning",
    description: "Bring Recall into your Discord voice channel. It records real-time audio streams and transcribes them locally using OpenAI's Whisper ASR model. Transcripts are synthesized into actionable study session summaries."
  },
  {
    id: "scheduler",
    icon: Calendar,
    title: "Session Scheduler",
    subtitle: "Coordinate Without Leaving",
    description: "Coordinate your study group effortlessly. Powered by APScheduler, use '/schedule create' to set up recurring or one-off study sessions. The bot handles timezone-aware logic and automatically pings your server."
  },
  {
    id: "summary",
    icon: ClipboardList,
    title: "Session Summaries",
    subtitle: "AI-Powered Study Sessions",
    description: "Turn your Discord server into a dedicated learning environment with automatic quizzes, voice transcripts, and instant AI-generated session summaries."
  }
]

export function Features() {
  const [activeTab, setActiveTab] = useState(featuresData[0].id)
  const [mockStep, setMockStep] = useState(0)
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  const activeFeature = featuresData.find(f => f.id === activeTab) || featuresData[0]

  return (
    <section ref={ref} className="bg-background pt-10 md:pt-16 pb-20 md:pb-32">
      <div className="mx-auto max-w-7xl px-6">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="mb-12 text-center"
        >
          <h2 className="mx-auto max-w-3xl font-display text-4xl font-bold tracking-tight text-foreground md:text-5xl">
            AI-native collaboration inside an existing communication platform.
          </h2>
        </motion.div>

        {/* Horizontal Navigation Tabs */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="flex flex-wrap justify-center gap-3 mb-16"
        >
          {featuresData.map((feature) => {
            const isActive = activeTab === feature.id;
            return (
              <button
                key={feature.id}
                onClick={() => {setActiveTab(feature.id); setMockStep(0)}}
                className={"flex items-center gap-2.5 px-6 py-3.5 rounded-full text-sm font-semibold transition-all duration-300 " + (isActive ? "bg-foreground text-background shadow-lg scale-105" : "bg-secondary border border-border text-foreground hover:bg-secondary/80")}
              >
                <feature.icon className={"h-4 w-4 " + (isActive ? "text-background" : "text-muted-foreground")} />
                {feature.title}
              </button>
            )
          })}
        </motion.div>

        {/* Massive Showcase Area */}
        <motion.div 
          initial={{ opacity: 0, y: 40 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.4 }}
          className="bg-secondary/20 rounded-3xl border border-border p-6 md:p-10 shadow-2xl"
        >
          <div className="mb-10 text-center max-w-3xl mx-auto">
            <h3 className="text-2xl font-display font-bold text-foreground">{activeFeature.title}</h3>
            <p className="text-muted-foreground mt-3 text-base leading-relaxed">{activeFeature.description}</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            
            {/* Discord Mock */}
            <div className="flex flex-col overflow-hidden rounded-2xl border border-[#1E1F22] bg-[#313338] shadow-2xl font-sans h-[550px]">
               <div className="flex items-center gap-2 border-b border-[#1E1F22] bg-[#2B2D31] px-4 py-3 shadow-sm shrink-0">
                  <Hash className="h-5 w-5 text-zinc-400" />
                  <span className="font-semibold text-white text-md">study-group</span>
               </div>
               <div className="flex-1 overflow-y-auto overscroll-contain custom-scrollbar relative min-h-0">
                  <AnimatePresence mode="wait">
                    <motion.div key={activeFeature.id} initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}>
                       {activeFeature.id === "rag" && <RagMock setStepState={setMockStep} />}
                       {activeFeature.id === "quizzes" && <QuizMock setStepState={setMockStep} />}
                       {activeFeature.id === "voice" && <VoiceMock setStepState={setMockStep} />}
                       {activeFeature.id === "scheduler" && <SchedulerMock setStepState={setMockStep} />}
                       {activeFeature.id === "summary" && <SummaryMock setStepState={setMockStep} />}
                    </motion.div>
                  </AnimatePresence>
               </div>
               <div className="bg-[#313338] px-4 pb-4 pt-2 shrink-0">
                  <div className="flex items-center gap-3 rounded-lg bg-[#383A40] px-4 py-2.5">
                    <span className="text-zinc-400 text-sm flex-1">Message #study-group</span>
                  </div>
               </div>
            </div>

            {/* Terminal Logs Mock */}
            <div className="flex flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#1E1E1E] shadow-2xl font-mono text-sm h-[550px]">
               <div className="flex items-center gap-2 border-b border-white/10 bg-[#2D2D2D] px-4 py-3 shrink-0">
                  <div className="flex gap-1.5">
                    <div className="h-3 w-3 rounded-full bg-[#FF5F56]" />
                    <div className="h-3 w-3 rounded-full bg-[#FFBD2E]" />
                    <div className="h-3 w-3 rounded-full bg-[#27C93F]" />
                  </div>
                  <div className="ml-3 flex items-center gap-2 text-xs text-white/50 font-sans font-medium uppercase tracking-wider">
                    <Terminal className="h-3 w-3" />
                    <span>backend-server-logs</span>
                  </div>
               </div>
               <div className="flex-1 p-6 overflow-y-auto overscroll-contain whitespace-pre-wrap leading-relaxed custom-scrollbar bg-[#0D0D0D] min-h-0">
                  <AnimatePresence mode="wait">
                    <motion.div key={activeFeature.id} initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}>
                       {activeFeature.id === "rag" && <RagTerminal step={mockStep} />}
                       {activeFeature.id === "quizzes" && <QuizTerminal state={mockStep} />}
                       {activeFeature.id === "voice" && <VoiceTerminal step={mockStep} />}
                       {activeFeature.id === "scheduler" && <SchedulerTerminal step={mockStep} />}
                       {activeFeature.id === "summary" && <SummaryTerminal step={mockStep} />}
                    </motion.div>
                  </AnimatePresence>
               </div>
            </div>

          </div>
        </motion.div>
      </div>
    </section>
  )
}
