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
const ROOM_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const MAX_JSON = 135 * 1024;

const tools = [
  { name:"ecoblend_scene", description:"Consultar grafo y geometría de la escena EcoBlend, previa aprobación en el navegador.", inputSchema: {type:"object",required:["room"],properties:{room:{type:"string"}}}, annotations:{readOnlyHint:true}},
  { name:"ecoblend_quad_view", description:"Obtener captura de cuatro vistas 3D, previa aprobación en el navegador.", inputSchema: {type:"object",required:["room"],properties:{room:{type:"string"}}}, annotations:{readOnlyHint:true}},
  { name:"ecoblend_creation_brief", description:"Leer el encargo de creación 3D actual, previa aprobación del usuario.", inputSchema: {type:"object",required:["room"],properties:{room:{type:"string"}}}, annotations:{readOnlyHint:true}},
  { name:"ecoblend_reference_image", description:"Leer la imagen de referencia cargada; el navegador pedirá autorización específica.", inputSchema: {type:"object",required:["room"],properties:{room:{type:"string"}}}, annotations:{readOnlyHint:true}},
  { name:"ecoblend_preset", description:"Crear una figura de catálogo mediante un comando tipado que el usuario aprobará.", inputSchema: {type:"object",required:["room","id"],properties:{room:{type:"string"},id:{type:"string",enum:["anthro-cat","dragon","robot","tree","chair","vehicle","castle"]}}}, annotations:{destructiveHint:false,readOnlyHint:false}},
  { name:"ecoblend_validate_blueprint", description:"Validar la definición de modelo 3D sin modificar la escena.", inputSchema: {type:"object",required:["room","blueprint"],properties:{room:{type:"string"},blueprint:{type:"object"}}}, annotations:{readOnlyHint:true}},
  { name:"ecoblend_build_blueprint", description:"Construir modelo 3D a partir de un blueprint validado; la ventana EcoBlend debe aprobarlo.", inputSchema: {type:"object",required:["room","blueprint"],properties:{room:{type:"string"},blueprint:{type:"object"}}}, annotations:{destructiveHint:false,readOnlyHint:false}},
  { name:"ecoblend_animation_inspect", description:"Inspeccionar articulaciones y animaciones, previa aprobación.", inputSchema: {type:"object",required:["room"],properties:{room:{type:"string"}}}, annotations:{readOnlyHint:true}},
  { name:"ecoblend_animation_preset", description:"Aplicar animación básica al modelo seleccionado previa confirmación.", inputSchema: {type:"object",required:["room","kind"],properties:{room:{type:"string"},kind:{type:"string",enum:["idle","attack","defend","hit","defeat"]}}}, annotations:{destructiveHint:false,readOnlyHint:false}}
];
const TOOL_MAP = {
  ecoblend_scene:"mcp_get_scene_graph",
  ecoblend_quad_view:"mcp_capture_quad_view",
  ecoblend_creation_brief:"mcp_get_creation_brief",
  ecoblend_reference_image:"mcp_get_reference_image",
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
  if(name==="ecoblend_preset" && !["anthro-cat","dragon","robot","tree","chair","vehicle","castle"].includes(args.id))throw new Error("Plantilla desconocida.");
  if(name==="ecoblend_animation_preset" && !["idle","attack","defend","hit","defeat"].includes(args.kind))throw new Error("Movimiento no permitido.");
  if(name.includes("blueprint") && (!args.blueprint||typeof args.blueprint!=="object"||Array.isArray(args.blueprint)
      ||!Array.isArray(args.blueprint.parts)||args.blueprint.parts.length>120))throw new Error("Plano 3D inválido.");
}
function simplifyArgs(name,args){
  const clean={...args};
  delete clean.room;
  return clean;
}
function mcpContent(name,result){
  if(["ecoblend_quad_view","ecoblend_reference_image"].includes(name)){
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
      return json({service:"ecoblend-remote-mcp",version:"0.1.0",mode:"temporary-room",mcp:"/mcp"});
    if(url.pathname==="/ws"){
      if(request.method!=="GET"||request.headers.get("Upgrade")?.toLowerCase()!=="websocket")
        return new Response("WebSocket required",{status:426});
      if(!SUPPORTED_ORIGINS.has(request.headers.get("Origin")))return new Response("Forbidden origin",{status:403});
      const room=url.searchParams.get("room");
      if(badRoom(room))return new Response("Invalid room",{status:400});
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
        serverInfo:{name:"ecoblend-remote-mcp",version:"0.1.0"},instructions:"Conecta primero la pestaña EcoBlend a MCP nube; proporciona el ID de sala al agente. Cada operación necesita aprobación visible del usuario."}));
    if(packet.method==="ping")return json(ok(packet.id,{}));
    if(packet.method==="tools/list")return json(ok(packet.id,{tools}));
    if(packet.method!=="tools/call")return json(fault(packet.id,-32601,"Método desconocido."),404);
    const name=packet.params?.name;
    if(typeof name!=="string"||!TOOL_MAP[name])
      return json(ok(packet.id,{isError:true,content:[{type:"text",text:"Herramienta no permitida."}]}));
    const args=packet.params?.arguments;
    try{
      validArgs(name,args);
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
      const timer=setTimeout(()=>{this.pending.delete(requestId);resolve(json({error:"Sin respuesta o sin aprobación en EcoBlend."},504))},35000);
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
