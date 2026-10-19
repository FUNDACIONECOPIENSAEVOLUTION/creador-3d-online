#!/usr/bin/env node
'use strict';

/**
 * NeoBlender MCP local bridge v1.2
 *
 * stdio: MCP JSON-RPC (one JSON payload per line)
 * WebSocket: browser transport bound ONLY to 127.0.0.1.
 * Restrict Origin to the official GitHub Pages editor or localhost development.
 * No eval/new Function commands are exposed.
 *
 * Usage: npm install && npm run start-mcp
 */
const readline = require('node:readline');
const { WebSocketServer } = require('ws');

const HOST = '127.0.0.1';
const PORT = Number(process.env.MCP_WS_PORT || 8765);
const ALLOWED_ORIGINS = new Set([
  'https://fundacionecopiensaevolution.github.io',
  'http://localhost:5173', 'http://127.0.0.1:5173',
  'http://localhost:8000', 'http://127.0.0.1:8000'
]);
const MAX_MESSAGE = 12 * 1024 * 1024;

if (!Number.isInteger(PORT) || PORT < 1024 || PORT > 65535) {
  process.stderr.write('[EcoBlend] Puerto MCP_WS_PORT inválido.\n');
  process.exit(1);
}

const tools = [
  { name: 'mcp_get_scene_graph', description: 'Inspeccionar mallas, huesos, transformaciones y materiales de la escena.', inputSchema: { type: 'object', properties: {} } },
  { name: 'mcp_capture_viewport', description: 'Capturar vista actual (PNG).', inputSchema: { type: 'object', properties: {} } },
  { name: 'mcp_capture_quad_view', description: 'Capturar cuatro vistas de la escena (PNG).', inputSchema: { type: 'object', properties: {} } },
  { name: 'mcp_get_creation_brief', description: 'Obtener prompt, destino y requisitos del personaje solicitados en la web.', inputSchema: { type: 'object', properties: {} } },
  { name: 'mcp_get_reference_image', description: 'Recibir imagen de referencia previamente cargada por el usuario (JPEG).', inputSchema: { type: 'object', properties: {} } },
  {
    name: 'mcp_asset_validate',
    description: 'Validar plano 3D de partes de cualquier figura. No ejecuta código.',
    inputSchema: {
      type: 'object', required: ['blueprint'], properties: {
        blueprint: { type: 'object', description: 'EcoBlend ecoblend.asset.v1, nombre, categoría y partes' }
      }
    }
  },
  {
    name: 'mcp_asset_build',
    description: 'Construir geometría editable de criaturas, antropomorfos, objetos, vehículos o escenas desde un plano validado.',
    inputSchema: {
      type: 'object', required: ['blueprint'], properties: {
        blueprint: { type: 'object', description: 'Plano 3D declarativo generado por agente autorizado (no JavaScript)' }
      }
    }
  },
  {
    name: 'mcp_asset_preset',
    description: 'Crear una plantilla web abierta en ausencia de un plano detallado.',
    inputSchema: {
      type: 'object', required: ['id'],properties: {
        id:{type:'string',enum:['anthro-cat','dragon','robot','tree','chair','vehicle','castle']}
      }
    }
  },
  {
    name: 'mcp_character_create',
    description: 'Crear base humanoide o ángel articulado mediante geometría local libre, sin suscripciones ni modelos descargables.',
    inputSchema: {
      type: 'object',
      required: ['type'],
      properties: { type: { type: 'string', enum: ['humanoid', 'angel'] } }
    }
  },
  {
    name: 'mcp_set_quality',
    description: 'Seleccionar modo ligero/equilibrado/visual según capacidad gráfica del navegador.',
    inputSchema: {
      type: 'object',
      required: ['profile'],
      properties: { profile: { type: 'string', enum: ['low', 'balanced', 'high'] } }
    }
  },
  {
    name: 'mcp_animation_inspect',
    description: 'Inspeccionar huesos, clips y fotogramas de la pieza o personaje seleccionado.',
    inputSchema: { type: 'object', properties: {} }
  },
  {
    name: 'mcp_animation_create',
    description: 'Crear nueva acción para el modelo seleccionado o el rootUuid indicado.',
    inputSchema: {
      type: 'object',
      required: ['name', 'duration'],
      properties: {
        name: { type: 'string', minLength: 1, maxLength: 80 },
        duration: { type: 'number', exclusiveMinimum: 0, maximum: 60 },
        rootUuid: { type: 'string' }
      }
    }
  },
  {
    name: 'mcp_animation_keyframe',
    description: 'Posicionar un hueso o pieza por UUID y registrar pose animada en segundos.',
    inputSchema: {
      type: 'object',
      required: ['uuid', 'time'],
      properties: {
        uuid: { type: 'string' },
        time: { type: 'number', minimum: 0, maximum: 60 },
        position: { type: 'array', items: { type: 'number' }, minItems: 3, maxItems: 3 },
        rotationDeg: { type: 'array', items: { type: 'number' }, minItems: 3, maxItems: 3 },
        scale: { type: 'array', items: { type: 'number' }, minItems: 3, maxItems: 3 }
      }
    }
  },
  {
    name: 'mcp_animation_commit',
    description: 'Convertir poses a un AnimationClip compatible con GLB.',
    inputSchema: { type: 'object', properties: {} }
  },
  {
    name: 'mcp_animation_preset',
    description: 'Animar pieza entera con preset rigido idle/attack/defend/hit/defeat.',
    inputSchema: {
      type: 'object',
      required: ['kind'],
      properties: {
        kind: { type: 'string', enum: ['idle', 'attack', 'defend', 'hit', 'defeat'] },
        rootUuid: { type: 'string' }
      }
    }
  },
  {
    name: 'mcp_animation_play',
    description: 'Previsualizar clip existente y, opcionalmente, colocarlo en un instante concreto.',
    inputSchema: {
      type: 'object',
      required: ['name'],
      properties: {
        name: { type: 'string' }, rootUuid: { type: 'string' },
        time: { type: 'number', minimum: 0, maximum: 60 }
      }
    }
  },
  {
    name: 'mcp_animation_pivot',
    description: 'Crear pivote para malla separada; no asigna skinning automático.',
    inputSchema: {
      type: 'object',
      required: ['uuid', 'worldPosition'],
      properties: {
        uuid: { type: 'string' },
        name: { type: 'string', maxLength: 80 },
        worldPosition: { type: 'array', items: { type: 'number' }, minItems: 3, maxItems: 3 }
      }
    }
  },
  {
    name: 'mcp_spawn_pbr_mesh',
    description: 'Crear primitiva geométrica con material PBR. No crea automáticamente humanos realistas.',
    inputSchema: {
      type: 'object',
      properties: {
        type: { type: 'string', enum: ['box', 'sphere', 'cylinder', 'torusknot'] },
        name: { type: 'string', maxLength: 100 },
        color: { type: 'string', pattern: '^#[0-9a-fA-F]{6}$' },
        metalness: { type: 'number', minimum: 0, maximum: 1 },
        roughness: { type: 'number', minimum: 0, maximum: 1 },
        clearcoat: { type: 'number', minimum: 0, maximum: 1 },
        x: { type: 'number' }, y: { type: 'number' }, z: { type: 'number' }
      }
    }
  },
  {
    name: 'mcp_modify_object',
    description: 'Ajustar un objeto autorizado por nombre o UUID, sin ejecutar JavaScript arbitrario.',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string' }, uuid: { type: 'string' },
        position: { type: 'array', items: { type: 'number' }, minItems: 3, maxItems: 3 },
        scale: { type: 'array', items: { type: 'number' }, minItems: 3, maxItems: 3 },
        color: { type: 'string', pattern: '^#[0-9a-fA-F]{6}$' },
        metalness: { type: 'number', minimum: 0, maximum: 1 },
        roughness: { type: 'number', minimum: 0, maximum: 1 },
        transmission: { type: 'number', minimum: 0, maximum: 1 }
      }
    }
  }
];

const toolNames = new Set(tools.map(t => t.name));
const pending = new Map();
let browser = null;
let requestCounter = 0;
const wss = new WebSocketServer({
  host: HOST, port: PORT, maxPayload: MAX_MESSAGE,
  verifyClient: (info, done) => {
    const accepted = ALLOWED_ORIGINS.has(info.origin);
    if (!accepted) process.stderr.write('[EcoBlend] WebSocket Origin no autorizado: ' + String(info.origin) + '\n');
    done(accepted, accepted ? 200 : 403, accepted ? 'OK' : 'Origen no autorizado');
  }
});

wss.on('listening', () => process.stderr.write('[EcoBlend] WebSocket local escuchando en ws://' + HOST + ':' + PORT + '\n'));
wss.on('error', error => process.stderr.write('[EcoBlend] WS error: ' + error.message + '\n'));

function abortPending(reason) {
  for (const [, operation] of pending) {
    clearTimeout(operation.timer);
    operation.reject(new Error(reason));
  }
  pending.clear();
}

wss.on('connection', socket => {
  if (browser && browser.readyState === 1) {
    socket.close(1008, 'Solo se admite una pestaña conectada');
    return;
  }
  browser = socket;
  process.stderr.write('[EcoBlend] Visor conectado\n');
  socket.on('message', message => {
    try {
      const response = JSON.parse(message.toString());
      if (typeof response.id !== 'number' || !pending.has(response.id)) return;
      const op = pending.get(response.id);
      pending.delete(response.id);
      clearTimeout(op.timer);
      op.resolve(response);
    } catch (error) {
      process.stderr.write('[EcoBlend] Respuesta WS inválida: ' + error.message + '\n');
    }
  });
  socket.on('close', () => {
    if (browser !== socket) return;
    browser = null;
    abortPending('El visor web se ha desconectado.');
  });
});

async function forward(method, args) {
  if (!browser || browser.readyState !== 1) throw new Error('Abre el editor web y pulsa Conectar WS.');
  const id = ++requestCounter;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error('Tiempo de espera agotado: la pestaña no respondió.'));
    }, 20000);
    pending.set(id, { resolve, reject, timer });
    browser.send(JSON.stringify({ jsonrpc: '2.0', id, method, params: args }), error => {
      if (error && pending.has(id)) {
        const op = pending.get(id);
        pending.delete(id);
        clearTimeout(op.timer);
        reject(error);
      }
    });
  });
}

function reply(id, result, error) {
  const envelope = { jsonrpc: '2.0', id };
  if (error) envelope.error = { code: -32000, message: String(error.message || error) };
  else envelope.result = result;
  process.stdout.write(JSON.stringify(envelope) + '\n');
}

async function handle(request) {
  if (!request || request.jsonrpc !== '2.0') return;
  if (request.id === undefined) return; // Las notificaciones no llevan respuesta.
  const method = request.method;
  try {
    if (method === 'initialize') {
      reply(request.id, {
        protocolVersion: '2024-11-05',
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: 'ecoblend-mcp', version: '1.4.0' }
      }); return;
    }
    if (method === 'ping') { reply(request.id, {}); return; }
    if (method === 'tools/list') { reply(request.id, { tools }); return; }
    if (method !== 'tools/call') throw new Error('Método no permitido.');
    const name = request.params?.name;
    const args = request.params?.arguments || {};
    if (!toolNames.has(name)) throw new Error('Herramienta no autorizada: ' + String(name));
    if (!args || typeof args !== 'object' || Array.isArray(args)) throw new Error('Argumentos inválidos.');
    if (name === 'mcp_spawn_pbr_mesh' && args.type && !['box', 'sphere', 'cylinder', 'torusknot'].includes(args.type))
      throw new Error('Geometría no permitida.');
    if (name === 'mcp_asset_preset' && !['anthro-cat','dragon','robot','tree','chair','vehicle','castle'].includes(args.id))
      throw new Error('Plantilla de figura desconocida.');
    if (name === 'mcp_asset_validate' || name === 'mcp_asset_build') {
      const blueprint = args.blueprint;
      if (!blueprint || typeof blueprint !== 'object' || Array.isArray(blueprint) ||
          !Array.isArray(blueprint.parts) || blueprint.parts.length > 120 ||
          JSON.stringify(blueprint).length > 128*1024)
        throw new Error('Plano EcoBlend ausente o supera los límites de seguridad.');
    }
    if (name === 'mcp_character_create' && !['humanoid', 'angel'].includes(args.type))
      throw new Error('Plantilla de personaje no permitida.');
    if (name === 'mcp_set_quality' && !['low', 'balanced', 'high'].includes(args.profile))
      throw new Error('Perfil gráfico no permitido.');

    if (name === 'mcp_animation_create' &&
        (typeof args.name !== 'string' || !args.name.trim() || args.name.length > 80 ||
         typeof args.duration !== 'number' || !Number.isFinite(args.duration) || args.duration <= 0 || args.duration > 60))
      throw new Error('Nombre o duración no válidos para animación.');
    if (name === 'mcp_animation_keyframe' && (
        typeof args.uuid !== 'string' ||
        typeof args.time !== 'number' || !Number.isFinite(args.time) || args.time < 0 || args.time > 60 ||
        ['position', 'rotationDeg', 'scale'].some(key => args[key] !== undefined &&
          (!Array.isArray(args[key]) || args[key].length !== 3 || !args[key].every(Number.isFinite)))))
      throw new Error('Fotograma inválido: UUID, tiempo o vectores.');
    if (name === 'mcp_animation_preset' && !['idle', 'attack', 'defend', 'hit', 'defeat'].includes(args.kind))
      throw new Error('Preset no permitido.');
    if (name === 'mcp_animation_pivot' && (
        typeof args.uuid !== 'string' ||
        !Array.isArray(args.worldPosition) || args.worldPosition.length !== 3 ||
        !args.worldPosition.every(Number.isFinite)))
      throw new Error('Pivote no válido.');

    const response = await forward(name, args);
    if (response.error) {
      reply(request.id, { content: [{ type: 'text', text: response.error.message }], isError: true });
      return;
    }
    const value = response.result;
    if (name === 'mcp_capture_viewport' || name === 'mcp_capture_quad_view' || name === 'mcp_get_reference_image') {
      const mimeType = value?.mimeType;
      if (!['image/png', 'image/jpeg'].includes(mimeType)) throw new Error('Imagen de respuesta no válida.');
      const prefix = 'data:' + mimeType + ';base64,';
      if (typeof value.dataUrl !== 'string' || !value.dataUrl.startsWith(prefix))
        throw new Error('Datos de imagen mal formados.');
      reply(request.id, { content: [{ type: 'image', mimeType, data: value.dataUrl.slice(prefix.length) }] });
    } else {
      reply(request.id, { content: [{ type: 'text', text: JSON.stringify(value) }] });
    }
  } catch (error) {
    reply(request.id, { isError: true, content: [{ type: 'text', text: String(error.message || error) }] });
  }
}

readline.createInterface({ input: process.stdin, crlfDelay: Infinity }).on('line', line => {
  if (!line.trim() || line.length > 256 * 1024) return;
  try { void handle(JSON.parse(line)); }
  catch (error) { process.stderr.write('[EcoBlend] JSON stdio inválido: ' + error.message + '\n'); }
});
