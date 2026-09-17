# StoryScro

StoryScro transforms a static professional report into a source-grounded, scroll-driven narrative experience.

Public demo: https://thomasjudes-del.github.io/storyscro/

The current build deliberately focuses on one narrative experience: full-screen visual chapters, sticky scroll scenes, progressive data revelation, horizontal sequences, animated planning and source provenance.

## Structure

- `v2/` current narrative engine and public experience
- `scripts/smoke.mjs` structural and provenance checks
- `scripts/visual_capture.py` headless scene-by-scene visual validation
- `.github/workflows/smoke.yml` automated structural smoke test
- `.github/workflows/visual-smoke.yml` automated desktop rendering and screenshot capture
- GitHub Pages deployment is handled by the repository's native Pages workflow
