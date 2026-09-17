# StoryScro v3 - Generic renderer

This directory is the first renderer driven by a renderer-independent `story.json` rather than hard-coded document content.

The current fixture intentionally reproduces the existing climate-strategy demo so that v2 and v3 can be compared while the architecture changes underneath.

Core contracts live in:

- `../engine/story.schema.json`
- `../engine/narrative-grammar.json`
- `../engine/PLANNER_RULES.md`

This is a milestone on the path to `ANY PDF -> Evidence Model -> Story Planner -> story.json -> StoryScro`, not a second visual theme.
