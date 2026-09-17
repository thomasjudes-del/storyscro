import fs from 'node:fs';

const readJson = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const fail = msg => { throw new Error(msg); };
const grammar = readJson('engine/narrative-grammar.json');
const schema = readJson('engine/story.schema.json');
const html = fs.readFileSync('v3/index.html','utf8');
const css = fs.readFileSync('v3/style.css','utf8');

if (!schema.$defs?.scene || !schema.$defs?.evidence) fail('Story schema missing core definitions');
if (!grammar.primitives || !grammar.effects) fail('Narrative grammar missing primitives/effects');

function validateStory(path) {
  const story = readJson(path);
  if (!Array.isArray(story.chapters) || !story.chapters.length) fail(`${path}: no chapters`);
  if (!Array.isArray(story.evidence) || !story.evidence.length) fail(`${path}: no evidence model`);

  const evidence = new Map(story.evidence.map(e => [e.id,e]));
  const assets = new Map((story.assets || []).map(a => [a.id,a]));
  const sceneIds = new Set();
  const usedAssetIds = new Map();
  let sceneCount = 0;
  let sourceRefCount = 0;
  let transformationCount = 0;

  for (const e of story.evidence) {
    if (!e.id || !e.status || !Array.isArray(e.source_refs) || !e.source_refs.length) fail(`${path}: invalid evidence ${e.id || '<missing id>'}`);
    for (const r of e.source_refs) {
      if (!r.file || !Number.isInteger(r.page) || r.page < 1) fail(`${path}: invalid source ref in evidence ${e.id}`);
      sourceRefCount++;
    }
  }

  for (const chapter of story.chapters) {
    if (!chapter.id || !chapter.title || !Array.isArray(chapter.scenes) || !chapter.scenes.length) fail(`${path}: invalid chapter ${chapter.id || '<missing id>'}`);
    for (const scene of chapter.scenes) {
      sceneCount++;
      if (!scene.id || sceneIds.has(scene.id)) fail(`${path}: duplicate/missing scene id ${scene.id}`);
      sceneIds.add(scene.id);
      if (!grammar.primitives[scene.primitive]) fail(`${path}: unknown primitive ${scene.primitive} in ${scene.id}`);
      if (!scene.semantic_role || !scene.message) fail(`${path}: scene ${scene.id} missing semantic role/message`);
      if (!Array.isArray(scene.source_evidence_ids) || !scene.source_evidence_ids.length) fail(`${path}: scene ${scene.id} has no evidence links`);
      for (const id of scene.source_evidence_ids) if (!evidence.has(id)) fail(`${path}: unknown evidence ${id} in ${scene.id}`);
      if (!Array.isArray(scene.transformations) || !scene.transformations.length) fail(`${path}: scene ${scene.id} has no transformation trail`);
      transformationCount += scene.transformations.length;
      if ((scene.effects || []).length > 2) fail(`${path}: scene ${scene.id} has more than two effects`);
      for (const effect of scene.effects || []) {
        if (!grammar.effects[effect.id] && !['line_by_line_fade','line_by_line_zoom','marker_highlight','scroll_highlight','full_screen_statement'].includes(effect.id)) fail(`${path}: unknown effect ${effect.id} in ${scene.id}`);
      }
      for (const m of scene.media || []) {
        if (!assets.has(m.asset_id)) fail(`${path}: unknown asset ${m.asset_id} in ${scene.id}`);
        const uses = usedAssetIds.get(m.asset_id) || [];
        uses.push(scene.id);
        usedAssetIds.set(m.asset_id, uses);
      }
      for (const r of scene.source_refs || []) {
        if (!r.file || !Number.isInteger(r.page) || r.page < 1) fail(`${path}: invalid scene source ref in ${scene.id}`);
        sourceRefCount++;
      }
    }
  }

  const repeated = [...usedAssetIds.entries()].filter(([,uses]) => uses.length > 1);
  if (repeated.length) console.warn(`${path} MEDIA_REUSE_WARNING`, repeated.map(([id,uses]) => `${id}:${uses.join('|')}`).join(', '));
  if (!story.navigation?.micro_navigation || !story.navigation?.reading_progress) fail(`${path}: navigation policy missing`);
  console.log(`${path} OK: ${story.chapters.length} chapters, ${sceneCount} scenes, ${story.evidence.length} evidence objects, ${sourceRefCount} source refs, ${transformationCount} transformations.`);
}

for (const path of ['v3/story.json','ccc-2025/story.json']) validateStory(path);

const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
const dupes = ids.filter((id,i) => ids.indexOf(id) !== i);
if (dupes.length) fail(`Duplicate shell ids: ${[...new Set(dupes)].join(', ')}`);
for (const linked of ['style.css','app.js']) if (!html.includes(linked)) fail(`v3 shell missing ${linked}`);
const openBraces = (css.match(/\{/g) || []).length;
const closeBraces = (css.match(/\}/g) || []).length;
if (openBraces !== closeBraces) fail(`CSS brace mismatch ${openBraces}/${closeBraces}`);
if (!html.includes('micro-nav') || !html.includes('chapter-nav')) fail('Generic navigation shell missing');
console.log('StoryScro generic smoke OK for all current test stories.');
