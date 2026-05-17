"use client"

import { motion, useInView } from "motion/react"
import { useRef } from "react"
import { Check, ArrowRight } from "lucide-react"

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "For casual note-takers getting started.",
    featured: false,
    cta: "Get Started",
    features: [
      "Up to 50 notes",
      "Basic search & tagging",
      "Single device access",
      "Community support",
    ],
  },
  {
    name: "Pro",
    price: "$69",
    period: "/year",
    description: "For power users who need more.",
    featured: true,
    cta: "Upgrade to Pro",
    features: [
      "Unlimited notes & notebooks",
      "Advanced search & tagging",
      "Real-time collaboration",
      "Cloud sync across devices",
      "Priority email support",
    ],
  },
  {
    name: "Vision Pro",
    price: "$149",
    period: "/year",
    description: "For teams that think together.",
    featured: false,
    cta: "Contact Sales",
    features: [
      "Everything in Pro",
      "Team dashboards & workspaces",
      "Admin roles & permissions",
      "Dedicated support manager",
      "Custom integrations",
    ],
  },
]

export function Pricing() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section
      ref={ref}
      id="pricing"
      aria-labelledby="pricing-heading"
      className="bg-background py-20 md:py-28"
    >
      <div className="mx-auto max-w-5xl px-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="mb-16 text-center"
        >
          <p className="mb-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">
            Pricing
          </p>
          <h2
            id="pricing-heading"
            className="font-display text-3xl font-bold tracking-tight text-foreground md:text-4xl text-balance"
          >
            Choose your pricing plan
          </h2>
          <p className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-muted-foreground">
            Keep your notes organized, clear, and easy to find. Every thought
            flows into a system that adapts to your style.
          </p>
        </motion.div>

        {/* Cards */}
        <div className="grid items-stretch gap-5 md:grid-cols-3">
          {plans.map((plan, i) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 30 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.12 * i }}
              className={`group relative flex flex-col rounded-2xl border transition-all duration-300 ${
                plan.featured
                  ? "border-foreground bg-foreground text-primary-foreground shadow-2xl md:-my-4 md:py-2"
                  : "border-border bg-card text-foreground hover:border-foreground/20 hover:shadow-lg"
              }`}
            >
              {/* Badge */}
              {plan.featured && (
                <div className="flex justify-center pt-6">
                  <span className="rounded-full border border-primary-foreground/20 bg-primary-foreground/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-widest text-primary-foreground/80">
                    Most Popular
                  </span>
                </div>
              )}

              <div className={`flex flex-1 flex-col p-7 ${plan.featured ? "pt-4" : ""}`}>
                {/* Plan Name */}
                <p
                  className={`text-sm font-medium ${
                    plan.featured
                      ? "text-primary-foreground/60"
                      : "text-muted-foreground"
                  }`}
                >
                  {plan.name}
                </p>

                {/* Price */}
                <div className="mt-3 flex items-baseline gap-1.5">
                  <span className="font-display text-4xl font-bold tracking-tight">
                    {plan.price}
                  </span>
                  <span
                    className={`text-sm ${
                      plan.featured
                        ? "text-primary-foreground/40"
                        : "text-muted-foreground"
                    }`}
                  >
                    {plan.period}
                  </span>
                </div>

                {/* Description */}
                <p
                  className={`mt-2 text-sm leading-relaxed ${
                    plan.featured
                      ? "text-primary-foreground/50"
                      : "text-muted-foreground"
                  }`}
                >
                  {plan.description}
                </p>

                {/* Divider */}
                <div
                  className={`my-6 h-px ${
                    plan.featured ? "bg-primary-foreground/10" : "bg-border"
                  }`}
                />

                {/* Features */}
                <ul className="flex-1 space-y-3.5">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3">
                      <span
                        className={`mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full ${
                          plan.featured
                            ? "bg-primary-foreground/15"
                            : "bg-foreground/5"
                        }`}
                      >
                        <Check
                          className={`h-2.5 w-2.5 ${
                            plan.featured
                              ? "text-primary-foreground/70"
                              : "text-foreground/60"
                          }`}
                          strokeWidth={3}
                        />
                      </span>
                      <span
                        className={`text-sm leading-snug ${
                          plan.featured
                            ? "text-primary-foreground/70"
                            : "text-muted-foreground"
                        }`}
                      >
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <a
                  href="#cta"
                  className={`mt-8 flex items-center justify-center gap-2 rounded-xl py-3 text-sm font-medium transition-all duration-200 ${
                    plan.featured
                      ? "bg-primary-foreground text-foreground hover:bg-primary-foreground/90"
                      : "border border-border bg-transparent text-foreground hover:bg-foreground hover:text-primary-foreground"
                  }`}
                >
                  {plan.cta}
                  <ArrowRight className="h-3.5 w-3.5" />
                </a>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
