# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Department engineers** who inherit or maintain repositories with little to no documentation, and need to understand a service's architecture, setup, and API before touching it.
- **New joiners** onboarding onto unfamiliar microservices who must trace how components connect without reading source line by line.
- **Hackathon judges** evaluating the project in a live 3-minute demo, who need to see the mechanism work end to end.
- **Docs maintainers** who would otherwise hand-write wikis and watch them rot.

## Product Purpose

GoWiki turns an undocumented repository into a browsable, structured technical wiki and a grounded question-answering surface. It exists because documentation written by hand does not survive the pace of departmental code changes. Success means an engineer can go from a bare repository to trustworthy, cited answers about its architecture in minutes, without a human writing documentation first.

## Positioning

Retrieval is vectorless. Instead of chunking source into embeddings and hoping similarity finds the right passage, GoWiki compiles the documentation into a hierarchical tree index and lets the model reason down that tree, the way a reader works through a table of contents. Answers name the exact document node they came from, so every claim is traceable to a section a human can open and read.

## Operating Context

- Repositories are ingested either from a public Git URL or a local path, bundled for token efficiency, then documented.
- The demo runs against personal project repositories rather than real organization code.
- The wiki is consumed in a browser: a repository directory, a documentation reader with a page sidebar and per-page table of contents, a reasoning chat surface, and a live ingestion progress view.
- The language model is provider-agnostic; the current hackathon deployment routes through a single OpenAI-compatible gateway.
- Judges see one repository already documented and one repository ingested live during the pitch.
- Deployment is a single local machine: the web app and the Python service run on localhost. No public host, no LAN sharing, no cloud storage backend. Server-side filesystem reads from `content/` are therefore legitimate and must be preserved.

## Capabilities and Constraints

- **Ingestion**: shallow clone, repository bundling with noise excluded (tests, lockfiles, binaries, lockfiles), two-pass documentation synthesis.
- **Generated pages**: a fixed, uniform page set per repository — overview, architecture, setup, API reference.
- **Reasoning chat**: repository-scoped questions answered by tree navigation over the generated wiki, with node-level citations that link back to the exact wiki section.
- **Constraint**: the wiki reader must function entirely from content already on disk, so a network failure during a demo does not break browsing.
- **Constraint**: chat operates on one repository at a time, selected explicitly.
- **Constraint**: generated documentation is the retrieval corpus; the wiki is not a mirror of source files.

## Brand Commitments

The product name is GoWiki. No visual identity, palette, or typographic system has been made binding yet.

## Accessibility & Inclusion

WCAG AA baseline is a requirement, not an aspiration: text contrast meets AA in both themes, every interactive element has a visible focus state, chat and sidebar navigation are operable by keyboard alone, and landmark regions (banner, navigation, main) are semantic.

## Evidence on Hand

- `content/payment-gateway/` — a complete seeded wiki: four documentation pages, a repository metadata file, and a tree index.
- `content/auth-sentinel/` — a three-page seeded wiki with its metadata and tree index.
- `PLAN.md` and `docs/` — the architecture contract, phase specifications, and demo runbook.
- No real customer testimonials, benchmarks, adoption metrics, or organizational endorsements exist. None may be fabricated.

## Product Principles

1. **Ground every claim.** An answer without a citable document node is a failure, not a feature.
2. **Show the machinery.** The pipeline is the pitch: ingestion, synthesis, and tree navigation are visible to the user rather than hidden behind a spinner.
3. **Uniform structure beats bespoke prose.** Every repository gets the same page skeleton so readers learn the shape once.
4. **Survive the demo.** Anything that can fail on stage — network, model latency, cloning — needs a pre-seeded or local fallback.
5. **Documentation is the product surface.** The wiki reader is not an afterthought bolted onto the chatbot; it is the primary artifact.
