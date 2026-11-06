// run-feature-test.mjs: runs tools/feature-test.js in a real Chromium through Playwright, then loads the reloading variants (scene, skin, score
// version, the other pieces) and checks that each loads without a console error. Writes tools/feature-test-result.json and prints a summary.
//   needs Playwright (not a dependency of the project):  npx -y playwright@1 install chromium  then  node tools/run-feature-test.mjs
// The server must be running (./run.sh or node serve.mjs).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BASE = process.env.BASE || 'http://127.0.0.1:8410';
let chromium;
try { ({ chromium } = await import('playwright')); } catch { console.error('Playwright is not installed here; see the header of this file.'); process.exit(2); }
const browser = await chromium.launch(), page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
const errors = []; page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errors.push(`${page.url()} ${m.type()}: ${m.text()}`); });
page.on('pageerror', e => errors.push('pageerror ' + e.message));
const ready = () => page.waitForFunction(() => window.__stage && document.getElementById('loading').classList.contains('done'), null, { timeout: 90000 });
await page.goto(BASE + '/stage.html?gate=0&deck=1&info=1'); await ready();
await page.addScriptTag({ path: path.join(HERE, 'feature-test.js') });
const results = await page.evaluate(() => window.__featureTest());
for (const [q, check] of [['score=v1', 'v1'], ['mix=0', 'not level-calibrated'], ['scene=expanded', 'expanded'], ['ui=bar', 'legacy'], ['ui=0', 'nobar']]) {
  await page.goto(`${BASE}/stage.html?gate=0&t=30&${q}`); await ready(); await page.waitForTimeout(500);
  const v = await page.evaluate(async c => { if (c === 'legacy' || c === 'nobar') return document.body.classList.contains(c); if (c === 'expanded') return __stage.SCENE === 'expanded'; await __stage.setSound(true); await new Promise(r => setTimeout(r, 2500)); return document.getElementById('mode').textContent.includes(c === 'v1' ? 'first version' : c); }, check);
  results.push({ feature: 'reload variant ?' + q, control: 'deck Scene and skin / Sound version', ok: v, detail: check });
}
for (const u of ['index.html?standalone=1', 'index.html?slide1&standalone=1', 'index.html?classic&standalone=1', 'score/index.html', 'fx_measure.html']) {
  await page.goto(BASE + '/' + u); await page.waitForTimeout(6000);
  const n = await page.evaluate(() => document.querySelectorAll('#ac button, #ac a').length);
  results.push({ feature: 'page ' + u, control: u.startsWith('index') ? `strip (${n} controls)` : 'page', ok: true, detail: 'loaded' });
}
await browser.close();
fs.writeFileSync(path.join(HERE, 'feature-test-result.json'), JSON.stringify({ when: new Date().toISOString(), results, errors }, null, 1));
const bad = results.filter(r => !r.ok);
console.log(`${results.length - bad.length} of ${results.length} passed; console errors/warnings: ${errors.length}`);
for (const r of bad) console.log('FAIL', r.feature, '|', r.control, '|', r.detail);
for (const e of errors) console.log('CONSOLE', e);
process.exit(bad.length || errors.length ? 1 : 0);
