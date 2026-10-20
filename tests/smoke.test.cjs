const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');

test('La página carga assets modulares', () => {
  const html = read('index.html');
  assert.match(html, /src="\.\/src\/studio\.js(?:\?v=[\w.-]+)?"/);
  assert.match(html, /href="\.\/styles\/studio\.css(?:\?v=[\w.-]+)?"/);
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

test('El panel MCP nube permite desplazarse y copiar el mensaje con ID temporal', () => {
  const html = read('index.html');
  const css = read('styles/studio.css');
  const studio = read('src/studio.js');
  assert.match(html, /id="remote-room"[^>]+readonly/);
  assert.match(html, /copyRemoteChatGPTPrompt\(\)/);
  assert.match(css, /\.panel-left\s*\{[^}]*overflow-y:\s*auto/);
  assert.match(css, /\.panel-left\s*>\s*\.mcp-container\s*\{[^}]*overflow:\s*visible/);
  assert.match(studio, /copyRemoteChatGPTPrompt\(\)/);
  assert.match(studio, /this\.remoteRoomId/);
  assert.doesNotMatch(studio, /navigator\.clipboard\.writeText\(key\)/);
});

test('EcoBlend muestra permisos MCP dentro del editor, sin ventanas confirm en segundo plano',()=>{
  const html=read('index.html');
  const css=read('styles/studio.css');
  const studio=read('src/studio.js');
  assert.match(html,/id="mcp-approval-panel"/);
  assert.match(html,/onclick="app\.answerRemotePermission\(true\)"/);
  assert.match(html,/onclick="app\.answerRemotePermission\(false\)"/);
  assert.match(html,/id="remote-approve-scene"/);
  assert.match(studio,/queueRemotePermission\(packet,socket\)/);
  assert.match(studio,/answerRemotePermission\(approved\)/);
  assert.match(studio,/clearRemotePermissionQueue/);
  assert.match(studio,/La solicitud caducó sin respuesta/);
  assert.doesNotMatch(studio,/window\.confirm\(/);
  assert.match(css,/mcp-approval-panel\[hidden\]/);
  assert.match(css,/\.mcp-approval-panel\s*\{/);
  assert.match(studio,/document\.getElementById\('remote-approve-scene'\)\.checked=false/);
});
