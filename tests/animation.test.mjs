import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { AnimationEditor } from '../src/animation-editor.js';

globalThis.document = { getElementById: () => null };

function fixture() {
  const scene = new THREE.Scene();
  const root = new THREE.Group();
  root.name = 'Angel';
  const arm = new THREE.Bone();
  arm.name = 'Arm_Left';
  root.add(arm);
  scene.add(root);
  const clips = [];
  const studio = {
    scene, objects: [root], selectedObject: arm,
    refreshOutliner() {}, selectObject(node) { this.selectedObject = node; },
    logAIAction() {}, setStatus() {},
    characterWorkflow: {
      ensureModel() {},
      stopForEdit() {},
      getClipsFor() { return clips; },
      registerAuthoredClip(_, clip) { clips.push(clip); }
    }
  };
  return { studio, editor: new AnimationEditor(studio), root, arm, clips };
}

test('Se crean poses de huesos reales en dos tiempos y un clip glTF exportable', () => {
  const { editor, root, arm, clips } = fixture();
  editor.createAction('Ataque', 2, root);
  editor.poseAndRecord({ uuid: arm.uuid, time: 0, rotationDeg: [0, 0, 0] });
  editor.poseAndRecord({ uuid: arm.uuid, time: 1, rotationDeg: [90, 0, 0] });
  const response = editor.saveAction();
  assert.equal(response.name, 'Ataque');
  assert.equal(response.tracks, 3);
  assert.equal(clips.length, 1);
  assert.equal(clips[0].validate(), true);
  assert.equal(clips[0].tracks[1].name, arm.uuid + '.quaternion');

  arm.rotation.set(0, 0, 0);
  const mixer = new THREE.AnimationMixer(root);
  mixer.clipAction(clips[0]).play();
  mixer.update(0.5);
  assert.ok(arm.rotation.x > 0.3 && arm.rotation.x < 1.3, 'El brazo debe girar de manera interpolada');
});

test('Crea pivote para extremidad rígida conservando posición mundial', () => {
  const { studio, editor, root } = fixture();
  const part = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial());
  part.name = 'Arm_Armor';
  part.position.set(0.8, 1, 0);
  root.add(part);
  studio.selectedObject = part;
  const previous = part.getWorldPosition(new THREE.Vector3()).clone();
  const result = editor.addPivot({ uuid: part.uuid, name: 'Hombro', worldPosition: [0.4, 1.6, 0] });
  assert.equal(result.name, 'Hombro');
  assert.equal(part.parent.name, 'Hombro');
  assert.ok(previous.distanceTo(part.getWorldPosition(new THREE.Vector3())) < 1e-6);
  assert.equal(part.parent.userData.neoJoint, true);
});

test('Presets iniciales no dependen de servidores o IA externa', () => {
  const { studio, editor, root, clips } = fixture();
  studio.selectedObject = root;
  const result = editor.makeRigidPreset('attack');
  assert.equal(result.type, 'whole_model');
  assert.equal(clips.length, 1);
  assert.equal(clips[0].validate(), true);
  assert.ok(clips[0].tracks[0].name.startsWith(root.uuid));
  assert.throws(() => editor.makeRigidPreset('remote-provider'), /Preset no válido/);
});

test('Se rechazan fotogramas fuera de duración y vectores inválidos', () => {
  const { editor, root, arm } = fixture();
  editor.createAction('Prueba', 2, root);
  assert.throws(() => editor.poseAndRecord({ uuid: arm.uuid, time: 4 }), /fuera de la acción/);
  assert.throws(() => editor.poseAndRecord({ uuid: arm.uuid, time: 1, rotationDeg: [NaN, 0, 0] }), /números válidos/);
});
