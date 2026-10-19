const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');

test('La página carga assets modulares', () => {
  const html = read('index.html');
  assert.match(html, /src="\.\/src\/studio\.js"/);
  assert.match(html, /href="\.\/styles\/studio\.css"/);
  assert.doesNotMatch(html, /<script type="module">[\s\S]+<\/script>/);
});
test('Módulo de personajes integra referencia, rig y animación', () => {
  const src = read('src/character-workflow.js');
  assert.match(src, /new THREE\.AnimationMixer/);
  assert.match(src, /getBrief\(\)/);
  assert.match(src, /getImage\(\)/);
  assert.match(src, /getExportClips\(\)/);
});
test('Se bloquea la ejecución remota de JavaScript', () => {
  const studio = read('src/studio.js');
  const server = read('mcp-server.js');
  assert.doesNotMatch(studio, /new Function\s*\(/);
  assert.doesNotMatch(server, /new Function\s*\(/);
  assert.doesNotMatch(server, /name:\s*['"]mcp_execute_three_code['"]/);
  assert.match(studio, /Ejecución arbitraria de JavaScript deshabilitada/);
});
test('Servidor local restringido con Origin', () => {
  const server = read('mcp-server.js');
  assert.match(server, /127\.0\.0\.1/);
  assert.match(server, /ALLOWED_ORIGINS\.has\(info\.origin\)/);
  assert.match(server, /mcp_get_reference_image/);
});
test('Los nombres del Outliner usan texto seguro', () => {
  const studio = read('src/studio.js');
  assert.match(studio, /label\.textContent/);
  assert.doesNotMatch(studio, /item\.innerHTML/);
});
