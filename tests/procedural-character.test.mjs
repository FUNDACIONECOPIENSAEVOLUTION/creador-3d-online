import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { createFreeCharacter } from '../src/procedural-character.js';
import { AnimationEditor } from '../src/animation-editor.js';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';

globalThis.FileReader ||= class {
  result = null;
  onloadend = null;
  onerror = null;
  async readAsArrayBuffer(blob) {
    try {
      this.result = await blob.arrayBuffer();
      this.onloadend?.();
    } catch (error) { this.onerror?.(error); }
  }
  async readAsDataURL(blob) {
    try {
      this.result = 'data:' + (blob.type || 'application/octet-stream') + ';base64,' +
        Buffer.from(await blob.arrayBuffer()).toString('base64');
      this.onloadend?.();
    } catch (error) { this.onerror?.(error); }
  }
};

globalThis.document ||= { getElementById: () => null };

test('Dos modelos nativos tienen anatomía base, articulaciones y cinco dedos por mano', () => {
  for (const type of ['humanoid', 'angel']) {
    const { object, metadata } = createFreeCharacter({ type, detail: 'low' });
    let triangleCount = 0;
    object.traverse(part => {
      if (!part.isMesh) return;
      const g = part.geometry;
      triangleCount += (g.index?.count ?? g.getAttribute('position').count) / 3;
    });
    assert.ok(triangleCount < 30000, 'Objetivo para equipos modestos: < 30k triángulos');
    assert.equal(metadata.notAutomaticHumanoidSkinning, true);
    assert.ok(object.getObjectByName('Izquierdo_Hombro')?.userData.neoJoint);
    assert.ok(object.getObjectByName('Derecho_Codo')?.userData.neoJoint);
    assert.ok(object.getObjectByName('Izquierda_Rodilla')?.userData.neoJoint);
    for (let finger = 1; finger <= 5; finger++) {
      assert.ok(object.getObjectByName('Izquierdo_Dedo_' + finger)?.userData.neoJoint);
      assert.ok(object.getObjectByName('Derecho_Dedo_' + finger)?.userData.neoJoint);
    }
    if (type === 'angel') {
      assert.ok(object.getObjectByName('Ala_Izquierda_Articulacion')?.userData.neoJoint);
      assert.ok(object.getObjectByName('Ala_Derecha_Articulacion')?.userData.neoJoint);
    }
    assert.ok(!JSON.stringify(metadata).match(/https?:\/\//), 'No depende de APIs externas');
  }
});

test('Creación web nativa -> animación de codo -> GLB exportable con clip', { timeout: 15000 }, async () => {
  const { object } = createFreeCharacter({ type: 'humanoid', detail: 'low' });
  const elbow = object.getObjectByName('Derecho_Codo');
  const clips = [];
  const fake = {
    objects: [object], selectedObject: elbow,
    characterWorkflow: {
      ensureModel() {}, stopForEdit() {}, getClipsFor() { return clips; },
      registerAuthoredClip(root, clip) { clips.push(clip); }
    },
    logAIAction() {}
  };
  const editor = new AnimationEditor(fake);
  editor.createAction('Mover_Codo', 1, object);
  editor.poseAndRecord({ uuid: elbow.uuid, time: 0, rotationDeg: [0, 0, 0] });
  editor.poseAndRecord({ uuid: elbow.uuid, time: 0.5, rotationDeg: [75, 0, 0] });
  editor.poseAndRecord({ uuid: elbow.uuid, time: 1, rotationDeg: [0, 0, 0] });
  const saved = editor.saveAction();
  assert.equal(saved.tracks, 3);
  assert.equal(clips[0].validate(), true);
  const blob = await new GLTFExporter().parseAsync(object, { binary: true, animations: clips });
  const out = Buffer.from(blob);
  assert.equal(out.toString('utf8', 0, 4), 'glTF');
  assert.ok(out.byteLength < 15 * 1024 * 1024, 'Exportación de modelo base debe ser <15MiB');
  const jsonLength = out.readUInt32LE(12);
  const data = JSON.parse(out.toString('utf8', 20, 20 + jsonLength));
  assert.equal(data.animations[0].name, 'Mover_Codo');
  assert.equal(data.animations[0].channels.length, 3);
});
