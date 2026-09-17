import fs from 'node:fs';
import vm from 'node:vm';

const read = p => fs.readFileSync(p, 'utf8');
const html = read('v2/index.html');
const css = read('v2/style.css');
const app = read('v2/app.js');
const dataJs = read('v2/story-data.js');

const fail = msg => { throw new Error(msg); };

for (const file of ['v2/style.css','v2/app.js','v2/story-data.js']) {
  if (!fs.existsSync(file)) fail(`Missing linked asset: ${file}`);
}

const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(m => m[1]);
const dupes = ids.filter((id,i) => ids.indexOf(id) !== i);
if (dupes.length) fail(`Duplicate ids: ${[...new Set(dupes)].join(', ')}`);

const requiredScenes = ['decisions','vulnerabilities','matrix','method','planning','workshops','deliverables','proof'];
for (const scene of requiredScenes) {
  if (!html.includes(`data-scene="${scene}"`)) fail(`Missing narrative scene: ${scene}`);
}

if (/TL;DR|Concertation<\/button>|data-view-target/i.test(html)) fail('Legacy multi-view UI still present in narrative v2');
if (/fictif/i.test(html + app + dataJs)) fail('Client-facing v2 still contains fictif wording');

const openBraces = (css.match(/\{/g) || []).length;
const closeBraces = (css.match(/\}/g) || []).length;
if (openBraces !== closeBraces) fail(`CSS brace mismatch: ${openBraces} vs ${closeBraces}`);

globalThis.window = {};
vm.runInThisContext(dataJs, { filename: 'story-data.js' });
const sources = globalThis.window.STORYSCRO?.sources || {};
const sourceKeys = [...html.matchAll(/data-source="([^"]+)"/g)].map(m => m[1]);
for (const key of sourceKeys) {
  if (key !== 'all' && !sources[key]) fail(`Unknown provenance key: ${key}`);
}

const contentSignals = ['De la vulnerabilite', 'Trois questions', 'Quatre vulnerabilites', '12 semaines', 'Pathways2Resilience'];
for (const signal of contentSignals) {
  if (!html.includes(signal) && !dataJs.includes(signal)) fail(`Missing source-grounded content signal: ${signal}`);
}

console.log(`StoryScro smoke OK: ${ids.length} unique ids, ${requiredScenes.length} narrative scenes, ${sourceKeys.length} source links.`);
