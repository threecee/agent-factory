'use strict';
// Runtime import boundary (verify-portfolio "Runtime import boundary"): the
// production entry point must not load anything from the test family. The
// probe runs in a SUBPROCESS from this file's own location, so a worktree
// cannot inherit the primary checkout's resolution by accident.
//
// Falsified 2026-09-06: the first version matched 'NativeModule node:test' and
// stayed green with `require('node:test')` planted in src/ — Node lists the
// builtin as 'NativeModule test'. A boundary test that has never been red
// proves nothing (verification/falsification.md).
const test = require('node:test');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const path = require('node:path');
const ROOT = path.resolve(__dirname, '..');
test('src/hello.js loads nothing from test/ or the node:test builtin', () => {
  const entry = path.join(ROOT, 'src', 'hello.js');
  const testDir = path.join(ROOT, 'test') + path.sep;
  const probe = `require(${JSON.stringify(entry)});
    const loaded = Object.keys(require.cache).filter(k => k.startsWith(${JSON.stringify(testDir)}));
    const builtin = process.moduleLoadList.filter(m => m === 'NativeModule test' || m.startsWith('NativeModule internal/test_runner/'));
    console.log(JSON.stringify({ origin: require.resolve(${JSON.stringify(entry)}), loaded, builtin }));`;
  const out = JSON.parse(execFileSync(process.execPath, ['-e', probe], { cwd: ROOT, encoding: 'utf8' }));
  assert.equal(out.origin, entry, 'import root must be this tree');
  assert.deepEqual(out.loaded, [], 'test-family modules loaded by the production entry');
  assert.deepEqual(out.builtin, [], 'node:test loaded by the production entry');
});
