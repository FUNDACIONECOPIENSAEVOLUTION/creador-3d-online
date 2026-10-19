import {test} from 'node:test';
import assert from 'node:assert/strict';
import worker,{PROTOCOL} from '../src/worker.mjs';

const env={
  ECOBLEND_ROOMS:{
    idFromName(name){throw Error('Unexpected durable room creation');},
    get(){throw Error('Unexpected DO access');}
  }
};
async function post(method,id=1,params){
 const res=await worker.fetch(new Request('https://ecoblend.example/mcp',{
   method:'POST',headers:{'content-type':'application/json','accept':'application/json, text/event-stream'},
   body:JSON.stringify({jsonrpc:'2.0',id,method,params})
 }),env);
 return {status:res.status,data:res.status===202?null:await res.json()};
}
test('MCP initialize devuelve protocolo y herramientas',async()=>{
 const {status,data}=await post('initialize',1,{protocolVersion:PROTOCOL,capabilities:{}});
 assert.equal(status,200);
 assert.equal(data.result.protocolVersion,PROTOCOL);
 assert.equal(data.result.serverInfo.name,'ecoblend-remote-mcp');
});
test('Catálogo solo expone comandos declarativos y tiene esquema de sala',async()=>{
 const {data}=await post('tools/list');
 assert.ok(data.result.tools.length>=6);
 assert.ok(data.result.tools.every(t=>t.inputSchema.required.includes('room')));
 assert.ok(!data.result.tools.some(t=>/eval|execute_code/.test(t.name)));
 assert.ok(data.result.tools.some(t=>t.name==='ecoblend_build_blueprint'));
});
test('Sin sala válida no toca ningún objeto ni revela datos',async()=>{
 const a=await post('tools/call',4,{name:'ecoblend_scene',arguments:{room:'12345'}});
 assert.equal(a.data.result.isError,true);
 assert.match(a.data.result.content[0].text,/sala inválido/i);
});
test('Nunca permite origen no autorizado en conexión websocket',async()=>{
 const r=await worker.fetch(new Request('https://ecoblend.example/ws?room=00000000-0000-4000-8000-000000000001',{
   headers:{Origin:'https://attacker.invalid',Upgrade:'websocket'}
 }),env);
 assert.equal(r.status,403);
});
test('No acepta comandos desconocidos ni requests mal formadas',async()=>{
 const other=await post('tools/call',4,{name:'execute_arbitrary_code',arguments:{room:'00000000-0000-4000-8000-000000000001'}});
 assert.equal(other.data.result.isError,true);
 const invalid=await worker.fetch(new Request('https://ecoblend.example/mcp',{method:'POST',body:'not json'}),env);
 assert.equal(invalid.status,400);
});
test('Health pública no contiene información de salas',async()=>{
 const r=await worker.fetch(new Request('https://ecoblend.example/health'),env);
 assert.deepEqual((await r.json()).mcp,'/mcp');
});
