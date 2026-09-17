# StoryScro - Project Instructions

## 1. Product vision

StoryScro transforms an arbitrary professional PDF into a high-quality interactive scrollytelling experience comparable in feel to strong Shorthand editorial stories, while preserving factual fidelity and source provenance.

The product is NOT a PDF-to-web reformatter and NOT a slide deck on a webpage. Its value is the editorial transformation: understand the source, identify the narrative structure, decide what deserves emphasis, select appropriate visual/interactive primitives, and build a coherent reading experience.

Longer-term, the same structured story should support multiple render targets, especially:
- interactive web StoryScro;
- static print PDF derived from the StoryScro composition, not from the original PDF.

Later, the same source/story model may support alternate themes, audience-specific views and an editor/preview workflow. These are NOT the current priority.

Repository: `thomasjudes-del/storyscro`
Current public demo: `https://thomasjudes-del.github.io/storyscro/`

## 2. Current milestone - Any PDF -> StoryScro

The only product milestone to solve now is:

> A user uploads an arbitrary PDF. StoryScro understands it, reconstructs its content and evidence, creates a structured Story Model, chooses suitable narrative primitives, and renders an interactive StoryScro with the visual/narrative quality of the current hand-built demo.

Do not distract the milestone with themes, SaaS billing, collaboration, advanced no-code editing, MCP packaging, authentication or PDF export yet. Keep their architectural compatibility in mind, but do not build them unless required by the ingestion/rendering architecture.

## 3. Definition of success for the milestone

The engine should work on at least 5 materially different PDFs, for example:
- consulting/proposal report;
- research/project deliverable;
- data-heavy report with charts/tables;
- institutional/public-sector report;
- visually rich report with images/diagrams.

For each PDF the generated StoryScro should:
1. preserve factual meaning;
2. not invent numbers, claims, references, conclusions or sources;
3. recover the document hierarchy and key messages;
4. identify useful data, images, tables, charts and evidence;
5. make an editorial selection rather than mechanically reproduce every page;
6. choose interaction patterns appropriate to the content;
7. expose provenance for claims/data/visuals;
8. work on desktop and mobile;
9. avoid layout overflow, broken assets and severe browser-console errors;
10. feel like a designed scrollytelling story, not a generated PowerPoint.

## 4. Core architecture

Use a clear pipeline:

`PDF -> Extraction -> Understanding -> Story Model -> Narrative Renderer -> StoryScro Web`

Future renderers may add:

`Story Model -> Print PDF`

The Story Model must become the canonical source of truth between understanding and rendering. The renderer must not depend on hard-coded content from the current demo.

### 4.1 Extraction layer

Recover as much source structure as reasonably possible:
- page number;
- headings and hierarchy;
- paragraphs;
- lists;
- captions;
- tables;
- figures/charts;
- embedded images;
- links/references/footnotes when accessible;
- bounding boxes or positional metadata when useful.

Keep the original PDF as immutable evidence.

### 4.2 Understanding / Story Planner

From the extracted source, identify:
- document purpose and audience;
- major sections and logical flow;
- key messages and conclusions;
- important numbers and comparisons;
- datasets or tabular structures;
- claims and supporting evidence;
- visual assets already present;
- content that can be condensed;
- content that should remain accessible as detail/appendix;
- candidate narrative sequences.

The system is allowed to summarize, reorder and visualize. It is not allowed to invent substantive facts.

### 4.3 Story Model

Represent the story in structured data, ideally JSON. Exact schema can evolve, but each scene should be addressable and renderer-independent.

A scene should be able to carry fields such as:
- `id`
- `chapter`
- `purpose`
- `message`
- `title`
- `body`
- `primitive`
- `visual`
- `interaction`
- `theme_hints`
- `sources[]`
- `transformations[]`
- `confidence/status`

Source metadata should be sufficiently precise to trace important content back to the PDF, e.g. file, page, section, figure/table, extracted value and transformation.

### 4.4 Provenance model

Distinguish:
- SOURCE: content explicitly present in the input;
- TRANSFORMATION: summarisation, reordering, aggregation, visual encoding;
- INTERPRETATION: analytical inference, only when explicitly allowed and visibly separated from sourced fact.

Every important number, claim, chart and conclusion should be auditable. If provenance cannot be established, mark it rather than pretending certainty.

## 5. Narrative primitive library

The current hand-built V0 demonstrates a useful starting grammar. Generalise it into reusable primitives instead of recreating bespoke HTML for every PDF.

Candidate primitives include:
- full-screen photographic hero;
- large statement / big number;
- sticky text + evolving background/visual;
- sticky multi-step scrollytelling;
- image parallax / zoom / pan;
- mosaic -> focus transition;
- progressive reveal;
- matrix / quadrant;
- timeline / phases;
- Gantt / schedule;
- network / stakeholder constellation;
- comparison;
- horizontal sequence;
- gallery / image sequence;
- quote / evidence break;
- chart / data visualisation;
- map when source data supports it;
- reference/proof scene;
- final synthesis.

Do not use effects because they exist. Choose them according to narrative function. Repetition should be controlled; rhythm and contrast matter.

## 6. Visual quality target

Target the editorial sensation of high-quality Shorthand/ICIS-style stories:
- full-screen composition;
- cinematic image use when relevant;
- layered depth;
- meaningful sticky sections;
- genuine scroll-driven state changes;
- controlled density;
- large typographic hierarchy;
- visual variety without gimmicks;
- transitions that support comprehension;
- strong mobile behaviour.

Avoid default SaaS/dashboard aesthetics, excessive cards, giant whitespace with little content, generic corporate PowerPoint layout, and explanatory UI copy that would never be shown to the end reader.

The final story should read as a client/public-facing deliverable, not as a test harness.

## 7. Assets

Images may come from the source PDF or from legitimately reusable external sources when editorially justified. Track origin/licensing metadata. For production, prefer controlled/local assets rather than fragile hotlinks. Do not use decorative images that misrepresent the source.

## 8. QA and development discipline

Development is iterative but must converge. For each meaningful change:
1. implement;
2. run structural/syntax tests;
3. render in a real browser/headless Chrome;
4. capture representative scenes;
5. inspect the captures;
6. fix visual defects;
7. test desktop and mobile;
8. verify GitHub Pages deployment.

Existing automated visual smoke tests should remain operational and evolve with the engine. Treat console errors, horizontal overflow, missing assets, clipped content and broken responsive behaviour as defects.

When a task is clear, execute it end-to-end without repeatedly asking for confirmation. Stop only for a genuine hard blocker, an irreversible/high-risk action, or missing information that materially changes the implementation.

## 9. Planned later stages - not now

After Any PDF -> StoryScro works reliably:

### Stage B - Formatting / view engine
Allow the same Story Model to be rendered with different editorial objectives or audiences, e.g. executive/TLDR, data-heavy, institutional, public, consultation, minimal, branded client, redacted/confidential.

### Stage C - Editor + Preview
AI-first editing with lightweight manual fine-tuning:
- edit text;
- replace image;
- change primitive/effect;
- effect intensity;
- reorder/hide/duplicate scene;
- modify density/theme;
- inspect source provenance;
- preview exactly what the reader will see;
- save variants.

Avoid building a full Webflow/Canva-style pixel editor unless real usage proves it necessary.

### Stage D - Outputs
- publish/export web;
- print PDF: a designed static adaptation of the generated StoryScro, preserving visual hierarchy and story structure while intelligently freezing interactive states.

### Stage E - Productisation
Potential ChatGPT App/MCP entry point, persistence, hosting/assets, collaboration, access control and SaaS features only after the core transformation quality is proven.

## 10. Development workflow / continuity

Primary workflow for now: continue developing from ChatGPT conversations with direct GitHub commits and automated tests. Codex may later be used for large, well-scoped engineering tasks, but product decisions and acceptance criteria remain grounded in this document and user feedback.

If a conversation loses context, reload this file first. Also inspect the current repository and the latest deployed build before proposing changes. Do not regress a working interaction merely because a new architecture is cleaner.

The immediate next engineering step is to decouple the current narrative demo from hard-coded content and make the renderer consume a generic Story Model. Then implement PDF ingestion/understanding that can generate that Story Model from unseen PDFs.