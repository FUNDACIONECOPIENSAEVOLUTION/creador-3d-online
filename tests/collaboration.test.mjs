import test from 'node:test';
import assert from 'node:assert/strict';
import {makePresetBlueprint} from '../src/asset-presets.js';
import {validateAssetBlueprint,buildAssetBlueprint} from '../src/asset-blueprint.js';
import {isAuthorizedMethod,COLLAB_TTL_MS} from '../src/mcp-collaboration.js';

test('peón humanoide se convierte en escena 3D real, editable y con articulaciones',()=>{
 const blueprint=makePresetBlueprint('guardian-pawn');
 const plan=validateAssetBlueprint(blueprint);
 assert.equal(plan.category,'human');
 assert.ok(plan.parts.length>=55);
 for(const name of ['Rostro','Casco','Torso_Pivote','Hombro_Izq','Codo_Izq','Codo_Der','Rodilla_Izq','Lanza_Punta','Escudo_Blason']){
   if(name==='Casco') continue;
   assert.ok(plan.parts.some(p=>p.id===name),name+' debe existir');
 }
 const {object,metadata}=buildAssetBlueprint(blueprint,'low');
 let meshes=0,joints=0;
 object.traverse(part=>{if(part.isMesh)meshes++;if(part.userData?.neoJoint)joints++;});
 assert.ok(meshes>=45);
 assert.ok(joints>=10);
 assert.equal(metadata.automaticPhotorealism,false);
 assert.equal(object.name,'Peon_Guardian_Ecoajedrez');
});

test('permiso de edición temporal cubre las herramientas declarativas pero nunca imágenes privadas',()=>{
 assert.equal(COLLAB_TTL_MS,20*60*1000);
 for(const tool of ['mcp_get_scene_graph','mcp_capture_quad_view','mcp_capture_progress',
 'mcp_get_feedback','mcp_asset_build','mcp_asset_preset','mcp_animation_preset']){
  assert.equal(isAuthorizedMethod('edit',tool),true,'edit '+tool);
 }
 assert.equal(isAuthorizedMethod('observe','mcp_asset_build'),false);
 assert.equal(isAuthorizedMethod('observe','mcp_capture_quad_view'),true);
 assert.equal(isAuthorizedMethod('edit','mcp_get_reference_image'),false);
 assert.equal(isAuthorizedMethod('edit','mcp_execute_three_code'),false);
 assert.equal(isAuthorizedMethod('none','mcp_asset_build'),false);
});
