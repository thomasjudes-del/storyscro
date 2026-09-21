# StoryScro - Shorthand quality reference map

_Date: 2026-09-21_

Purpose: translate the strongest editorial/scrollytelling patterns observed in Shorthand reference stories into generic StoryScro planner/renderer rules. This is a benchmark, not a document-specific template and not an attempt to copy Shorthand implementation code.

## Reference stories reviewed

The benchmark review used Shorthand's own scrollytelling examples and support material, with particular attention to:

- EPFL - *L'impact du numérique sur les villes de l'Afrique de l'Ouest*: report-style narrative mixing photography, maps, graphs, workflows and prose.
- European Commission - *How EU laws are made*: minimalist institutional explainer using stepwise flow, short copy and restrained illustration.
- The Conversation - *The science of beautiful buildings*: data visualisation and diagrammatic progression used as the main explanatory device.
- Stuff - *The tale of two pandemics*: timeline + chart progression where counters and data update with the scroll.
- UCL Portico - *The Library of Lost Maps*: strong full-width media opening, reveal, map focus and disciplined pacing.
- Shorthand Reveal / Scrollmation / Chart guidance: full-screen media transitions, stepwise visual changes, text aligned with a specific visual state, and mobile-native fallbacks.

## What StoryScro should reproduce as a generic interaction grammar

### 1. One scene = one clear editorial frame

A scene should behave like an authored frame, not an arbitrary slice of a web page.

Quality gate:
- title + active evidence + visual must fit the viewport without collision;
- the reader should immediately know what to look at;
- avoid giant headings that leave no room for the evidence;
- use quiet frames between dense or highly animated scenes.

### 2. Scroll changes state, not just position

Good scrollytelling makes scrolling reveal a new explanatory state.

Generic states:
- ARRIVE
- SETTLE
- REVEAL
- HOLD
- TRANSITION
- EXIT

Examples of meaningful state change:
- chart series or annotation appears;
- map region is focused;
- layer is added/removed;
- key phrase is progressively highlighted;
- one method/process step replaces the previous one;
- image changes because the narrative moves to a new case or place.

### 3. Data should be narrated, not merely displayed

For quantitative evidence, select the chart from the analytical question.

- trend -> line/area;
- category comparison -> bar/dot;
- change between two states -> slope/delta;
- composition -> stacked bar / simple donut only when appropriate;
- exact values -> table;
- one decision-critical metric -> big number with comparison/context;
- geography -> map when spatial variation matters;
- timeline + metric -> scroll-linked timeline/chart.

A chart scene should have a message, source provenance and one or more progressive states. Do not put every number in oversized typography.

### 4. Text emphasis is an explanatory primitive

StoryScro should support:
- marker highlight;
- underline;
- accent-colour phrase;
- scroll-linked word/phrase highlight;
- pull quote;
- isolated statement;
- big number with context.

Emphasis is selected from semantic salience, not added decoratively. Normally one emphasis device per scene.

### 5. Media must be semantically relevant

Priority order:
1. strong source image/diagram/chart;
2. source visual transformed through crop, zoom, annotation or reveal;
3. externally sourced contextual media only when it clearly matches the topic and cannot be mistaken for source evidence;
4. clean graphic/no-image composition when relevance is uncertain.

Reject external media when search confidence is weak. A wrong atmospheric image is worse than no image.

### 6. Preserve source identity, improve composition

Default goal: recognisably related to the source, but stronger.

Extract and reuse when coherent:
- palette;
- logo/publisher identity;
- typography character and hierarchy;
- chart colours/status scales;
- recurring motifs;
- illustration/photography character.

StoryScro should improve:
- hierarchy;
- pacing;
- density;
- cropping;
- alignment;
- contrast;
- narrative sequencing;
- data-viz clarity.

It should not repaint every PDF into one generic StoryScro theme.

### 7. Vary primitives by semantic role

Variation should emerge from content:
- thesis -> full-screen statement;
- visual evidence -> text over media / reveal;
- process -> scrollmation / process flow;
- comparison -> side-by-side / progressive comparison;
- geographic relation -> map/scrollpoints;
- repeated categories -> mosaic;
- timeline -> timeline/Gantt;
- data -> chart;
- dense useful prose -> text section;
- evidence detail -> source drawer.

Do not vary layouts merely to avoid repetition.

### 8. Pacing and compression

Shorthand reference stories alternate copy, media, interactive evidence and breathing room.

Generic StoryScro rule:
- compress the source editorially before rendering;
- do not create one scene per PDF page or heading;
- avoid long stretches of identical cards;
- avoid long stretches of full-screen effects;
- keep the narrative length proportional to the information value of the source.

### 9. Mobile is a designed fallback, not desktop squeezed smaller

For each primitive define a mobile strategy:
- two-column scrollmation -> visual sticky above copy;
- wide chart -> simplified/small multiples or focused frames;
- dense map/network -> selected states rather than tiny whole view;
- large type -> fit to safe viewport budget;
- reveal -> native vertical scroll with portrait-safe media.

### 10. Source/provenance remains visible

Premium editorial quality must not break auditability. Every material claim/chart has:
- source evidence IDs;
- page/source refs;
- transformation trail;
- status when needed.

## Benchmark-derived quality gates for Milestone 1

A generated StoryScro is not ready for user acceptance if any of the following is true:

- chapter labels are structural noise, page numbers or truncated junk;
- hero is merely the PDF title on a generic background with no visual rationale;
- unrelated external image is used for atmosphere;
- source identity is lost without reason;
- title or active text collides/crops;
- a data-rich source becomes mostly big-number typography;
- chart type does not answer the underlying comparison/trend question;
- dense document becomes much longer without increasing comprehension;
- the same primitive repeats monotonously;
- mobile is only a scaled desktop scene;
- provenance cannot be inspected;
- planner output is mostly deterministic heading extraction rather than document understanding.

## Implication for current architecture

The public upload path should eventually be:

PDF -> deterministic ingestion/evidence -> AI document understanding/planner -> Story Model -> generic renderer.

The existing deterministic browser planner is useful as a fallback/smoke path, but it is not the target editorial reasoning layer for final Milestone 1 acceptance.
