/**
 * EcoBlend Remote MCP Pilot, Cloudflare Workers + Durable Objects.
 * Stateless MCP over HTTPS; short-lived, random room IDs; browser approves
 * EVERY operation, including scene reads and screenshots. No secrets in repo.
 *
 * This is a private TEST gateway, not general-purpose multi-tenant OAuth auth.
 * For public multi-user deployment, implement OAuth 2.1 and resource isolation.
 */
export const PROTOCOL = "2025-06-18";
export const ROOM_TTL_MS = 20 * 60 * 1000;
export const SUPPORTED_ORIGINS = new Set([
  "https://fundacionecopiensaevolution.github.io",
  "http://localhost:5173",
  "http://localhost:8000",
  "http://127.0.0.1:8000"
]);
const ROOM_PATTERN = /^([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})\.(\d{13})\.([a-zA-Z0-9_-]{43})$/i;
const MAX_JSON = 135 * 1024;
const BLUEPRINT_FORMAT = {
  version:"ecoblend.asset.v1",
  categories:["human","anthropomorphic","animal","creature","robot","vehicle","building","prop","abstract","other"],
  shapes:["box","sphere","cylinder","cone","capsule","torus","mesh"],
  limits:{partsMax:120,customVerticesPerPart:3000,customTrianglesPerPart:6000},
  required:["version","name","category","parts"],
  partFields:["id","parent","kind","shape","name","position","rotationDeg","scale","color","metalness","roughness","vertices","faces"],
  conventions:"parts es una lista ordenada; los padres deben declararse antes que sus hijos. kind=mesh o joint; los materiales usan colores hexadecimales #RRGGBB. Coordenadas XYZ y rotaciones en grados.",
  minimalExample:{
    version:"ecoblend.asset.v1",name:"FiguraDePrueba",category:"prop",
    parts:[{id:"cuerpo",kind:"mesh",shape:"sphere",position:[0,1,0],scale:[1,2,1],color:"#a6bed0"}]
  },
  shortcut:"Para obtener inmediatamente una figura 3D, usa ecoblend_preset con id guardian-pawn, sin redactar blueprint.",
  validationSteps:"Llama a ecoblend_blueprint_format para conocer el formato; ecoblend_validate_blueprint para validar; después ecoblend_build_blueprint para crear; confirma con ecoblend_scene y ecoblend_quad_view."
};


const encoder=new TextEncoder();
function base64url(array){
  let value='';
  for(const byte of new Uint8Array(array))value+=String.fromCharCode(byte);
  return btoa(value).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}
async function roomSignature(secret,room,expires){
  const key=await crypto.subtle.importKey('raw',encoder.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  return base64url(await crypto.subtle.sign('HMAC',key,encoder.encode(room+'.'+expires)));
}
function equalStrings(a,b){
  if(typeof a!=='string'||typeof b!=='string'||a.length!==b.length)return false;
  let diff=0;
  for(let i=0;i<a.length;i++)diff|=a.charCodeAt(i)^b.charCodeAt(i);
  return diff===0;
}
async function verifiedRoom(secret,room){
  const match=typeof room==='string'?room.match(ROOM_PATTERN):null;
  if(!match||typeof secret!=='string'||secret.length<24)return false;
  const expiry=Number(match[2]);
  if(expiry<Date.now()||expiry>Date.now()+ROOM_TTL_MS+60000)return false;
  const expected=await roomSignature(secret,match[1],expiry);
  return equalStrings(expected,match[3]);
}
function allowedOrigin(request){return SUPPORTED_ORIGINS.has(request.headers.get('Origin'));}
function cors(request){const origin=request.headers.get('Origin');return allowedOrigin(request)?{
  'Access-Control-Allow-Origin':origin,
  'Access-Control-Allow-Methods':'POST, OPTIONS',
  'Access-Control-Allow-Headers':'Authorization, Content-Type',
  Vary:'Origin'
}:{};}


const tools = [
  { name:"ecoblend_blueprint_format", description:"Mostrar la versión y un ejemplo exacto de blueprint JSON admitido: version ecoblend.asset.v1, name, category, parts. No modifica escena. Para el primer peón usa ecoblend_preset id guardian-pawn.", inputSchema:{type:"object",required:["room"],properties:{room:{type:"string"}}},annotations:{readOnlyHint:true}},
  { name:"ecoblend_scene", description:"Consultar grafo y geometría de la escena EcoBlend, previa aprobación en el navegador.", inputSchema: {type:"object",required:["room"],properties:{room:{type:"string"}}}, annotations:{readOnlyHint:true}},
  { name:"ecoblend_progress", description:"Ver un mosaico de los últimos avances renderizados después de crear o modificar el modelo (no es vídeo en vivo).", inputSchema:{type:"object",required:["room"],properties:{room:{type:"string"}}},annotations:{readOnlyHint:true}},
  { name:"ecoblend_feedback", description:"Leer correcciones escritas en EcoBlend por el usuario mientras la IA trabaja.",inputSchema:{type:"object",required:["room"],properties:{room:{type:"string"}}},annotations:{readOnlyHint:true}},
  { name:"ecoblend_quad_view", description:"Obtener captura de cuatro vistas 3D, previa aprobación en el navegador.", inputSchema: {type:"object",required:["room"],properties:{room:{type:"string"}}}, annotations:{readOnlyHint:true}},
  { name:"ecoblend_creation_brief", description:"Leer el encargo de creación 3D actual, previa aprobación del usuario.", inputSchema: {type:"object",required:["room"],properties:{room:{type:"string"}}}, annotations:{readOnlyHint:true}},
  { name:"ecoblend_reference_image", description:"Leer la imagen de referencia cargada; el navegador pedirá autorización específica.", inputSchema: {type:"object",required:["room"],properties:{room:{type:"string"}}}, annotations:{readOnlyHint:true}},
  { name:"ecoblend_modify_part", description:"Ajustar un objeto o articulación existente sin volver a construir toda la figura: posición, rotación, escala y material PBR. Se requiere UUID o nombre del objeto.", inputSchema:{type:"object",required:["room"],properties:{
    room:{type:"string"},uuid:{type:"string"},name:{type:"string"},
    position:{type:"array",items:{type:"number"},minItems:3,maxItems:3},
    rotationDeg:{type:"array",items:{type:"number"},minItems:3,maxItems:3},
    scale:{type:"array",items:{type:"number"},minItems:3,maxItems:3},
    color:{type:"string",pattern:"^#[0-9a-fA-F]{6}$"},
    metalness:{type:"number",minimum:0,maximum:1},
    roughness:{type:"number",minimum:0,maximum:1},
    transmission:{type:"number",minimum:0,maximum:1}
  }}, annotations:{destructiveHint:false,readOnlyHint:false}},
  { name:"ecoblend_preset", description:"Crear una figura de catálogo mediante un comando tipado que el usuario aprobará.", inputSchema: {type:"object",required:["room","id"],properties:{room:{type:"string"},id:{type:"string",enum:["anthro-cat","dragon","robot","tree","chair","vehicle","castle","guardian-pawn"]}}}, annotations:{destructiveHint:false,readOnlyHint:false}},
  { name:"ecoblend_validate_blueprint", description:"Validar blueprint EXACTO ecoblend.asset.v1 con name, category y parts. Si no conoces el formato llama antes a ecoblend_blueprint_format. No modifica escena.", inputSchema: {type:"object",required:["room","blueprint"],properties:{room:{type:"string"},blueprint:{type:"object"}}}, annotations:{readOnlyHint:true}},
  { name:"ecoblend_build_blueprint", description:"Construir geometría desde blueprint version ecoblend.asset.v1, name, category, parts. Validar antes con ecoblend_validate_blueprint. Para figura inmediata usa ecoblend_preset guardian-pawn.", inputSchema: {type:"object",required:["room","blueprint"],properties:{room:{type:"string"},blueprint:{type:"object"}}}, annotations:{destructiveHint:false,readOnlyHint:false}},
  { name:"ecoblend_animation_inspect", description:"Inspeccionar articulaciones y animaciones, previa aprobación.", inputSchema: {type:"object",required:["room"],properties:{room:{type:"string"}}}, annotations:{readOnlyHint:true}},
  { name:"ecoblend_animation_preset", description:"Aplicar animación básica al modelo seleccionado previa confirmación.", inputSchema: {type:"object",required:["room","kind"],properties:{room:{type:"string"},kind:{type:"string",enum:["idle","attack","defend","hit","defeat"]}}}, annotations:{destructiveHint:false,readOnlyHint:false}}
];
const TOOL_MAP = {
  ecoblend_blueprint_format:"mcp_asset_blueprint_format",
  ecoblend_scene:"mcp_get_scene_graph",
  ecoblend_progress:"mcp_capture_progress",
  ecoblend_feedback:"mcp_get_feedback",
  ecoblend_quad_view:"mcp_capture_quad_view",
  ecoblend_creation_brief:"mcp_get_creation_brief",
  ecoblend_reference_image:"mcp_get_reference_image",
  ecoblend_modify_part:"mcp_modify_object",
  ecoblend_preset:"mcp_asset_preset",
  ecoblend_validate_blueprint:"mcp_asset_validate",
  ecoblend_build_blueprint:"mcp_asset_build",
  ecoblend_animation_inspect:"mcp_animation_inspect",
  ecoblend_animation_preset:"mcp_animation_preset"
};

function json(body,status=200,extra={}) {
  return new Response(JSON.stringify(body),{
    status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store",
      "X-Content-Type-Options":"nosniff",...extra}
  });
}
const fault=(id,code,message)=>({jsonrpc:"2.0",id:id??null,error:{code,message}});
const ok=(id,result)=>({jsonrpc:"2.0",id,result});
const badRoom=room=>typeof room!=="string"||!ROOM_PATTERN.test(room);
function validArgs(name,args) {
  if(!args||typeof args!=="object"||Array.isArray(args)||badRoom(args.room))throw new Error("ID de sala inválido.");
  if(name==="ecoblend_modify_part"){
    if(!([args.name,args.uuid].some(v=>typeof v==="string"&&v.trim().length>0)))
      throw new Error('Indica el nombre o UUID de una pieza.');
    if(!['position','scale','rotationDeg','color','metalness','roughness','transmission'].some(k=>args[k]!==undefined))
      throw new Error('Indica al menos un ajuste.');
  }
  if(name==="ecoblend_preset" && !["anthro-cat","dragon","robot","tree","chair","vehicle","castle","guardian-pawn"].includes(args.id))throw new Error("Plantilla desconocida.");
  if(name==="ecoblend_animation_preset" && !["idle","attack","defend","hit","defeat"].includes(args.kind))throw new Error("Movimiento no permitido.");
  if(["ecoblend_validate_blueprint","ecoblend_build_blueprint"].includes(name)){
    const blueprint=args.blueprint;
    if(!blueprint||typeof blueprint!=="object"||Array.isArray(blueprint))
      throw new Error("El plano 3D debe ser un objeto JSON. Consulta ecoblend_blueprint_format.");
    if(blueprint.version!==BLUEPRINT_FORMAT.version)
      throw new Error("Versión de plano incompatible. Se requiere version: ecoblend.asset.v1. Consulta ecoblend_blueprint_format.");
    if(typeof blueprint.name!=="string"||!BLUEPRINT_FORMAT.categories.includes(blueprint.category)
      ||!Array.isArray(blueprint.parts)||!blueprint.parts.length||blueprint.parts.length>120)
      throw new Error("Plano inválido: necesitas name, category reconocida y parts de 1 a 120 componentes. Consulta ecoblend_blueprint_format.");
  }
}
function simplifyArgs(name,args){
  const clean={...args};
  delete clean.room;
  return clean;
}
function mcpContent(name,result){
  if(["ecoblend_quad_view","ecoblend_reference_image","ecoblend_progress"].includes(name)){
    if(!result || !["image/jpeg","image/png"].includes(result.mimeType) ||
      typeof result.dataUrl!=="string")throw new Error("Imagen inválida.");
    const base="data:"+result.mimeType+";base64,";
    if(!result.dataUrl.startsWith(base))throw new Error("Formato de imagen inválido.");
    return {content:[{type:"image",mimeType:result.mimeType,data:result.dataUrl.slice(base.length)}]};
  }
  return {content:[{type:"text",text:JSON.stringify(result)}]};
}
export default {
  async fetch(request,env) {
    const url=new URL(request.url);
    if(url.pathname==="/health" && request.method==="GET")
      return json({service:"ecoblend-remote-mcp",version:"0.2.0",mode:"temporary-room",mcp:"/mcp",features:["ecoblend_blueprint_format","guardian-pawn","ecoblend_progress","ecoblend_modify_part"]});

    // Creating a session requires a server-side secret known only to the owner.
    // This credential is never stored in GitHub or sent to ChatGPT.
    if(url.pathname==="/pair"){
      if(request.method==='OPTIONS')return new Response(null,{
        status:allowedOrigin(request)?204:403,headers:cors(request)
      });
      if(request.method!=='POST')return new Response('Method not allowed',{status:405});
      if(!allowedOrigin(request))return new Response('Forbidden origin',{status:403});
      if(typeof env.ECOBLEND_PILOT_KEY!=='string'||env.ECOBLEND_PILOT_KEY.length<24)
        return json({error:'ECOBLEND_PILOT_KEY no configurada en Cloudflare'},503,cors(request));
      const auth=request.headers.get('Authorization')||'';
      if(!equalStrings(auth,'Bearer '+env.ECOBLEND_PILOT_KEY))
        return json({error:'Credencial de emparejamiento no válida.'},401,cors(request));
      const roomId=crypto.randomUUID();
      const roomExpiry=Date.now()+ROOM_TTL_MS;
      const roomSig=await roomSignature(env.ECOBLEND_PILOT_KEY,roomId,roomExpiry);
      const room=roomId+'.'+roomExpiry+'.'+roomSig;
      const expires=Date.now()+60000;
      const sig=await roomSignature(env.ECOBLEND_PILOT_KEY,room,expires);
      return json({room,ticket:expires+'.'+sig,expiresSeconds:60},200,cors(request));
    }
    if(url.pathname==="/ws"){
      if(request.method!=="GET"||request.headers.get("Upgrade")?.toLowerCase()!=="websocket")
        return new Response("WebSocket required",{status:426});
      if(!SUPPORTED_ORIGINS.has(request.headers.get("Origin")))return new Response("Forbidden origin",{status:403});
      const room=url.searchParams.get("room");
      if(!await verifiedRoom(env.ECOBLEND_PILOT_KEY,room))
        return new Response("Invalid or expired signed room",{status:403});
      if(typeof env.ECOBLEND_PILOT_KEY!=='string'||env.ECOBLEND_PILOT_KEY.length<24)
        return new Response("Pairing not configured",{status:503});
      const ticket=url.searchParams.get('ticket')||'';
      const match=ticket.match(/^(\d{13})\.([a-zA-Z0-9_-]{43})$/);
      if(!match||Number(match[1])<Date.now()||Number(match[1])>Date.now()+60000)
        return new Response("Invalid or expired pairing ticket",{status:403});
      const expected=await roomSignature(env.ECOBLEND_PILOT_KEY,room,Number(match[1]));
      if(!equalStrings(expected,match[2]))return new Response("Invalid pairing ticket",{status:403});

      const stub=env.ECOBLEND_ROOMS.get(env.ECOBLEND_ROOMS.idFromName(room));
      return stub.fetch(request);
    }
    if(url.pathname!=="/mcp")return new Response("Not found",{status:404});
    if(request.method!=="POST")
      return new Response(null,{status:405,headers:{Allow:"POST"}});
    if(Number(request.headers.get("content-length")||0)>MAX_JSON)return json(fault(null,-32600,"Solicitud demasiado grande."),413);
    let packet;
    try {
      const body=await request.text();
      if(body.length>MAX_JSON)throw new Error("Solicitud demasiado grande.");
      packet=JSON.parse(body);
    }catch(error){return json(fault(null,-32700,"JSON inválido."),400);}
    if(!packet||packet.jsonrpc!=="2.0"||typeof packet.method!=="string")
      return json(fault(packet?.id,-32600,"Solicitud MCP inválida."),400);
    if(packet.id===undefined)return new Response(null,{status:202});
    if(packet.method==="initialize")
      return json(ok(packet.id,{protocolVersion:PROTOCOL,capabilities:{tools:{listChanged:false}},
        serverInfo:{name:"ecoblend-remote-mcp",version:"0.2.0"},instructions:"Conecta primero la pestaña EcoBlend a MCP nube; proporciona el ID de sala al agente. Durante una sesión EcoBlend el usuario puede conceder un permiso temporal de observación o edición y detenerlo cuando quiera; la lectura de imágenes privadas sigue requiriendo consentimiento individual."}));
    if(packet.method==="ping")return json(ok(packet.id,{}));
    if(packet.method==="tools/list")return json(ok(packet.id,{tools}));
    if(packet.method!=="tools/call")return json(fault(packet.id,-32601,"Método desconocido."),404);
    const name=packet.params?.name;
    if(typeof name!=="string"||!TOOL_MAP[name])
      return json(ok(packet.id,{isError:true,content:[{type:"text",text:"Herramienta no permitida."}]}));
    const args=packet.params?.arguments;
    try{
      validArgs(name,args);
      if(!await verifiedRoom(env.ECOBLEND_PILOT_KEY,args.room))
        throw new Error('Sala caducada o firma inválida. Reconecta desde EcoBlend.');
      if(name==="ecoblend_blueprint_format")
        return json(ok(packet.id,{content:[{type:"text",text:JSON.stringify(BLUEPRINT_FORMAT)}]}));
      const stub=env.ECOBLEND_ROOMS.get(env.ECOBLEND_ROOMS.idFromName(args.room));
      const task=await stub.fetch("https://internal.ecoblend/rpc",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({method:TOOL_MAP[name],tool:name,params:simplifyArgs(name,args)})
      });
      const result=await task.json();
      if(!task.ok||result.error)
        return json(ok(packet.id,{isError:true,content:[{type:"text",text:result.error||"No disponible."}]}));
      return json(ok(packet.id,mcpContent(name,result.result)));
    }catch(error){
      return json(ok(packet.id,{isError:true,content:[{type:"text",text:error.message||"Operación rechazada."}]}));
    }
  }
};

/** Room lifecycle: max one browser tab, max 20min, 35s operation timeout. */
export class EcoBlendRoom {
  constructor(ctx,env){this.ctx=ctx;this.env=env;this.pending=new Map();this.connectedAt=0;}
  getViewer(){
    return this.ctx.getWebSockets().find(ws=>{
      try{return ws.deserializeAttachment()?.role==="viewer"}catch{return false}
    });
  }
  async fetch(request){
    const url=new URL(request.url);
    if(url.pathname==="/ws"){
      if(this.getViewer())return new Response("Room already in use",{status:409});
      const pair=new WebSocketPair();
      const [client,server]=Object.values(pair);
      this.ctx.acceptWebSocket(server);
      server.serializeAttachment({role:"viewer",joined:Date.now()});
      this.connectedAt=Date.now();
      server.send(JSON.stringify({type:"ready",expiresMinutes:20}));
      return new Response(null,{status:101,webSocket:client});
    }
    if(url.pathname!=="/rpc"||request.method!=="POST")return json({error:"Not found"},404);
    const viewer=this.getViewer();
    if(!viewer)return json({error:"La sala no tiene una pestaña EcoBlend conectada."},409);
    const joined=viewer.deserializeAttachment()?.joined||0;
    if(Date.now()-joined>ROOM_TTL_MS) {
      viewer.close(4001,"Sesión caducada");
      return json({error:"Sala caducada: reconecta desde EcoBlend."},410);
    }
    let job;
    try {job=await request.json();}catch{return json({error:"JSON inválido."},400)}
    if(!TOOL_MAP[job.tool]||TOOL_MAP[job.tool]!==job.method)return json({error:"Herramienta no autorizada."},403);
    if(this.pending.size>=3)return json({error:"Hay demasiadas solicitudes pendientes."},429);
    const requestId=crypto.randomUUID();
    const output=new Promise(resolve=>{
      const timer=setTimeout(()=>{this.pending.delete(requestId);resolve(json({error:"EcoBlend no respondió dentro del tiempo de espera. Mantén abierta la pestaña y concede un permiso temporal de trabajo para evitar aprobaciones repetidas."},504))},25000);
      this.pending.set(requestId,{resolve,timer});
    });
    try {
      viewer.send(JSON.stringify({type:"request",requestId,method:job.method,tool:job.tool,params:job.params}));
    }catch{
      const p=this.pending.get(requestId);
      if(p){clearTimeout(p.timer);this.pending.delete(requestId)}
      return json({error:"No se puede enviar a la pestaña EcoBlend."},502);
    }
    return output;
  }
  webSocketMessage(ws,message){
    if(ws!==this.getViewer())return;
    let data;
    try{data=JSON.parse(typeof message==="string"?message:"")}catch{return}
    if(data.type!=="response"||typeof data.requestId!=="string")return;
    const pending=this.pending.get(data.requestId);
    if(!pending)return;
    this.pending.delete(data.requestId);
    clearTimeout(pending.timer);
    if(data.error) pending.resolve(json({error:String(data.error).slice(0,500)},400));
    else pending.resolve(json({result:data.result}));
  }
  webSocketClose(ws){this.cleanup();}
  webSocketError(ws){this.cleanup();}
  cleanup(){
    for(const [id,p] of this.pending){
      clearTimeout(p.timer);
      p.resolve(json({error:"EcoBlend se desconectó."},410));
    }
    this.pending.clear();
  }
}
