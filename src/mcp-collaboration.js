/**
 * EcoBlend 1.8 — Collaboration controller. No external AI SDK needed.
 * Lives in the opened browser tab; no clipboard, localStorage or cloud persistence.
 * Live video/screen sharing is NOT implemented: snapshots are made on successful edits.
 */
export const COLLAB_TTL_MS = 20 * 60_000;
const READ = new Set([
  'mcp_get_scene_graph','mcp_capture_quad_view','mcp_get_creation_brief',
  'mcp_asset_validate','mcp_animation_inspect','mcp_get_feedback','mcp_capture_progress'
]);
const WRITE = new Set(['mcp_asset_build','mcp_asset_preset','mcp_animation_preset','mcp_modify_object']);
export const isAuthorizedMethod = (scope,method) =>
  scope === 'edit' ? READ.has(method) || WRITE.has(method) :
  scope === 'observe' ? READ.has(method) : false;

export class CollaborationSession {
  constructor(app) {
    this.app=app;
    this.scope='none';
    this.room=null;
    this.expires=0;
    this.feedback=[];
    this.frames=[];
  }
  connected(room) {
    this.revoke();
    this.room=room;
    this.feedback=[];
    this.frames=[];
    this.render();
  }
  grant(scope) {
    if(scope!=='observe' && scope!=='edit')throw Error('Nivel de control no permitido.');
    if(!this.app.remoteRoomId || this.app.remoteSocket?.readyState!==WebSocket.OPEN)
      throw Error('Primero conecta EcoBlend MCP Nube.');
    this.room=this.app.remoteRoomId;
    this.scope=scope;
    const roomExpiry=Number(this.room.split('.')[1]);
    this.expires=Number.isFinite(roomExpiry) ? Math.min(Date.now()+COLLAB_TTL_MS,roomExpiry) : Date.now()+COLLAB_TTL_MS;
    this.render();
    return {scope,expires:this.expires};
  }
  revoke() {
    this.scope='none';
    this.expires=0;
    this.render();
  }
  allows(method) {
    if(this.scope==='none' || this.room!==this.app.remoteRoomId)return false;
    if(Date.now()>=this.expires){this.revoke();return false;}
    // Images uploaded by the user NEVER inherit a broad grant.
    if(method==='mcp_get_reference_image')return false;
    return isAuthorizedMethod(this.scope,method);
  }
  addFeedback(value) {
    const text=typeof value==='string'?value.trim():'';
    if(!text || text.length>700)throw Error('Escribe una corrección de 1 a 700 caracteres.');
    const selected=this.app.selectedObject;
    const item={
      id:crypto.randomUUID(),time:new Date().toISOString(),
      text,object: selected && selected.name!=='Studio_Floor'
        ? {name:selected.name,uuid:selected.uuid}:null,
      seen:false
    };
    this.feedback.push(item);
    if(this.feedback.length>30)this.feedback.shift();
    this.render();
    return item;
  }
  getFeedback() {
    const pending=this.feedback.filter(x=>!x.seen).slice(0,20);
    for(const x of pending)x.seen=true;
    this.render();
    return {notes:pending,remaining:this.feedback.filter(x=>!x.seen).length,
      instruction:'Los comentarios son peticiones explícitas del usuario; consúltalos y confirma los cambios aplicados.'};
  }
  pendingCount() {return this.feedback.filter(x=>!x.seen).length;}
  recordFrame(action='Edición'){
    if(!this.room || this.room!==this.app.remoteRoomId)return;
    try {
      const renderer=this.app.renderer;
      renderer.render(this.app.scene,this.app.camera);
      const source=renderer.domElement;
      const canvas=document.createElement('canvas');
      canvas.width=360;canvas.height=225;
      canvas.getContext('2d').drawImage(source,0,0,canvas.width,canvas.height);
      this.frames.push({
        src:canvas.toDataURL('image/jpeg',.66), canvas,
        at:new Date().toLocaleTimeString('es-CO'),
        action:String(action).slice(0,48)
      });
      if(this.frames.length>6)this.frames.shift();
      const image=document.getElementById('mcp-progress-preview');
      if(image){image.src=this.frames.at(-1).src;image.hidden=false;}
    }catch{
      // A lost WebGL context must not interrupt scene editing.
    }
  }
  getProgress(){
    if(this.frames.length===0)this.recordFrame('Vista inicial');
    if(!this.frames.length)throw Error('No hay imágenes disponibles. Revisa el visor 3D.');
    const canvas=document.createElement('canvas');
    canvas.width=720;canvas.height=516;
    const ctx=canvas.getContext('2d');
    ctx.fillStyle='#111827';ctx.fillRect(0,0,canvas.width,canvas.height);
    // Browser image decode is asynchronous; use an offscreen copy of each
    // source at record time instead of decoding data URLs during MCP calls.
    for(let i=0;i<Math.min(4,this.frames.length);i++){
      const frame=this.frames[Math.max(0,this.frames.length-4)+i];
      if(frame.canvas)ctx.drawImage(frame.canvas,(i%2)*360,Math.floor(i/2)*258,360,225);
      ctx.fillStyle='rgba(0,0,0,.8)';
      ctx.fillRect((i%2)*360,Math.floor(i/2)*258+225,360,33);
      ctx.fillStyle='#d1fae5';ctx.font='12px sans-serif';
      ctx.fillText((frame.at+' · '+frame.action).slice(0,48),
        (i%2)*360+7,Math.floor(i/2)*258+246);
    }
    return {mimeType:'image/jpeg',dataUrl:canvas.toDataURL('image/jpeg',.76),
      frames:this.frames.length,description:'Registro de avances: hasta cuatro capturas tras acciones de modelado; no es un video en vivo.'};
  }
  render(){
    if(typeof document==='undefined')return;
    const status=document.getElementById('mcp-collab-status');
    if(status)status.textContent=this.scope==='none'?'Control IA desactivado':
      'IA '+(this.scope==='edit'?'puede editar':'solo observa')+
      ' hasta '+new Date(this.expires).toLocaleTimeString('es-CO');
    const stop=document.getElementById('mcp-collab-stop');
    if(stop)stop.disabled=this.scope==='none';
    const count=document.getElementById('mcp-feedback-count');
    if(count)count.textContent=this.pendingCount()+' comentario(s) sin leer por la IA';
  }
}
