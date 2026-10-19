import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { ASSET_VERSION, validateAssetBlueprint, buildAssetBlueprint } from '../src/asset-blueprint.js';
import { makePresetBlueprint, matchPreset, PRESET_OPTIONS } from '../src/asset-presets.js';
import { planFreeCommand } from '../src/free-command-assistant.js';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

globalThis.FileReader ||= class {
  result=null;onloadend=null;
  async readAsArrayBuffer(blob) {this.result=await blob.arrayBuffer();this.onloadend?.();}
  async readAsDataURL(blob) {
    this.result='data:'+(blob.type||'application/octet-stream')+';base64,'+
      Buffer.from(await blob.arrayBuffer()).toString('base64');
    this.onloadend?.();
  }
};

test('Las plantillas incluyen objetos, antropomorfos, robot y criaturas, sin APIs externas',()=>{
  for(const {id} of PRESET_OPTIONS){
    const blueprint=makePresetBlueprint(id);
    const plan=validateAssetBlueprint(blueprint);
    const {object,metadata}=buildAssetBlueprint(blueprint,'low');
    assert.equal(metadata.category,plan.category);
    assert.equal(object.userData.ecoblendAssetVersion,ASSET_VERSION);
    assert.ok(object.children.length);
    let meshes=0;
    object.traverse(node => {if(node.isMesh)meshes++;});
    assert.ok(meshes>0 && meshes<=120);
    assert.equal(plan.parts.length,blueprint.parts.length);
  }
});
test('Descripciones en español reconocen plantillas básicas; lo desconocido no se inventa',()=>{
  assert.equal(matchPreset('quiero un gato antropomorfo guerrero'),'anthro-cat');
  assert.equal(matchPreset('dragón de cuatro patas'),'dragon');
  assert.equal(matchPreset('construye una silla'),'chair');
  assert.equal(matchPreset('un objeto que nadie ha visto'),null);
  assert.deepEqual(planFreeCommand('crea un gato antropomorfo y modo ligero')[0],{type:'asset',preset:'anthro-cat'});
});
test('Se rechazan planos maliciosos o inválidos antes de construir',()=>{
  const base=makePresetBlueprint('robot');
  assert.throws(()=>validateAssetBlueprint({...base,parts:[{id:'evil',kind:'mesh',shape:'javascript',position:[0,0,0]}]}),/Geometría no reconocida/);
  assert.throws(()=>validateAssetBlueprint({...base,parts:[{id:'evil',parent:'missing',shape:'box'}]}),/padre/);
  assert.throws(()=>validateAssetBlueprint({...base,parts:Array.from({length:121},(_,i)=>({id:'p'+i}))}),/120/);
  assert.throws(()=>validateAssetBlueprint({...base,parts:[{id:'bad',shape:'box',scale:[1,1,NaN]}]}),/fuera de rango/);
  assert.throws(()=>validateAssetBlueprint({...base,parts:[{id:'bad',shape:'box',color:'javascript:alert(1)'}]}),/Color hexadecimal/);
});
test('Una IA puede describir una figura original por partes y exportarla como GLB animable', {timeout:12000},async()=>{
  const blueprint={version:ASSET_VERSION,name:'Figura_Imaginada',category:'other',parts:[
    {id:'base',shape:'cylinder',position:[0,.5,0],scale:[.7,1,.7],color:'#a07db0'},
    {id:'neck',parent:'root',kind:'joint',position:[0,1,0]},
    {id:'top',parent:'neck',shape:'sphere',scale:[.8,.8,.8],color:'#f0b090'}
  ]};
  const {object}=buildAssetBlueprint(blueprint,'low');
  const joint=object.getObjectByName('neck');
  assert.equal(joint.userData.neoJoint,true);
  const clip=new THREE.AnimationClip('Tilt',1,[
    new THREE.QuaternionKeyframeTrack(joint.uuid+'.quaternion',
      [0,1],[0,0,0,1,...new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),.3).toArray()])
  ]);
  const array=await new GLTFExporter().parseAsync(object,{binary:true,animations:[clip]});
  const result=await new GLTFLoader().parseAsync(array,'');
  assert.equal(result.animations[0].name,'Tilt');
  assert.ok(result.scene.getObjectByName('neck'));
});
