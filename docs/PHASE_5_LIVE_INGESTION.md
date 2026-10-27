# Phase 5 Specification: Live Ingestion Stepper UI

**Status**: Completed  
**Route**: `app/generate/page.tsx`  
**Purpose**: Hackathon pitch visual center. Lets judges type a GitHub URL or local path and watch the live ingestion pipeline run in real-time.

---

## 1. UI Components
1. **Input Section**:
   - URL / Local path input field with quick-fill buttons for demo repositories (e.g. `payment-gateway`, `auth-sentinel`).
   - "Start Ingestion" trigger button.
2. **Visual Pipeline Stepper**:
   - Multi-step progress list:
     1. `Clone Repository` (with byte count / elapsed timer)
     2. `Repomix Codebase Bundler` (XML token count estimate)
     3. `Synthesize Table of Contents` (TOC schema generation)
     4. `Generate Documentation Pages` (parallel progress 0/4 -> 4/4)
     5. `Build PageIndex Hierarchy` (heading trees + summaries)
     6. `Index Complete`
   - Active step has pulsing glow indicator; completed steps show checkmarks.
3. **Completion Card**:
   - Shows summary of generated wiki with "Open Wiki" and "Chat With Repo" CTA buttons.
