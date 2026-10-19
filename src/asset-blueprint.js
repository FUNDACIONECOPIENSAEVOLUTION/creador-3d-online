import * as THREE from 'three';

export const ASSET_VERSION = 'ecoblend.asset.v1';
export const ASSET_CATEGORIES = ['human', 'anthropomorphic', 'animal', 'creature', 'robot', 'vehicle', 'building', 'prop', 'abstract', 'other'];
export const ASSET_SHAPES = ['box', 'sphere', 'cylinder', 'cone', 'capsule', 'torus'];
const scalar = (v, min, max, name) => {
  if (typeof v !== 'number' || !Number.isFinite(v) || v < min || v > max) throw new Error(name + ' fuera de rango.');
  return v;
};
const vector = (v, def, min, max, name) => {
  const arr = v === undefined ? def : v;
  if (!Array.isArray(arr) || arr.length !== 3) throw new Error(name + ' debe contener XYZ.');
  return arr.map((n,i) => scalar(n,min,max,name + '[' + i + ']'));
};
function label(s, name, max = 80) {
  if (typeof s !== 'string' || !s.trim() || s.length > max) throw new Error(name + ' debe ser texto de 1 a ' + max + ' caracteres.');
  return s.trim();
}
export function validateAssetBlueprint(blueprint) {
  if (!blueprint || typeof blueprint !== 'object' || Array.isArray(blueprint)) throw new Error('El plano 3D debe ser JSON de tipo objeto.');
  if (blueprint.version !== ASSET_VERSION) throw new Error('Versión de plano 3D no soportada.');
  const name = label(blueprint.name, 'name');
  if (!ASSET_CATEGORIES.includes(blueprint.category)) throw new Error('Categoría 3D no reconocida.');
  if (!Array.isArray(blueprint.parts) || !blueprint.parts.length || blueprint.parts.length > 120)
    throw new Error('Un plano 3D debe contener entre 1 y 120 partes.');
  const known = new Set(['root']);
  const parts = blueprint.parts.map((part, i) => {
    if (!part || typeof part !== 'object' || Array.isArray(part)) throw new Error('Parte ' + i + ' inválida.');
    const id = label(part.id, 'parts['+i+'].id', 60);
    if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(id) || known.has(id))
      throw new Error('ID duplicado o inválido: ' + id);
    const parent = part.parent ?? 'root';
    if (typeof parent !== 'string' || !known.has(parent))
      throw new Error('La parte ' + id + ' debe referirse a una parte anterior como padre.');
    const kind = part.kind || 'mesh';
    if (!['mesh','joint'].includes(kind)) throw new Error('Tipo de parte no permitido: ' + kind);
    const shape = part.shape || 'sphere';
    if (kind === 'mesh' && !ASSET_SHAPES.includes(shape)) throw new Error('Geometría no reconocida: ' + shape);
    const color = part.color ?? '#9da8b5';
    if (typeof color !== 'string' || !/^#[0-9a-fA-F]{6}$/.test(color)) throw new Error('Color hexadecimal inválido en ' + id);
    const position = vector(part.position,[0,0,0],-25,25,'position');
    const rotation = vector(part.rotationDeg,[0,0,0],-3600,3600,'rotationDeg');
    const scale = vector(part.scale,[1,1,1],0.005,25,'scale');
    const metalness = scalar(part.metalness ?? 0, 0,1,'metalness');
    const roughness = scalar(part.roughness ?? .7,0,1,'roughness');
    known.add(id);
    return {id, name: part.name ? label(part.name,'name') : id, parent, kind, shape, position,rotationDeg:rotation,scale,color,metalness,roughness};
  });
  return {version:ASSET_VERSION,name,category:blueprint.category,parts};
}
export function buildAssetBlueprint(blueprint, quality = 'low') {
  const plan = validateAssetBlueprint(blueprint);
  const smooth = quality === 'high' ? 24 : quality === 'balanced' ? 14 : 8;
  const objects = new Map();
  const root = new THREE.Group();
  root.name = plan.name;
  root.userData.ecoblendAssetVersion = ASSET_VERSION;
  root.userData.ecoblendCategory = plan.category;
  root.userData.licenseNote = 'Verify any third-party reference rights independently.';
  objects.set('root', root);
  const geometry = new Map();
  const getGeometry = (shape) => {
    if (!geometry.has(shape)) {
      let meshGeometry;
      switch(shape){
        case 'box': meshGeometry = new THREE.BoxGeometry(1,1,1); break;
        case 'cylinder': meshGeometry = new THREE.CylinderGeometry(.5,.5,1,smooth);break;
        case 'cone': meshGeometry = new THREE.ConeGeometry(.5,1,smooth);break;
        case 'capsule': meshGeometry = new THREE.CapsuleGeometry(.5,1,smooth > 12 ? 6 : 3,smooth);break;
        case 'torus': meshGeometry = new THREE.TorusGeometry(.5,.12,6,smooth*2);break;
        default: meshGeometry = new THREE.SphereGeometry(.5,smooth*2,smooth);
      }
      geometry.set(shape,meshGeometry);
    }
    return geometry.get(shape);
  };
  for (const part of plan.parts) {
    const node = part.kind === 'joint'
      ? new THREE.Group()
      : new THREE.Mesh(getGeometry(part.shape),new THREE.MeshStandardMaterial({
          color: part.color,metalness:part.metalness,roughness:part.roughness
        }));
    node.name=part.name;
    node.userData.ecoblendPartId=part.id;
    if(part.kind==='joint') node.userData.neoJoint=true;
    node.position.fromArray(part.position);
    node.rotation.set(...part.rotationDeg.map(THREE.MathUtils.degToRad));
    node.scale.fromArray(part.scale);
    if(node.isMesh){node.castShadow=true;node.receiveShadow=true;}
    objects.get(part.parent).add(node);
    objects.set(part.id,node);
  }
  return {object:root,metadata:{parts:plan.parts.length,category:plan.category,version:ASSET_VERSION,geometry:'parametric',automaticPhotorealism:false}};
}
