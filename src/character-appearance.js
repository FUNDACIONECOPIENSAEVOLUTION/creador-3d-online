import * as THREE from 'three';
import { normalizeCharacterSpec } from './character-spec.js';

const COLORS = {
  eye: { brown:'#543420',green:'#44864b',blue:'#4b91c9',hazel:'#87723a',gray:'#798c91' },
  hair: {black:'#18191c',brown:'#493021',blond:'#bb9552',red:'#8c3525',gray:'#83878d',white:'#e5e5e2'},
  skin: {light:'#dfb39b',medium:'#c79972',tan:'#ab7854',dark:'#744b38'}
};
const BUILD = {
  slim:{torso:.86,hips:.87,shoulder:.9},
  average:{torso:1,hips:1,shoulder:1},
  curvy:{torso:1.15,hips:1.29,shoulder:.97},
  athletic:{torso:1.15,hips:1.05,shoulder:1.14},
  broad:{torso:1.26,hips:1.1,shoulder:1.23}
};
const get=(root,name)=>root.getObjectByName(name);
function addHair(head,spec) {
  let current=get(head,'EcoBlend_Cabello');
  if(current){
    head.remove(current);
    current.traverse(node=>{if(node.isMesh){node.geometry.dispose();node.material.dispose();}});
  }
  const root=new THREE.Group();
  root.name='EcoBlend_Cabello';
  head.add(root);
  if(spec.hairStyle==='none')return;
  const material=new THREE.MeshStandardMaterial({color:COLORS.hair[spec.hairColor],roughness:.93,metalness:0});
  const piece=(name,xyz,scale)=>{
    const hair=new THREE.Mesh(new THREE.SphereGeometry(1,12,8),material);
    hair.name=name;
    hair.position.set(...xyz);
    hair.scale.set(...scale);
    root.add(hair);
  };
  piece('Cabello_Coronilla',[0,.117,.025],[.159,.104,.145]);
  if(spec.hairStyle==='medium'||spec.hairStyle==='long'){
    const length=spec.hairStyle==='long'?.34:.19;
    piece('Melena_Izquierda',[-.138,-length/2,.045],[.065,.12+length,.083]);
    piece('Melena_Derecha',[.138,-length/2,.045],[.065,.12+length,.083]);
    piece('Melena_Posterior',[0,-length/2,.14],[.153,.14+length,.065]);
  }
}
/**
 * Stylized parametric adjustments only; does not provide realistic skin weights
 * nor MPFB2/Blender functionality. Inputs are explicit and validated.
 */
export function applyCharacterAppearance(root,rawSpec={}){
  if(!root?.userData?.neoFreeCharacter)
    throw new Error('Selecciona una base humana o ángel EcoBlend, no un GLB externo.');
  const spec=normalizeCharacterSpec(rawSpec,root.userData.ecoblendCharacterSpec);
  const skin=COLORS.skin[spec.skinTone];
  const iris=COLORS.eye[spec.eyeColor];
  root.traverse(obj=>{
    if(!obj.isMesh)return;
    if(obj.name==='Rostro_Base'||obj.name==='Nariz'||obj.name==='Cuello_Piel'||
       obj.name.startsWith('Oreja_')||obj.name.endsWith('_Palma')||obj.name.includes('_Falange_'))
      obj.material.color.set(skin);
    if(obj.name.startsWith('Ojo_')){
      if(!obj.userData.ecoblendIris){
        obj.material=obj.material.clone();
        obj.userData.ecoblendIris=true;
      }
      obj.material.color.set(iris);
      obj.material.roughness=.22;
    }
  });
  const shape=BUILD[spec.build];
  const torso=get(root,'Torso_Armadura');
  const pelvis=get(root,'Pelvis');
  if(torso){
    torso.scale.x=.29*shape.torso;
    torso.scale.z=.18*Math.min(1.25,shape.torso);
  }
  if(pelvis)pelvis.scale.x=.255*shape.hips*(spec.presentation==='feminine'?1.04:1);
  for(const [name,sign] of [['Izquierdo_Hombro',-1],['Derecho_Hombro',1]]){
    const part=get(root,name);
    if(part)part.position.x=sign*.335*shape.shoulder*(spec.presentation==='feminine'?.95:1);
  }
  for(const [name,sign] of [['Izquierda_Cadera',-1],['Derecha_Cadera',1]]){
    const part=get(root,name);
    if(part)part.position.x=sign*.16*shape.hips;
  }
  const face=get(root,'Rostro_Base');
  if(face){
    face.scale.x=spec.faceShape==='round'?.172:spec.faceShape==='angular'?.147:.156;
    face.scale.y=spec.faceShape==='round'?.17:spec.faceShape==='angular'?.21:.196;
  }
  const head=get(root,'Cabeza');
  if(head)addHair(head,spec);
  root.scale.setScalar(spec.heightCm/172);
  root.userData.ecoblendCharacterSpec=spec;
  root.userData.ecoblendAppearance='stylized';
  return {spec,updated:true,quality:'stylized_3d_base',note:'No es una reconstrucción humana hiperrealista ni MPFB2 ejecutándose en la web.'};
}
