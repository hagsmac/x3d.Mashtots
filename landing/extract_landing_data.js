// Runs the ORIGINAL Landing math (attention, Fiedler, PageRank, message passing, SVD, k-means, DFT, layout, seed-405 flights, stars, motes)
// straight from MashtotsLanding.dc.html and dumps it as JSON, so the X3D generator bakes exactly what the JavaScript computes.
const fs = require('fs');
const src = fs.readFileSync('scratch/MashtotsLanding.dc.html', 'utf8');
const measure = JSON.parse(fs.readFileSync('scratch/measure40.json', 'utf8'));
let cls = src.slice(src.indexOf('class Component extends DCLogic'), src.indexOf('</script>', src.indexOf('class Component extends DCLogic')));
const cut = 'const start = performance.now(); let last = start; let lastGlyph = -1;';
if (!cls.includes(cut)) throw new Error('cut marker not found');
const names = ['P','slots','NG','GDT','DW','N','begin','stagger','flight','flightR','S','T1','TL','TT','TC','TW2','TS','DS','TS2','TB','DB','TB2','TM','TSP','TP','TA','TD','TD2','TWK','TF','TPC','TSV','TSV2','TH','T2','T3','CYCLE',
  'motes','HC','R','HH','F','RG','EMB','HULLS','STARS','A','FIED','lam2','PR','PRmax','PRtop','MSG','GD','SV','WK','WKmax','WKres','SVDXY','KM','ZS','ZK','src','row','veilBox','HM','SG','TV','GDP','Ws','deg','SENT','CLASSES'];
cls = cls.replace(cut, 'return {' + names.join(',') + '};\n' + cut);
const ctxStub = new Proxy({ measureText: (ch) => ({ width: (measure[ch] ?? 20) }) }, { get: (t, k) => (k in t ? t[k] : () => {}), set: () => true });
const factory = new Function('DCLogic', 'React', 'window', 'document', 'localStorage', cls + '\nreturn Component;');
const Component = factory(class {}, { createRef: () => ({ current: null }) }, { devicePixelRatio: 1, addEventListener() {} }, {}, {});
const c = new Component(); c.props = {}; c.attention = c.buildAttention();
c.canvasRef = { current: { width: 0, height: 0, getContext: () => ctxStub } };
// startCanvas returns the constants because of the injected return
const out = c.startCanvas();
// CLASSES holds colour arrays; the glyph table is DATA
out.DATA = c.DATA; out.ROWS = c.ROWS;
const flat = (k, v) => (v === Infinity ? 1e9 : v === -Infinity ? -1e9 : v);
fs.writeFileSync('scratch/landing.json', JSON.stringify(out, flat));
console.log('ok', Object.keys(out).length, 'keys; CYCLE', out.CYCLE.toFixed(3), 'NG', out.NG, 'T1', out.T1.toFixed(2), 'TT', out.TT.toFixed(2), 'TC', out.TC.toFixed(2), 'TW2', out.TW2.toFixed(2), 'TS2', out.TS2.toFixed(2), 'TH', out.TH.toFixed(2), 'T3', out.T3.toFixed(2));
