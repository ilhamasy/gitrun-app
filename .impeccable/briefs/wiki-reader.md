# Surface brief — GoWiki documentation reader + repository directory

Mode: **Read** (the wiki reader, directory, and home are surfaces where the visitor must understand
a repository; the two service pages are honest placeholders).

Audience: department engineers and new joiners tracing a service they inherited, plus hackathon
judges on a bright projector. Job: find the right section, trust it, and follow a citation back to
the exact place it came from. Action: read one page, then cite or leave for another section.

Proof on hand: two synthetic seeded wikis (`content/payment-gateway`, `content/auth-sentinel`) with
generated pages, a `toc.json` and a `pageindex_tree.json`. No testimonials, benchmarks, or
adoption numbers exist and none may be invented. Seed content is labelled a demo fixture.

Constraints: WCAG AA in both themes; keyboard-only operation of navigation; no network dependency
for browsing; server-side reads from `content/` are legitimate and stay.

## Direction contract

THESIS: A generated wiki is a transit line, and its station numbers are the retrieval tree. The page
refuses the category default — a neutral docs theme with a grey sidebar and rounded cards — by making
the navigation instrument itself carry the product's mechanism: a numbered line down the margin, a
"you are here" pip, a departure board instead of cards.

OWN-WORLD: Paper-white ground (#F4F4EF), near-black ink, an enamel-blue masthead that owns the top
field (#10365A), signal yellow reserved for the current station and focus only (#F5C518), one
assigned line hue per repository. Barlow Condensed for signage and labels in caps, Source Serif 4
for the reading column at 66ch, JetBrains Mono for station codes, node IDs, and code. Square
corners, 1px hairlines, 2px wayfinding rules, no shadows anywhere.

STORY: The reader sees which line they are on, which station they are reading, how many remain, and
the exact node that would be cited. They believe the wiki is generated and traceable rather than
hand-maintained, and they leave by the next station or another line.

FIRST VIEWPORT: Masthead (56px, enamel field) with the wordmark and three destinations; a route
strip beneath it naming the line, its station count, and the generation date; a 256px left rail
where the four pages hang as numbered stations on a drawn line with the active pip filled in signal
yellow; a 66ch reading column whose H1 is set in Barlow Condensed at 48px above a margin-numbered
station header; a 208px right rail carrying the station summary and the on-page station list. The
primary action is not a button — it is the next station, so the column ends on Previous/Next station
rather than a call to action.

FORM: At the top of my ordered list was a standards-body specification (highest product clarity);
the roll assigned transit wayfinding, 6th on the list, and it wins because the station number is the
retrieval node, so the world carries mechanism rather than reference. seed:29987ab13e4ba311

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the
verdict, DESIGN.md, and every shipping raster carrying its provenance
