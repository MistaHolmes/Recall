import { SmoothScroll } from "@/components/smooth-scroll"
import { StructuredData } from "@/components/structured-data"
import { Header } from "@/components/sections/header"
import { Hero } from "@/components/sections/hero"
import { TrustBar } from "@/components/sections/trust-bar"
import { NotesPreview } from "@/components/sections/notes-preview"
import { Features } from "@/components/sections/features"
import { CTA } from "@/components/sections/cta"
import { Footer } from "@/components/sections/footer"

export default function Home() {
  return (
    <SmoothScroll>
      <StructuredData />
      <Header />
      <main>
        <Hero />
        <TrustBar />
        <NotesPreview />
        <Features />
        <CTA />
      </main>
      <Footer />
    </SmoothScroll>
  )
}
