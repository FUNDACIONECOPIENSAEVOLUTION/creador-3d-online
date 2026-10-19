const { test } = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const path = require('node:path');
const { WebSocket } = require('ws');

test('Integración MCP: stdio ↔ websocket local, Origin y herramientas permitidas', { timeout: 25000 }, async () => {
  const port = 18765;
  const child = spawn(process.execPath, ['mcp-server.js'], {
    cwd: path.resolve(__dirname, '..'),
    env: { ...process.env, MCP_WS_PORT: String(port) },
    stdio: ['pipe', 'pipe', 'pipe']
  });
  let stderr = '';
  child.stderr.setEncoding('utf8');
  child.stderr.on('data', chunk => { stderr += chunk; });

  let nextId = 0;
  let partial = '';
  const pending = new Map();
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', chunk => {
    partial += chunk;
    let at;
    while ((at = partial.indexOf('\n')) >= 0) {
      const line = partial.slice(0, at);
      partial = partial.slice(at + 1);
      if (!line.trim()) continue;
      const packet = JSON.parse(line);
      if (!pending.has(packet.id)) continue;
      pending.get(packet.id)(packet);
      pending.delete(packet.id);
    }
  });
  async function call(method, params) {
    const id = ++nextId;
    const response = new Promise(resolve => pending.set(id, resolve));
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
    return await response;
  }
  function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
  let ws;
  try {
    // El servidor solo abre un puerto loopback, no una interfaz pública.
    for (let i = 0; i < 70 && !stderr.includes('WebSocket local escuchando'); i++) await sleep(100);
    assert.match(stderr, /127\.0\.0\.1/);

    const init = await call('initialize', { protocolVersion: '2024-11-05', capabilities: {} });
    assert.equal(init.result.serverInfo.version, '1.4.0');
    const listing = await call('tools/list', {});
    const names = listing.result.tools.map(x => x.name);
    assert.ok(names.includes('mcp_get_reference_image'));
    assert.ok(names.includes('mcp_animation_create'));
    assert.ok(names.includes('mcp_animation_keyframe'));
    assert.ok(names.includes('mcp_animation_commit'));
    assert.ok(names.includes('mcp_animation_pivot'));
    assert.ok(!names.some(name => /hunyuan|tripo|meshy/i.test(name)));
    assert.ok(names.includes('mcp_get_creation_brief'));
    assert.ok(names.includes('mcp_asset_build'));
    assert.ok(names.includes('mcp_asset_validate'));
    assert.ok(names.includes('mcp_asset_preset'));
    assert.ok(!names.includes('mcp_execute_three_code'));

    ws = new WebSocket('ws://127.0.0.1:' + port, {
      origin: 'https://fundacionecopiensaevolution.github.io'
    });
    await new Promise((resolve, reject) => {
      ws.once('open', resolve);
      ws.once('error', reject);
    });
    ws.on('message', payload => {
      const req = JSON.parse(payload.toString());
      ws.send(JSON.stringify({ jsonrpc: '2.0', id: req.id, result: { description: 'Ángel de ajedrez', rigRequired: true } }));
    });

    const brief = await call('tools/call', { name: 'mcp_get_creation_brief', arguments: {} });
    assert.equal(JSON.parse(brief.result.content[0].text).description, 'Ángel de ajedrez');

    const unsafe = await call('tools/call', {
      name: 'mcp_execute_three_code', arguments: { code: 'alert(1)' }
    });
    assert.equal(unsafe.result.isError, true);

    // Con Origin no autorizado el servidor rechaza la conexión.
    const malicious = new WebSocket('ws://127.0.0.1:' + port, {
      origin: 'https://untrusted.example'
    });
    const blocked = await new Promise(resolve => {
      malicious.once('error', () => resolve(true));
      malicious.once('open', () => resolve(false));
      malicious.once('unexpected-response', (_, response) => {
        response.resume();
        resolve(response.statusCode === 403);
      });
    });
    assert.equal(blocked, true);
    malicious.terminate();
  } finally {
    if (ws) ws.terminate();
    child.kill();
  }
});
