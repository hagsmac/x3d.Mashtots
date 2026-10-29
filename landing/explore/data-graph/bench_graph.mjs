// CPU cost of the graph acts' maths (what a WebGPU port would replace): Fiedler by shifted power iteration (300 steps, as the deck), PageRank (15 its), SVD-ish (6 x 200 power steps)
function bench(N, reps) {
  const W = Array.from({ length: N }, (_, i) => { const r = Array.from({ length: N }, (_, j) => i === j ? 0 : Math.exp(-((i - j) ** 2) / 50) + 0.01 * Math.random()); const s = r.reduce((a, b) => a + b, 0); return r.map(v => v / s); });
  const t0 = performance.now();
  for (let rep = 0; rep < reps; rep++) {
    const deg = W.map(r => r.reduce((a, b) => a + b, 0)), c = 2 * Math.max(...deg); let f = W.map((_, i) => Math.sin(i * 1.7));
    for (let it = 0; it < 300; it++) { const m = f.reduce((a, b) => a + b, 0) / N; f = f.map(v => v - m); const nf = new Array(N).fill(0); for (let i = 0; i < N; i++) { let s = (c - deg[i]) * f[i]; for (let j = 0; j < N; j++) s += W[i][j] * f[j]; nf[i] = s; } const n = Math.hypot(...nf); f = nf.map(v => v / n); }
    let r = new Array(N).fill(1 / N); for (let k = 0; k < 15; k++) { const nr = new Array(N).fill(0.15 / N); for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) nr[i] += 0.85 * r[j] * W[j][i]; r = nr; }
  }
  return (performance.now() - t0) / reps;
}
for (const [N, reps] of [[36, 200], [500, 2], [2000, 1]]) console.log(`N = ${N}: ${bench(N, reps).toFixed(N === 36 ? 3 : 0)} ms per Fiedler (300 power steps) + PageRank (15 iterations), plain JS on one core`);
