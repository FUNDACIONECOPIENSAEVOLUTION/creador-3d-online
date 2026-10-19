import * as THREE from 'three';

/**
 * NeoBlender Free Base Characters.
 * Parametric, articulated game-ready *starter geometry*: authored entirely
 * in-browser, with no model-downloads, subscriptions, APIs, or generative AI.
 * Segmented limbs use transform pivots (not anatomical skinning).
 * This is a mannequin prototype, NOT photorealistic anatomy.
 */
export function createFreeCharacter({ type = 'humanoid', detail = 'low' } = {}) {
  if (!['humanoid', 'angel'].includes(type)) throw new Error('Plantilla desconocida.');
  if (!['low', 'balanced'].includes(detail)) throw new Error('Resolución no válida.');
  const radial = detail === 'low' ? 10 : 18;
  const width = detail === 'low' ? 12 : 22;
  const group = new THREE.Group();
  group.name = type === 'angel' ? 'Guardian_Alado_Libre' : 'Humanoide_Articulado_Libre';
  group.userData.neoFreeCharacter = true;
  group.userData.license = 'CC0-1.0';
  group.userData.note = 'Base geométrica estilizada con pivotes, no realismo fotográfico.';

  const materials = {
    skin: new THREE.MeshStandardMaterial({ color: '#c79972', roughness: 0.78, metalness: 0 }),
    cloth: new THREE.MeshStandardMaterial({ color: '#e5dec7', roughness: 0.88, metalness: 0 }),
    armor: new THREE.MeshStandardMaterial({ color: '#aeb9c3', roughness: 0.33, metalness: 0.77 }),
    gold: new THREE.MeshStandardMaterial({ color: '#d5ae5c', roughness: 0.28, metalness: 0.78 }),
    leather: new THREE.MeshStandardMaterial({ color: '#474144', roughness: 0.81, metalness: 0 }),
    feather: new THREE.MeshStandardMaterial({ color: '#f1f0e9', roughness: 0.85, metalness: 0 })
  };
  const sphere = new THREE.SphereGeometry(1, width, radial);
  const cylinder = new THREE.CylinderGeometry(1, 1, 1, radial);
  const thinCylinder = new THREE.CylinderGeometry(0.75, 1, 1, radial);
  const torus = new THREE.TorusGeometry(1, 0.07, 6, radial * 3);

  function pivot(parent, name, at) {
    const item = new THREE.Group();
    item.name = name;
    item.userData.neoJoint = true;
    item.position.set(...at);
    parent.add(item);
    return item;
  }

  function shape(parent, name, geo, mat, where, scale, rotation) {
    const item = new THREE.Mesh(geo, mat);
    item.name = name;
    item.position.set(...where);
    item.scale.set(...scale);
    if (rotation) item.rotation.set(...rotation);
    item.castShadow = true;
    item.receiveShadow = true;
    parent.add(item);
    return item;
  }

  const pelvis = pivot(group, 'Cadera_Centro', [0, 0.96, 0]);
  shape(pelvis, 'Pelvis', sphere, materials.cloth, [0, 0, 0], [.255, .18, .16]);
  const spine = pivot(pelvis, 'Columna', [0, .05, 0]);
  shape(spine, 'Torso_Armadura', sphere, materials.cloth, [0, .33, 0], [.29, .40, .18]);
  shape(spine, 'Pectoral_Armadura', sphere, materials.armor, [0, .45, -.12], [.285, .26, .10]);
  shape(spine, 'Borde_Pectoral', sphere, materials.gold, [0, .35, -.188], [.22, .018, .012]);
  const neck = pivot(spine, 'Cuello', [0, .62, 0]);
  shape(neck, 'Cuello_Piel', cylinder, materials.skin, [0, .045, 0], [.075, .12, .075]);
  const head = pivot(neck, 'Cabeza', [0, .18, 0]);
  shape(head, 'Rostro_Base', sphere, materials.skin, [0, 0, -.005], [.156, .196, .145]);
  shape(head, 'Nariz', sphere, materials.skin, [0, -.01, -.149], [.033, .049, .036]);
  for (const sign of [-1, 1]) {
    shape(head, sign < 0 ? 'Ojo_Izquierdo' : 'Ojo_Derecho', sphere, materials.leather,
      [sign * .064, .025, -.129], [.021, .018, .01]);
    shape(head, 'Oreja_' + (sign < 0 ? 'I' : 'D'), sphere, materials.skin,
      [sign * .151, -.02, 0], [.024, .053, .029]);
  }

  function arm(sign, side) {
    const shoulder = pivot(spine, side + '_Hombro', [sign * .335, .53, 0]);
    shape(shoulder, side + '_Hombrera', sphere, materials.armor, [sign * .03, -.065, 0], [.15, .16, .145]);
    shape(shoulder, side + '_Brazo', thinCylinder, materials.cloth, [sign * .01, -.23, 0], [.105, .34, .105]);
    const elbow = pivot(shoulder, side + '_Codo', [sign * .01, -.405, 0]);
    shape(elbow, side + '_Antebrazo', thinCylinder, materials.armor, [0, -.175, 0], [.083, .29, .085]);
    const wrist = pivot(elbow, side + '_Muneca', [0, -.33, 0]);
    shape(wrist, side + '_Palma', sphere, materials.skin, [0, -.08, -.002], [.077, .10, .045]);
    for (let finger = 0; finger < 5; finger++) {
      const x = (finger - 2) * .031;
      const length = finger === 0 ? .075 : finger === 4 ? .09 : finger === 2 ? .155 : .126;
      const f = pivot(wrist, side + '_Dedo_' + (finger + 1), [x, -.15, -.01]);
      shape(f, side + '_Falange_' + (finger + 1), thinCylinder, materials.skin,
        [0, -length / 2, 0], [.012, length, .013],
        finger === 0 ? [0, 0, sign * .5] : undefined);
    }
    return shoulder;
  }

  arm(-1, 'Izquierdo');
  arm(1, 'Derecho');

  function leg(sign, side) {
    const hip = pivot(pelvis, side + '_Cadera', [sign * .16, -.055, 0]);
    shape(hip, side + '_Muslo', thinCylinder, materials.cloth, [0, -.225, 0], [.135, .42, .135]);
    const knee = pivot(hip, side + '_Rodilla', [0, -.435, 0]);
    shape(knee, side + '_Pierna', thinCylinder, materials.armor, [0, -.18, 0], [.102, .34, .1]);
    const foot = pivot(knee, side + '_Tobillo', [0, -.38, 0]);
    shape(foot, side + '_Bota', sphere, materials.leather, [0, -.06, -.10], [.125, .105, .225]);
  }
  leg(-1, 'Izquierda');
  leg(1, 'Derecha');

  if (type === 'angel') {
    const halo = pivot(head, 'Halo_Pivote', [0, .285, 0]);
    shape(halo, 'Halo_Dorado', torus, materials.gold, [0, 0, 0], [.19, .19, .19], [Math.PI / 2, 0, 0]);
    for (const sign of [-1, 1]) {
      const side = sign < 0 ? 'Izquierda' : 'Derecha';
      const wing = pivot(spine, 'Ala_' + side + '_Articulacion', [sign * .18, .54, .17]);
      // Fan of individual feathers: move/rotate wings by their pivots.
      for (let i = 0; i < 10; i++) {
        const angle = sign * (.12 + i * .095);
        const feather = shape(wing, 'Pluma_' + side + '_' + (i + 1),
          sphere, materials.feather,
          [sign * (.18 + i * .062), .15 - i * .035, .03 + i * .005],
          [.085, .41 - i * .011, .045], [0, 0, -angle]);
        feather.castShadow = false;
      }
    }
  }

  const box = new THREE.Box3().setFromObject(group);
  const height = box.max.y - box.min.y;
  return {
    object: group,
    metadata: {
      type, geometry: 'segmented_parametric',
      lightweight: true, height: Number(height.toFixed(2)),
      rigType: 'hierarchical_pivots',
      compatibleWithKeyframes: true,
      notAutomaticHumanoidSkinning: true,
      source: 'NeoBlender built-in shapes; no external downloads or subscriptions'
    }
  };
}
