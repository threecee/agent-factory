#!/usr/bin/env node
// Lint ratchet for a stack with no linter installed — the package's ratchet
// contract in JavaScript: a committed PER-RULE baseline (.lint-baseline.json),
// exit 1 when any rule's finding count INCREASES over baseline or a new rule
// appears, `--update` as the ONLY path to a new baseline, `--report` prints and
// exits 0, and a MISSING baseline is a hard failure (never a silent pass).
//   node scripts/check_lint_ratchet.mjs            # exit 1 on regression
//   node scripts/check_lint_ratchet.mjs --report   # print, exit 0
//   node scripts/check_lint_ratchet.mjs --update   # rewrite the baseline
import { readFileSync, writeFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, relative } from 'node:path';
const ROOT = process.cwd();
const BASELINE = join(ROOT, '.lint-baseline.json');
const RULES = {
  'no-console': /^\s*console\.(log|debug)\(/,
  'no-todo': /\b(TODO|FIXME)\b/,
  'no-var': /^\s*var\s+/,
};
function* files(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) yield* files(p);
    else if (/\.(m?js|cjs)$/.test(name)) yield p;
  }
}
const counts = Object.fromEntries(Object.keys(RULES).map(r => [r, 0]));
const hits = [];
for (const f of files(join(ROOT, 'src'))) {
  readFileSync(f, 'utf8').split('\n').forEach((line, i) => {
    for (const [rule, re] of Object.entries(RULES)) if (re.test(line)) { counts[rule]++; hits.push(`${relative(ROOT, f)}:${i + 1} ${rule}`); }
  });
}
const mode = process.argv[2] ?? '--check';
if (mode === '--update') { writeFileSync(BASELINE, JSON.stringify(counts, null, 2) + '\n'); console.log(`[lint-ratchet] wrote ${relative(ROOT, BASELINE)}: ${JSON.stringify(counts)}`); process.exit(0); }
if (mode === '--report') { console.log(`[lint-ratchet] ${JSON.stringify(counts)}`); hits.forEach(h => console.log('  ' + h)); process.exit(0); }
if (!existsSync(BASELINE)) { console.log(`[lint-ratchet] HARD: ${relative(ROOT, BASELINE)} missing — generate it with --update (do NOT skip)`); process.exit(1); }
const base = JSON.parse(readFileSync(BASELINE, 'utf8'));
const regressions = Object.entries(counts).filter(([r, n]) => n > (base[r] ?? 0)).map(([r, n]) => `${r}: ${n} > baseline ${base[r] ?? 0}`);
if (regressions.length) { console.log(`[lint-ratchet] HARD: ${regressions.length} regression(s)`); regressions.forEach(r => console.log('  ' + r)); hits.forEach(h => console.log('  ' + h)); process.exit(1); }
console.log(`[lint-ratchet] ok ${JSON.stringify(counts)} (baseline ${JSON.stringify(base)})`);
