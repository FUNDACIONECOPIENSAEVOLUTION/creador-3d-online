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

test('Solo el propietario con clave larga puede crear una sala temporal',async()=>{
 const secret='a-private-key-only-for-unit-tests-123456789';
 const authorized={...env,ECOBLEND_PILOT_KEY:secret};
 const link='https://ecoblend.example/pair';
 const noOrigin=await worker.fetch(new Request(link,{method:'POST',headers:{Authorization:'Bearer '+secret}}),authorized);
 assert.equal(noOrigin.status,403);
 const wrong=await worker.fetch(new Request(link,{method:'POST',headers:{
   Origin:'https://fundacionecopiensaevolution.github.io',Authorization:'Bearer wrong-key'
 }}),authorized);
 assert.equal(wrong.status,401);
 const good=await worker.fetch(new Request(link,{method:'POST',headers:{
   Origin:'https://fundacionecopiensaevolution.github.io',Authorization:'Bearer '+secret
 }}),authorized);
 assert.equal(good.status,200);
 const data=await good.json();
 assert.match(data.room,/^[0-9a-f-]{36}\.\d{13}\.[a-zA-Z0-9_-]{43}$/i);
 const forged=data.room.slice(0,-1)+(data.room.at(-1)==='x'?'y':'x');
 const rejected=await post('tools/call',7,{name:'ecoblend_scene',arguments:{room:forged}});
 assert.equal(rejected.data.result.isError,true);
 assert.match(rejected.data.result.content[0].text,/firma inválida|caducada/i);
 assert.match(data.ticket,/^\d{13}\.[a-zA-Z0-9_-]{43}$/);
 const invalidTicket=await worker.fetch(new Request('https://ecoblend.example/ws?room='+data.room+'&ticket=invalid',{
   headers:{Origin:'https://fundacionecopiensaevolution.github.io',Upgrade:'websocket'}
 }),authorized);
 assert.equal(invalidTicket.status,403);
});


test('el MCP descubre el formato real de blueprint sin tocar el navegador',async()=>{
 const secret='mcp-test-secret-for-ecoblend-123456789';
 const authorized={...env,ECOBLEND_PILOT_KEY:secret};
 const pair=await worker.fetch(new Request('https://ecoblend.example/pair',{
   method:'POST',headers:{Origin:'https://fundacionecopiensaevolution.github.io',
     Authorization:'Bearer '+secret}
 }),authorized);
 assert.equal(pair.status,200);
 const {room}=await pair.json();
 const request=async(name,args)=>{
   const response=await worker.fetch(new Request('https://ecoblend.example/mcp',{
     method:'POST',headers:{'content-type':'application/json'},
     body:JSON.stringify({jsonrpc:'2.0',id:9,method:'tools/call',
       params:{name,arguments:{room,...args}}})
   }),authorized);
   assert.equal(response.status,200);
   return (await response.json()).result;
 };
 const schema=await request('ecoblend_blueprint_format',{});
 assert.equal(schema.isError,undefined);
 const fmt=JSON.parse(schema.content[0].text);
 assert.equal(fmt.version,'ecoblend.asset.v1');
 assert.equal(fmt.minimalExample.version,'ecoblend.asset.v1');
 assert.equal(fmt.minimalExample.parts[0].shape,'sphere');
 assert.match(fmt.shortcut,/guardian-pawn/);
 const wrong=await request('ecoblend_validate_blueprint',{
   blueprint:{version:'legacy-v2',name:'Error',category:'human',parts:[{id:'cuerpo'}]}
 });
 assert.equal(wrong.isError,true);
 assert.match(wrong.content[0].text,/ecoblend\.asset\.v1/);
 const invalid=await request('ecoblend_build_blueprint',{blueprint:{version:'ecoblend.asset.v1',name:'x'}});
 assert.equal(invalid.isError,true);
 assert.match(invalid.content[0].text,/name, category/i);
});

test('health identifica el despliegue actualizado y sus nuevas herramientas',async()=>{
 const response=await worker.fetch(new Request('https://ecoblend.example/health'),env);
 const health=await response.json();
 assert.equal(health.version,'0.2.0');
 assert.ok(health.features.includes('ecoblend_blueprint_format'));
 const toolList=await post('tools/list');
 assert.ok(toolList.data.result.tools.some(x=>x.name==='ecoblend_blueprint_format'));
 assert.ok(toolList.data.result.tools.some(x=>x.name==='ecoblend_preset'));
});
