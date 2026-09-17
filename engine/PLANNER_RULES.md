# StoryScro Narrative Planner Rules

## Purpose

The planner converts document understanding into a sequence of StoryScro scenes. It must choose structure, primitive and effects from meaning, not from a desire to maximise motion.

## Planning order

Always decide in this order:

1. What is the source actually saying?
2. What must the reader understand or decide?
3. What is the semantic role of this material?
4. Does the original PDF structure help or hinder that goal?
5. Which primitive makes the relationship easiest to understand?
6. Does motion add explanatory value?
7. If yes, choose the lightest effect that does the job.
8. Record source evidence and every material transformation.

Do not choose an effect first and then look for content to justify it.

## Editorial fidelity

StoryScro supports three narrative policies. This is not a visual theme. It controls how far the planner may depart from the source document's original organisation.

### faithful

- Preserve the original major section order.
- Preserve nearly all substantive content.
- Improve hierarchy, pacing, typography, media use and interaction.
- Suitable when the PDF structure is contractual, regulatory, politically sensitive or already editorially strong.

### adaptive (default)

- Preserve every material fact, conclusion and piece of evidence.
- May merge repetitive sections, move supporting material, promote conclusions earlier and compress low-value prose.
- Keep a transformation trail for every structural change.
- Suitable for most professional reports.

### restructured

- Rebuild the story around the central question, messages and evidence rather than the PDF's section order.
- May reduce five source chapters to two narrative chapters, or split one dense source chapter into several scenes.
- Must not create new factual claims.
- Use only when the source organisation materially weakens comprehension.

## Scene selection rules

### Opening

Use `hero` when the document has a clear title, thesis or contextual visual. Use a full-screen image or muted background video only when it supports the topic. A hero should not become a mini executive summary.

### Thesis / key turn

Use `full_screen_statement` for one important idea that deserves pause. It is also the preferred breathing scene after a visually dense or data-heavy sequence.

Text emphasis can include one highlighted phrase, accent colour, underline or scroll-linked marker highlight. Highlighting should reveal hierarchy, not decorate every paragraph.

### Dense prose

Use `text_section`. Do not punish useful prose by forcing it into animation. Editorial quality includes quiet reading zones.

### Stepwise reasoning

Use `scrollmation` when text steps correspond to visible changes in one stable visual context. Examples: methodology, mechanism, decision sequence, progressive diagram or evolving chart.

Use `background_scrollmation` when the changing full-screen media is itself part of the evidence or story, for example places, cases, photographic evidence or visual states.

### Same object, different states

Use `reveal` for before/after, added/removed layers, alternative scenarios or sequential states of the same visual. Appropriate transitions are fade or directional wipes. Hard cuts are better for frame animation where intermediate blending would create flicker.

### Overview to detail

Use `scrollpoints` for maps, large images, complex diagrams and charts where the reader needs to retain overall context while zooming or panning to specific features.

### Quantitative evidence

Ask the analytical question first.

- Trend over time -> line / area chart.
- Compare categories -> bar / dot / small multiples.
- Composition -> stacked bar, pie/donut only for simple part-to-whole cases.
- Distribution -> dot, histogram, box/other specialised chart if justified.
- Flow -> Sankey / process flow if the source contains actual flows.
- Exact lookup -> data table.
- One decision-critical value -> big number with context.

Animation may reveal series, annotations or states progressively. Never animate simply because a chart exists.

### Time and planning

Use `timeline` for events and milestones. Use `gantt` when tasks have durations or overlap. Do not infer dates or durations.

### Prioritisation

Use `matrix` only when there are meaningful axes. If axes or point locations are qualitative transformations rather than source measurements, label that explicitly in provenance.

### Geography

Use `map` only when location or spatial variation changes the interpretation. Do not use maps as decorative territory icons.

### Stakeholders

Use `network` only when source evidence supports relationships. If the document merely lists actors, prefer a grouped list, process role map or mosaic instead of inventing edges.

### Parallel categories / cases

Use `mosaic`, `grid` or `gallery` for a small bounded set of peers. Preserve hierarchy if some cases are more important than others.

## Motion policy

Motion levels:

- LOW: fades, subtle depth, focus shifts, restrained parallax.
- MEDIUM: pan/zoom, progressive build, sticky steps, horizontal sequence, path drawing.
- HIGH: flipbook/frame animation or substantial scene transformation.

Rules:

- Normally one primary effect plus at most one subtle secondary effect per scene.
- Avoid consecutive HIGH-motion scenes.
- Insert quiet sections after dense data or highly animated sequences.
- Effects must remain understandable when motion is disabled.
- Respect `prefers-reduced-motion` and render stable final states.

## Directional transitions

Directional wipes have semantic meaning when possible:

- left/right: comparison, replacement, movement through alternatives or timeline direction;
- up/down: layer addition/removal, vertical hierarchy or progressive build;
- fade: context changes without meaningful direction;
- hard cut: discrete frame states or technical animation.

Do not use arbitrary alternating directions simply for variety.

## Text emphasis

StoryScro should support more than bold text.

Allowed emphasis patterns:

- accent-colour word or phrase;
- underline;
- marker highlight;
- scroll-linked highlight that progresses with reading;
- line-by-line fade or blur-to-focus;
- pull quote;
- isolated full-screen sentence;
- big number.

The planner should identify a small number of phrases with high semantic salience. Do not highlight every sentence.

## Media policy

- Prefer useful source images, diagrams and charts.
- External royalty-free/contextual imagery is allowed when it establishes atmosphere or context without pretending to be evidence from the source.
- Never reuse the same image in one story by default.
- Detect perceptual near-duplicates and reject them unless the scene is intentionally a before/after or layer sequence.
- Background video is allowed: muted, looped, with a still fallback and a mobile-safe treatment.
- Foreground video can have controls and sound.
- Important factual information must never exist only inside a video.

## Navigation

The Story Model exposes semantic anchors at chapter and scene level.

The renderer should support:

- overall reading progress;
- major chapter navigation;
- a StoryScro micro-navigation rail on desktop;
- chapter markers plus nested significant-scene dots;
- active chapter/scene label;
- previous/next buttons;
- keyboard navigation with up/down or page keys when it does not interfere with native scrolling;
- a compact mobile equivalent.

Navigation must jump to semantic scene anchors, not fixed pixel positions.

## Pacing

A strong story alternates:

- orientation;
- reading;
- visual evidence;
- interaction;
- synthesis;
- breathing room.

Do not produce twenty consecutive full-screen effects. Do not produce twenty consecutive white cards either.

The planner should calculate a rough motion/density profile for the whole story and reject monotonous sequences.

## Provenance

Every scene must reference the evidence IDs it depends on.

Every transformation must be recorded as one or more of:

- paraphrase;
- shorten;
- reorder;
- group;
- aggregate;
- visualize;
- restructure;
- translate.

If a visual relationship is not explicitly sourced, either mark it as a transparent qualitative transformation or do not draw it.

## Mobile

Every interactive primitive needs an explicit mobile strategy.

Examples:

- horizontal track -> snap/stack or controlled horizontal scene;
- large map -> zoom/pan with readable labels or static selected views;
- two-column scrollmation -> sticky visual above text or inline selected frames;
- dense network -> simplified groups rather than tiny nodes;
- wide Gantt -> scaled/scrollable overview plus focused milestones.

Do not assume desktop CSS shrinking is an acceptable mobile experience.

## Technical implementation

The renderer can implement the grammar with normal web technologies:

- `position: sticky` for pinned scrollytelling stages;
- `IntersectionObserver` and scroll progress for semantic triggers;
- CSS transforms, opacity, filters, clip-path and masks for transitions;
- SVG for paths, timelines, networks, maps and most charts;
- Canvas/WebGL only when data volume or rendering complexity requires it;
- native `<video>` for background and foreground video;
- D3 or purpose-built SVG modules for specialised data visualisation;
- accessible HTML as the underlying content layer.

StoryScro should reproduce the interaction grammar, not copy Shorthand proprietary implementation code.
