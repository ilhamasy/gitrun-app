---
name: GoWiki
description: Generated repository wikis drawn as transit lines, where every section number is a citation address.
colors:
  paper: '#f4f4ef'
  paper-2: '#eaebe4'
  surface: '#ffffff'
  ink: '#151a1d'
  ink-2: '#525c63'
  ink-3: '#5c656b'
  hairline: '#dcddd3'
  hairline-strong: '#b9bbb0'
  enamel: '#10365a'
  enamel-deep: '#0b2740'
  signal: '#f5c518'
  on-enamel: '#ffffff'
  focus-on-paper: '#10365a'
  focus-on-enamel: '#f5c518'
  line-harbour: '#1f5c94'
  line-bramble: '#7a2141'
  line-cedar: '#11643f'
  line-amber: '#8a4b00'
  line-violet: '#4a3c7a'
  timetable-field: '#0d1c2b'
  timetable-ink: '#e8edf2'
  timetable-rule: '#1e3a52'
  timetable-head-ink: '#c9dcec'
  fault-red: '#a3231b'
  paper-dark: '#0e1417'
  paper-2-dark: '#151c20'
  surface-dark: '#1a2226'
  ink-dark: '#e9e9e3'
  ink-2-dark: '#a7b0b6'
  ink-3-dark: '#95a0a6'
  hairline-dark: '#2a3439'
  hairline-strong-dark: '#3b474d'
  enamel-dark: '#1a4a72'
  enamel-deep-dark: '#0f3355'
  focus-on-paper-dark: '#f5c518'
  line-harbour-dark: '#2b6ea8'
  line-bramble-dark: '#ad3a60'
  line-cedar-dark: '#1a7a4f'
  line-amber-dark: '#a05c0a'
  line-violet-dark: '#6a57a6'
  line-harbour-ink-dark: '#6fa8d6'
  line-bramble-ink-dark: '#d07e9c'
  line-cedar-ink-dark: '#5fb68c'
  line-amber-ink-dark: '#d9a15b'
  line-violet-ink-dark: '#a295d6'
  timetable-field-dark: '#070d11'
  fault-red-dark: '#e0705f'
typography:
  display:
    fontFamily: Barlow Condensed, "Arial Narrow", sans-serif
    fontSize: 4.25rem
    fontWeight: 600
    lineHeight: 0.98
    letterSpacing: -0.005em
  body:
    fontFamily: Source Serif 4, Georgia, serif
    fontSize: 1.0625rem
    fontWeight: 400
    lineHeight: 1.68
    letterSpacing: normal
  label:
    fontFamily: Barlow Condensed, "Arial Narrow", sans-serif
    fontSize: 0.8125rem
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: 0.11em
  label-wide:
    fontFamily: Barlow Condensed, "Arial Narrow", sans-serif
    fontSize: 0.625rem
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: 0.16em
  mono:
    fontFamily: JetBrains Mono, ui-monospace, monospace
    fontSize: 0.8125rem
    fontWeight: 400
    lineHeight: 1.65
    letterSpacing: -0.01em
rounded:
  sm: 0px
  md: 0px
  lg: 0px
  xl: 0px
  2xl: 0px
  3xl: 0px
  4xl: 0px
spacing:
  hairline: 1px
  2px: 2px
  4px: 4px
  6px: 6px
  8px: 8px
  10px: 10px
  12px: 12px
  14px: 14px
  16px: 16px
  20px: 20px
  24px: 24px
  28px: 28px
  32px: 32px
  36px: 36px
  40px: 40px
  48px: 48px
  56px: 56px
  64px: 64px

components:
  masthead:
    backgroundColor: '{colors.enamel}'
    textColor: '{colors.on-enamel}'
    height: 56px
    width: 100%
  masthead-link:
    textColor: 'color-mix(in srgb, #ffffff 74%, transparent)'
    height: 56px
    padding: 0 2px
  masthead-link-current:
    textColor: '{colors.on-enamel}'
    height: 56px
    padding: 0 2px
  route-strip:
    backgroundColor: '{colors.enamel-deep}'
    textColor: '{colors.on-enamel}'
    padding: 10px 24px
  rail:
    backgroundColor: '{colors.paper-2}'
    textColor: '{colors.ink-2}'
    width: 256px
    height: calc(100vh - 56px)
  rail-station:
    backgroundColor: transparent
    textColor: '{colors.ink-2}'
    padding: 9px 14px 9px 11px
  rail-station-hover:
    backgroundColor: 'color-mix(in srgb, #ffffff 70%, transparent)'
    textColor: '{colors.ink}'
    padding: 9px 14px 9px 11px
  rail-station-active:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.ink}'
    padding: 9px 14px 9px 11px
  station-index-link:
    textColor: '{colors.ink-2}'
    padding: 5px 0 5px 10px
    width: 160px
  station-index-link-active:
    backgroundColor: '{colors.paper-2}'
    textColor: '{colors.ink}'
    padding: 5px 0 5px 10px
    width: 160px
  board-row:
    backgroundColor: transparent
    textColor: '{colors.ink}'
    padding: 17px 20px
    width: 100%
  board-row-hover:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.ink}'
    padding: 17px 20px
    width: 100%
  button-primary:
    backgroundColor: '{colors.enamel}'
    textColor: '{colors.on-enamel}'
    typography: '{typography.label}'
    rounded: '{rounded.sm}'
    padding: 0 18px
    height: 40px
  button-primary-hover:
    backgroundColor: '{colors.enamel-deep}'
    textColor: '{colors.on-enamel}'
    rounded: '{rounded.sm}'
    height: 40px
  button-signal:
    backgroundColor: '{colors.signal}'
    textColor: '{colors.ink}'
    typography: '{typography.label}'
    rounded: '{rounded.sm}'
    padding: 0 18px
    height: 40px
  button-signal-hover:
    backgroundColor: 'color-mix(in srgb, #f5c518 84%, #151a1d)'
    textColor: '{colors.ink}'
    rounded: '{rounded.sm}'
    height: 40px
  button-quiet:
    backgroundColor: transparent
    textColor: '{colors.ink}'
    typography: '{typography.label}'
    rounded: '{rounded.sm}'
    padding: 0 18px
    height: 40px
  button-quiet-hover:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.ink}'
    rounded: '{rounded.sm}'
    height: 40px
  button-on-enamel:
    backgroundColor: transparent
    textColor: '{colors.on-enamel}'
    typography: '{typography.label}'
    rounded: '{rounded.sm}'
    padding: 0 14px
    height: 36px
  tag:
    backgroundColor: transparent
    textColor: '{colors.ink-2}'
    rounded: '{rounded.sm}'
    padding: 3px 7px
  tag-on-signal:
    backgroundColor: '{colors.signal}'
    textColor: '{colors.ink}'
    rounded: '{rounded.sm}'
    padding: 3px 7px
  code-cell:
    backgroundColor: '{colors.timetable-field}'
    textColor: '{colors.timetable-ink}'
    typography: '{typography.mono}'
    rounded: '{rounded.sm}'
    padding: 15px 16px
  code-cell-head:
    backgroundColor: '{colors.enamel}'
    textColor: '{colors.timetable-head-ink}'
    typography: '{typography.label-wide}'
    padding: 5px 12px
---

# Design System: GoWiki

## Overview

**Creative North Star: "The Signal Box"**

GoWiki is drawn as the instrument room of a transit authority: a schematic in hairlines on paper, a line that names every stop, and one lamp that says where you are standing. Every mark on the page is an address or a direction — a station number, a pip on the line, a citation that names the section it came from. The surface should look *issued* rather than *styled*, the way a printed timetable looks set rather than designed: paper ground, an enamel-blue header field, condensed signage capitals for anything that names a place, and a serif reading column for anything that explains one.

Density is high and volume is low. Many quiet 1px hairlines carry structure, so almost nothing needs to shout: the largest ink in the system is a condensed display line, and the loudest colour is a single yellow lamp that appears on three elements at most. Corners are square down to the last token. There are no shadows anywhere in the build — depth is a matter of which field a thing sits on, not how far it floats above the page.

The world deliberately rejects the documentation-site default it could have become: grey sidebar, rounded cards, soft drop shadows, a gradient hero, a pill-shaped tag. It rejects them because a generated wiki that looks hand-assembled contradicts the product's central claim — that every sentence has a machine-addressable source. The instrument metaphor is the argument.

**Key Characteristics:**
- Square by default: every radius token (`--radius-sm` through `--radius-4xl`) resolves to 0px, and the station pip is a square inside a square.
- Paper ground with an enamel header field; white is a *raised* surface, never the page.
- Signal yellow (#f5c518) is a lamp, not a brand colour: current station, keyboard focus, and a status that needs attention.
- One line hue per repository, resolved through `data-line` into `--line` and `--line-ink`, never written into markup.
- Depth without shadow: 1px hairlines, field changes, and 2px ink rules.
- One authored motion — the rail line drawing itself to the current station — plus 140ms and 240ms state transitions.

## Colors

A printed-transit palette: warm paper, near-black ink, enamel blue for the fields that carry the product's name, and a single high-chroma lamp.

### Primary
- **Enamel Blue** (#10365a): the masthead field, primary buttons, the code-cell header, and the focus ring on paper. It is the only large saturated field in the system, which is why it can carry the header without decoration.
- **Deep Enamel** (#0b2740): primary-button hover, the 1px rule under the masthead, and the fallback field for the route strip before a line hue resolves.

### Secondary
- **Signal Yellow** (#f5c518): the lamp. It marks the active rail pip, the current masthead destination (a 3px underline), keyboard focus on enamel, the skip link, `::selection`, and the "needs you now" stamp. It is a signal in the literal sense — a value that changes meaning — and it loses all meaning if it is used as ambience.
- **Line identity — Harbour** (#1f5c94), **Bramble** (#7a2141), **Cedar** (#11643f), **Amber** (#8a4b00), **Violet** (#4a3c7a): one hue per repository, assigned deterministically from the repository name, so a line never changes colour between visits. Each hue has two values: a **field** value for fills (route strip, pip borders, the drawn rail line at 32% opacity, list bullets, link underlines) and an **ink** value for text on paper. In light mode the two coincide; in the dark theme they separate, because a field that stays saturated becomes unreadable as text on a dark ground (Harbour ink becomes #6fa8d6, Bramble #d07e9c, Cedar #5fb68c, Amber #d9a15b, Violet #a295d6).

### Neutral
- **Paper** (#f4f4ef): the page ground, in every surface including the reading column.
- **Platform Grey** (#eaebe4): the rail, table header rows, the active station-index row, and quiet fills.
- **Chalk Surface** (#ffffff): the top of the ladder — hover fill on board rows, the active rail station, panels, inputs. White is never the page.
- **Tunnel Ink** (#151a1d): body text, 2px wayfinding rules, the active code chip in the station index.
- **Secondary Ink** (#525c63): descriptions, inactive rail stations.
- **Tertiary Ink** (#5c656b): station codes, meta labels, timestamps.
- **Hairline** (#dcddd3): the 1px divider that does most of the structural work in the system.
- **Hairline Strong** (#b9bbb0): control borders, scrollbar thumb, tag outlines.
- **Timetable Night** (#0d1c2b), **Timetable Chalk** (#e8edf2), **Timetable Rule** (#1e3a52), **Timetable Head Ink** (#c9dcec): the code cell — a dark window inside a paper page, deliberately not theme-dependent in light mode.
- **Fault Red** (#a3231b): destructive and error states only; it is rare enough that it reads as an alarm.
- The dark theme re-points the same roles rather than inventing new ones: Paper #0e1417, Platform Grey #151c20, Chalk Surface #1a2226, Tunnel Ink #e9e9e3, Secondary Ink #a7b0b6, Tertiary Ink #95a0a6, Hairline #2a3439, Hairline Strong #3b474d, Enamel #1a4a72, Deep Enamel #0f3355, and focus moves from enamel to signal.

### Named Rules
**The Signal Reservation Rule.** Signal yellow marks exactly three classes of thing: where you are (the active pip, the current destination, `::selection` on the text you have claimed), where the keyboard is (the focus ring on enamel, the skip link), and a state that asks for you now (the `Not connected` stamp, the signal button). It is never a hover fill on a neutral control, never a heading accent, never a decorative wash — a lamp that is always on is not a lamp.

**The Line Hue Identity Rule.** A repository's hue is assigned by hash and expressed only as `--line` / `--line-ink` through `data-line`. Fills use the field value; text, underlines, and bullet marks use the ink value. No component writes a hue as a literal, and no page picks a hue to look nice.

## Typography

**Display Font:** Barlow Condensed (with "Arial Narrow", sans-serif)
**Body Font:** Source Serif 4 (with Georgia, serif)
**Label Font:** Barlow Condensed, uppercase, widened tracking
**Mono Font:** JetBrains Mono (with ui-monospace, monospace)

**Character:** Two voices, cleanly split. Barlow Condensed is the signage voice — compressed, confident, always capitalised when it names a place, a control, or a count. Source Serif 4 is the reading voice, set at a generous 1.68 line height so a dense technical page stays readable at arm's length on a projector. JetBrains Mono is the address voice: station codes, node IDs, section numbers, and code. Nothing is set in a fourth family, and no role borrows another's font.

### Hierarchy
- **Display** (600, up to 4.25rem / 68px, 0.98 line height, -0.005em): the home headline and the reader's H1 (2.25rem mobile, 2.875rem at `sm`). Condensed and tightly leaded; balanced wrapping is on.
- **Section head** (700, 1.5rem, 1.2, 0.012em): the reading column's H2, which floats right its section address and sits under a 2px ink rule with 3.25rem of space above. H3 (700, 1.125rem, 0.02em) and H4 (700, 0.9375rem, uppercase, 0.08em) step down without leaving the signage family.
- **Title** (600, 1.375rem, 1.15, 0.01em): board destinations and the name of the thing you are about to open.
- **Body** (400, 1.0625rem / 17px, 1.68, 64ch measure): the reading column. List items and blockquotes inherit it; the base document body uses 1.62.
- **Label** (700, 0.8125rem / 13px, 0.11em, uppercase): the control voice — buttons and masthead destinations. Its smaller siblings are the cap labels: 0.6875rem / 600 / 0.1em for the rail head and table heads, and **Label-wide** (600, 0.625rem / 10px, 0.16em) for the route strip, code-cell language, board column heads and generation dates. Tags and board meta use 0.625rem at 0.13em.
- **Station name** (600, 0.875rem, 0.045em, uppercase, single line with ellipsis): the rail's station titles; the active one steps to 700 and its code slot reads `HERE`.
- **Mono / data** (400, 0.8125rem, -0.01em, tabular numerals): counts, station codes, node totals, code. The station index drops to 0.6875rem at 0.04em; the code cell sets 0.8125rem at 1.65.

### Named Rules
**The Measure Rule.** The reading column is 64ch and stays 64ch. It is not stretched to fill a wide monitor and not widened for tables; a 66ch figure that appeared in an early brief is retired — 64ch is the printed line length the page is typeset to, and the side column leaves the layout before the measure would ever shrink.

**The Signage–Serif Split Rule.** Barlow Condensed names things, Source Serif 4 explains them, JetBrains Mono addresses them. The one deliberate exception is the station-index label, set in serif because it is the section's own prose title, not a place name — everything else that navigates is signage.

## Layout

A fixed 56px masthead over a paper shell. The full-bleed container caps at 1600px; the reading page caps narrower, at 1180px, so the measure is never at the mercy of a wide screen.

Inside a wiki repository the shell is a horizontal split: a **256px rail** on the left, sticky at `top: 56px`, scrolling independently to `calc(100vh - 56px)`; then a flexible content column. The reading page inside it centres a **64ch measure** with comfortable page padding (20px → 32px). The **station index** sits in the right margin as a 248px column; a 40px left gutter leaves **208px of content**, and the sticky block's own 24px inset leaves about 160px for the links themselves. It sticks at 100px so it clears both the masthead and the route strip.

The rhythm is a 4px grid with half-steps where a hairline has to sit tight: 2 / 6 / 10 / 14 alongside 4 / 8 / 12 / 16 / 20 / 24 / 28 / 32 / 36 / 40 / 48 / 56 / 64. Board rows use 17px vertical and 20px horizontal padding; rail stations use 9px/14px; the masthead is exactly one rhythm step tall at 56px, which is also the offset the rail and every anchored heading use (anchored targets get 7rem, clearing masthead plus route strip).

Responsive behaviour is a staircase, not a collapse:
- **≥1280px**: reading + station index. The aside only appears here, because below it the aside would compete with the measure.
- **1024–1279px**: reading only; the measure keeps its full 64ch and the page simply ends earlier.
- **<1024px**: the rail leaves the vertical column and becomes a horizontal, scrollable line diagram beneath the masthead — same pips, same codes, same order, with the rail header and interchange extras removed and a mask fade at the right edge to show the line continues. Nothing becomes a drawer or a hamburger.
- **<640px**: the masthead destinations scroll horizontally beside the wordmark (short labels, never truncated into an ellipsis mid-word) and the same mask fade signals more content. The measure becomes 100% of the viewport width.
- Hairline grids (`gap: 1px` over a hairline background) are the table device: the gap *is* the divider, so no cell needs a border of its own.

### Named Rules
**The One Address Rule.** Every section has exactly one number, and the margin owns it. Author-typed numerals are stripped from headings on render, and the station index and the citation both read from the same heading parse — so the address printed in the margin and the address quoted in an answer can never disagree.

**The Rail-Before-Content Rule.** Navigation is drawn, not hidden. The rail is present at every width: vertical and sticky above 1024px, horizontal and scrollable below it. There is no state in which a reader cannot see the line they are on.

## Elevation & Depth

**This system uses no shadows. There are zero `box-shadow` declarations in the build, and that is an invariant, not an omission.**

Depth comes from three devices instead: (1) a three-step field ladder — Paper (#f4f4ef) as ground, Platform Grey (#eaebe4) as recessed furniture, Chalk Surface (#ffffff) as raised; (2) 1px hairlines (#dcddd3) that separate without lifting; and (3) 2px ink rules (#151a1d) that mark a genuine boundary — the top of a section, the header of a table, the seam above previous/next station. The enamel masthead is the one element that reads as *above* the page, and it earns that by being a saturated field pinned to the top, not by casting anything.

The only soft edges in the system are mask fades at the ends of scrollable strips (the masthead nav and the horizontal rail). They indicate that content continues; they are not decorative gradients, and they never appear on a static surface.

### Named Rules
**The No-Shadow Rule.** A shadow implies an object floating above the page, and nothing here floats — every element is printed onto the paper. If a surface needs to read as raised, move it up the field ladder and give it a hairline, not a blur.

**The Field-Before-Border Rule.** Reach for a field change before a border. A row hover is a move to Chalk Surface; only genuine separations get a hairline, and only wayfinding gets a 2px rule.

## Shapes

Square, everywhere we set a corner. `--radius`, `--radius-sm`, `--radius-md`, `--radius-lg`, `--radius-xl`, `--radius-2xl`, `--radius-3xl`, and `--radius-4xl` all resolve to **0px**, so Tailwind's rounded utilities are inert by construction — a rounded class cannot accidentally reintroduce a curve.

The memorable silhouette is the **station pip**: a 21px square ground with an 11px square inside it, outlined at 2px in the line hue. It is not a circle and not a dot — it reads as a printed symbol on a schematic, and the same 14px square-in-square appears as the wordmark mark in the masthead. Tags are stamps with 1px outlines and square corners, not pills. Code cells are windows with a flat header bar. Buttons are rectangles. Nothing we draw is rounded; the browser's own focus ring and native scrollbar are the only curved or platform-drawn edges on the page.

Borders come in exactly two weights: **1px** for structure (hairlines, control outlines, dividers) and **2px** for wayfinding (section tops, table heads, the previous/next seam, the active station-index edge). A 3px mark is reserved for the signal underline under the current masthead destination.

### Named Rules
**The Square-By-Default Rule.** Nothing is rounded — not tags, not buttons, not panels, not the pip. If a shape feels too sharp, the fix is spacing or a hairline, never a radius.

**The Border Weight Rule.** 1px divides, 2px addresses, 3px signals. There is no fourth weight: a hairline never thickens to look important, and a decorative rule never appears at all.

## Components

The component language is "printed cell": a bordered field on paper, filled with one of three surfaces, separated by hairlines, addressed by a code.

### Buttons
- **Shape:** square (0px radius), 40px tall, 1px border in the fill colour, 18px horizontal padding, 8px icon gap.
- **Primary:** Enamel Blue field, white caps at 0.8125rem / 700 / 0.11em. Hover deepens to Deep Enamel (#0b2740) over 140ms.
- **Signal:** signal field with Tunnel Ink text, hover mixed 84% signal / 16% ink. Declared in the stylesheet as the reserved action variant; it is the only button allowed to use the lamp.
- **Quiet:** transparent with a Hairline Strong outline; hover fills Chalk Surface and the border darkens to Tertiary Ink.
- **On enamel:** transparent with a 42% white border, used in the masthead at 36px tall; hover lifts the fill to 12% white and the border to 70%.
- **Focus / Disabled:** `outline: 2px solid` at `2px` offset, colour `--focus` (enamel on paper, signal on enamel, ink on primary). Disabled drops to 0.45 opacity with a not-allowed cursor.

### The Rail Station
A rectangle, not a card. Grid of `36px 1fr auto` — pip, name, code — with 9px/14px padding on Platform Grey.
- **The drawn line:** each station owns its own segment (a 3px pseudo-element at 32% opacity in the line hue), so the diagram stays correct at any row count and never dangles past the first or last pip.
- **Pips:** 21px square ground with an 11px square outlined at 2px in the line hue. Active is a signal fill with an ink border and the word `HERE` in the code slot; visited fills the inner square with the line hue, so progress is legible at a glance.
- **States:** hover moves the row to 70% white and ink text; active moves it to Chalk Surface with a 700-weight name and a solid code in Tunnel Ink.
- **Motion:** on arrival the line draws itself down (420ms, staggered 60/140/220/300/360ms) and the active pip lands 320ms in. That is the only authored animation on the page; `prefers-reduced-motion` reduces it to 0.001ms.

### The Station Index Link
The retrieval node, printed. An 18px code column, then the label, with a 2px transparent left edge that becomes the active marker.
- **Address:** the section code in JetBrains Mono at 0.6875rem / 500 / 0.04em, tertiary ink.
- **Active:** the row fills Platform Grey, the name goes ink at 600, and the code inverts to a Tunnel Ink chip with paper text. The left edge becomes 2px ink — a marker, not a side stripe of colour.
- **Hover:** ink text, no fill. Focus is the global 2px outline.

### The Board Row
The repository directory, set as a departure board. Four columns — line swatch, destination, station count, updated — on a shared template (`5.5rem 1fr 6.5rem 8.5rem`) with 24px gaps, so the header labels sit exactly over the values they name.
- **Shape:** no radius, 1px hairline bottom, 17px/20px padding, transparent at rest.
- **Hover:** fills Chalk Surface and underlines the destination at 0.18em offset.
- **Below 1024px:** collapses to two columns with the line row spanning both, and the station list becomes a row of code tags instead of grid cells — never a horizontally scrolling board.

### The Code Cell
A timetable window inside the reading column.
- **Shape:** 1px Deep Enamel border, 0px radius, no shadow, 24px vertical margin.
- **Header:** Enamel Blue bar, 5px/12px padding, language name and copy control in label-wide caps at #c9dcec, separated from the body by a 1px #1e3a52 rule.
- **Body:** Timetable Night (#0d1c2b) with Timetable Chalk text, JetBrains Mono at 0.8125rem / 1.65, tab-size 2, horizontal scroll inside the window so the page never scrolls sideways.
- **Dark theme:** the field deepens to #070d11 and the header becomes the surface colour with a hairline border.

### The Tag
A printed stamp, never a pill. Inline-flex, 3px/7px padding, 1px Hairline Strong outline, 0.625rem / 600 / 0.13em caps, transparent fill by default.
- **Signal variant:** signal fill with Tunnel Ink text — used for the "Not connected" state, i.e. a status that genuinely asks for the reader.
- **No hover, no dismiss affordance:** a tag is information, not a control.

### The Masthead Nav
One 56px enamel row: a 14px square-in-square mark and the wordmark at 1.3125rem / 700 / 0.06em, three destinations, a theme toggle, and a 36px on-enamel button.
- **Links:** 56px tall, 0.8125rem / 600 / 0.13em caps at 74% white; hover and current go to full white, and current adds a 3px signal underline sitting 1px below the bar.
- **Dark theme** repoints the field to #1a4a72 and focus to signal, but the geometry is identical.
- **Narrow:** the link set scrolls beside the wordmark with short labels and a mask fade at the trailing edge; the bar never becomes two rows.

### The Route Strip
The colour field under the masthead, filled with the repository's line hue and white text, naming line → station → indexed node count. It is the only place the line hue fills a full-width band, and it is what tells a reader at a glance which line they entered.

### Named Rules
**The Cell-Not-Card Rule.** Containers are bordered cells on paper — hairline outline, square corners, no elevation. A card that floats above the page belongs to another product.

**The Next-Station Rule.** A reading page ends on previous/next station, not on a call to action. The primary action of a wiki page is the next thing to read, so it is never a button.

## Do's and Don'ts

### Do:
- **Do** hold the reading column at 64ch and move the side column out of the layout before the measure shrinks.
- **Do** name places, controls, and counts in Barlow Condensed caps; explain them in Source Serif 4; address them in JetBrains Mono.
- **Do** use `--line` / `--line-ink` through `data-line` for every repository hue, so light and dark modes both stay legible.
- **Do** give every generated page the same station skeleton — index head, numbered sections, previous/next — so a reader learns the shape once.
- **Do** build separation from 1px hairlines and field changes before reaching for any other device.
- **Do** keep motion to the one arrival moment plus 140ms state transitions and 240ms pip fills, and honour `prefers-reduced-motion`.
- **Do** reserve signal yellow for current location, keyboard focus, text selection, and a status that needs attention.
- **Do** preserve the focus outline at 2px with a 2px offset in every theme.

### Don't:
- **Don't** add `box-shadow`, `drop-shadow`, or any blur to imply elevation.
- **Don't** round a corner on any surface you set — not buttons, tags, pips, panels, or code cells. (The browser's own focus ring and native scrollbar are outside the rule.)
- **Don't** apply signal yellow as a hover fill on a control that was not already a signal field, as a heading accent, or as a decorative band.
- **Don't** invent a sixth line hue or hard-code a hue in markup; assignment is deterministic per repository.
- **Don't** use a gradient as a background fill; the only gradients permitted are the mask fades at the ends of scrollable strips.
- **Don't** put a heading's number into the authored markdown — the margin owns the address and prints it once.
- **Don't** turn the rail into a drawer, hamburger, or collapsed dropdown at any width.
- **Don't** set a rail or board station name, or a control label, in serif — and don't set a paragraph in condensed caps.
- **Don't** end a reading page with a primary button; the next station is the action.
- **Don't** let a code sample push the page sideways — it scrolls inside its own window.
