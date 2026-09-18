# StoryScro - Product decisions from 18 Sep 2026

This note records decisions made while reviewing the CCC 2025 StoryScro. It is subordinate to the project source of truth and does not change the milestone order unless explicitly stated.

## 1. Reading rhythm

A StoryScro scene should feel closer to a slide or an editorial frame than to an arbitrary position in a long web page.

- Short/non-scrolly scenes move semantically from scene to scene.
- Scroll-driven scenes remain fixed/sticky while their internal state changes.
- A reader should not be left in an accidental half-scene state.
- Internal scrollytelling must remain free to progress through states without CSS scroll snap fighting the scroll position.

Scene lifecycle remains:

ARRIVE -> SETTLE -> REVEAL -> HOLD -> TRANSITION -> EXIT.

## 2. Progressive emphasis

Underline, marker highlight and scroll highlight are semantic effects.

- They should draw progressively while the relevant scene is held.
- They should not be fully visible before the reader reaches the message.
- Key metrics may use scale, field inversion, contrast change or image/background change when that supports the meaning.
- A high-impact metric can be given a more cinematic treatment without changing the source claim.

## 3. Navigation

Keep:
- top-level chapter navigation;
- reading progress;
- right-side micro-navigation / scrubber;
- semantic scene labels.

Remove redundant visible up/down arrow buttons.

During prototype/training, expose the original source PDF in the top-right header whenever a source URL is available.

## 4. Source identity

When the source PDF has a coherent visual system, StoryScro should preserve its recognisable identity:
- palette;
- typography character;
- logos/publisher identity;
- chart/status colours;
- strong source visuals.

StoryScro changes narrative composition and motion, not brand identity by default.

## 5. Presentation profile

The Story Model now supports a compact presentation profile. The dimensions are:

- density: amount of information held in each scene;
- motion: global motion intensity;
- image_weight: importance of photography/source visuals;
- type_scale: global typography scale;
- compression: extensive -> TLDR/executive;
- contrast: strength of inversions and focal emphasis;
- source_identity: degree of fidelity to source visual identity.

Initial presets:
- source_faithful;
- consulting;
- executive;
- dynamic;
- cinematic;
- data_heavy;
- minimal.

A preset is a starting point, not a rigid template.

## 6. Mix and match

Longer term, a scene may have multiple valid visual variants while keeping the same:
- semantic message;
- factual content;
- evidence/provenance;
- transformation trail.

The editor/viewer should be able to show previous/next variants for a scene and allow the user to mark one as preferred. This enables combinations such as a restrained consulting opening with a cinematic key metric later in the same story.

The variant system must not create uncontrolled rewrites of facts.

## 7. Minimal editor

The editor is AI-first and deliberately shallow.

Useful direct controls:
- edit text;
- text size;
- text/accent colour;
- text/content position within safe zones;
- scene primitive;
- effect;
- effect intensity;
- replace image;
- hide/duplicate/reorder scene;
- choose/favourite a scene variant;
- inspect sources.

Do not build a Notion/Webflow/Canva clone.

## 8. Roadmap order

### NOW - Milestone 1: ANY PDF -> STORYSCRO

Still mandatory before declaring the engine proven:
- user-facing PDF upload/ingestion entry point;
- deterministic ingestion;
- evidence/provenance model;
- document understanding;
- Story Planner;
- Story Model generation;
- generic renderer;
- source-aware design extraction;
- semantic scene pacing;
- desktop/mobile QA;
- validation on several materially different PDFs;
- no document-specific recoding required for a credible result.

### NEXT - Milestone 2: formatting / views

- presentation profile selector before generation;
- source-faithful / consulting / executive / dynamic / cinematic / data-heavy / minimal views;
- audience-specific views;
- branded/confidential variants;
- same factual Story Model underneath.

### AFTER - Milestone 3: editor + preview

- minimal controls listed above;
- scene-level variants;
- mix-and-match/favourite workflow;
- clean PREVIEW mode separate from EDIT.

### THEN - Milestone 4: outputs

- publish interactive web;
- static print PDF derived from the validated Story Model and selected variants;
- hosting/publication choices.

### LATER

- SaaS/project/version/collaboration layer;
- business model and go-to-market;
- ChatGPT / MCP integration and equivalent invocation from other AI clients.

## 9. Immediate product rule

Do not delay Milestone 1 by building the full editor or SaaS. The next major proof remains: several unknown PDFs in, credible StoryScros out, with no document-specific front-end recoding.
