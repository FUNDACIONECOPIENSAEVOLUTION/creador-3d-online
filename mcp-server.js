#!/usr/bin/env node
/**
 * Servidor Puente MCP para Creador 3D Online
 * Repositorio: https://github.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online
 *
 * Conecta agentes MCP locales (Claude Desktop, Cursor, Windsurf, Cline) via stdio
 * con la pestaña abierta del navegador en ws://localhost:8765.
 */

const { WebSocketServer } = require('ws');
const readline = require('readline');

const WS_PORT = process.env.MCP_WS_PORT || 8765;
const wss = new WebSocketServer({ port: WS_PORT });

let activeBrowserSocket = null;
const pendingRequests = new Map();

wss.on('connection', (ws) => {
  activeBrowserSocket = ws;
  process.stderr.write(`[MCP-3D-Bridge] Navegador conectado en ws://localhost:${WS_PORT}\n`);

  ws.on('message', (data) => {
    try {
      const response = JSON.parse(data.toString());
      if (response.id && pendingRequests.has(response.id)) {
        const resolve = pendingRequests.get(response.id);
        pendingRequests.delete(response.id);
        resolve(response);
      }
    } catch (err) {
      process.stderr.write(`[MCP-3D-Bridge] Error parseando mensaje del navegador: ${err.message}\n`);
    }
  });

  ws.on('close', () => {
    if (activeBrowserSocket === ws) activeBrowserSocket = null;
    process.stderr.write('[MCP-3D-Bridge] Navegador desconectado.\n');
  });
});

function forwardToBrowser(method, params = {}) {
  return new Promise((resolve, reject) => {
    if (!activeBrowserSocket || activeBrowserSocket.readyState !== 1) {
      return reject(new Error('No hay ninguna pestaña de Creador 3D Online conectada a ws://localhost:' + WS_PORT));
    }
    const id = Date.now() + Math.floor(Math.random() * 1000);
    pendingRequests.set(id, resolve);
    activeBrowserSocket.send(JSON.stringify({ jsonrpc: '2.0', id, method, params }));

    setTimeout(() => {
      if (pendingRequests.has(id)) {
        pendingRequests.delete(id);
        reject(new Error('Timeout esperando respuesta del motor 3D en el navegador.'));
      }
    }, 10000);
  });
}

const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: false });

rl.on('line', async (line) => {
  if (!line.trim()) return;
  try {
    const req = JSON.parse(line);

    if (req.method === 'initialize') {
      process.stdout.write(JSON.stringify({
        jsonrpc: '2.0',
        id: req.id,
        result: {
          protocolVersion: '2024-11-05',
          capabilities: { tools: {} },
          serverInfo: { name: 'creador-3d-online-mcp', version: '1.1.0' }
        }
      }) + '\n');
      return;
    }

    if (req.method === 'tools/list') {
      process.stdout.write(JSON.stringify({
        jsonrpc: '2.0',
        id: req.id,
        result: {
          tools: [
            {
              name: 'mcp_get_scene_graph',
              description: 'Obtiene todos los objetos 3D, transformaciones y materiales PBR de la escena actual.',
              inputSchema: { type: 'object', properties: {} }
            },
            {
              name: 'mcp_capture_quad_view',
              description: 'Captura 4 vistas (Perspectiva, Frontal, Superior, Lateral) del modelo 3D en Base64 PNG para que la IA vea la geometría.',
              inputSchema: { type: 'object', properties: {} }
            },
            {
              name: 'mcp_spawn_pbr_mesh',
              description: 'Crea un objeto 3D hiperrealista con MeshPhysicalMaterial.',
              inputSchema: {
                type: 'object',
                properties: {
                  type: { type: 'string', enum: ['sphere', 'box', 'cylinder', 'torusknot'] },
                  name: { type: 'string' },
                  color: { type: 'string' },
                  metalness: { type: 'number' },
                  roughness: { type: 'number' },
                  clearcoat: { type: 'number' },
                  transmission: { type: 'number' },
                  ior: { type: 'number' },
                  x: { type: 'number' },
                  y: { type: 'number' },
                  z: { type: 'number' }
                }
              }
            },
            {
              name: 'mcp_execute_three_code',
              description: 'Ejecuta código Three.js directo en la escena (recibe THREE, scene, app).',
              inputSchema: {
                type: 'object',
                properties: { code: { type: 'string' } },
                required: ['code']
              }
            }
          ]
        }
      }) + '\n');
      return;
    }

    if (req.method === 'tools/call') {
      const toolName = req.params.name;
      const toolArgs = req.params.arguments || {};
      const browserRes = await forwardToBrowser(toolName, toolArgs);

      if (browserRes.error) {
        process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: req.id, error: browserRes.error }) + '\n');
      } else if (toolName === 'mcp_capture_quad_view' || toolName === 'mcp_capture_viewport') {
        const base64Data = browserRes.result.dataUrl.replace(/^data:image\/png;base64,/, '');
        process.stdout.write(JSON.stringify({
          jsonrpc: '2.0',
          id: req.id,
          result: {
            content: [{ type: 'image', data: base64Data, mimeType: 'image/png' }]
          }
        }) + '\n');
      } else {
        process.stdout.write(JSON.stringify({
          jsonrpc: '2.0',
          id: req.id,
          result: {
            content: [{ type: 'text', text: JSON.stringify(browserRes.result, null, 2) }]
          }
        }) + '\n');
      }
    }
  } catch (err) {
    process.stderr.write(`[MCP-3D-Bridge] Error: ${err.message}\n`);
  }
});
