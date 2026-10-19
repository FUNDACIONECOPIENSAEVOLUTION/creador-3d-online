import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

/** Minimal browser FileReader API used by Three's exporter in the Node test runner. */
class NodeFileReader {
  result = null;
  onloadend = null;
  onerror = null;
  async readAsArrayBuffer(blob) {
    try { this.result = await blob.arrayBuffer(); this.onloadend?.(); }
    catch (error) { this.onerror?.(error); }
  }
  async readAsDataURL(blob) {
    try {
      const buffer = Buffer.from(await blob.arrayBuffer());
      this.result = 'data:' + (blob.type || 'application/octet-stream') + ';base64,' + buffer.toString('base64');
      this.onloadend?.();
    } catch (error) { this.onerror?.(error); }
  }
}
globalThis.FileReader ||= NodeFileReader;

test('GLB conserva geometría, esqueleto y pistas de animación creadas localmente', { timeout: 10000 }, async () => {
  const root = new THREE.Group();
  root.name = 'Angel_Rig';
  const geometry = new THREE.BoxGeometry(0.3, 1, 0.25, 2, 4, 2);
  const count = geometry.attributes.position.count;
  const indices = [], weights = [];
  const positions = geometry.attributes.position;
  for (let i = 0; i < count; i++) {
    const v = THREE.MathUtils.clamp(positions.getY(i) + 0.5, 0, 1);
    indices.push(0, 1, 0, 0);
    weights.push(1 - v, v, 0, 0);
  }
  geometry.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(indices, 4));
  geometry.setAttribute('skinWeight', new THREE.Float32BufferAttribute(weights, 4));
  const mesh = new THREE.SkinnedMesh(geometry, new THREE.MeshStandardMaterial({ color: 0xffffff }));
  mesh.name = 'Brazo';
  const shoulder = new THREE.Bone();
  shoulder.name = 'Hombro';
  const elbow = new THREE.Bone();
  elbow.name = 'Codo';
  shoulder.add(elbow);
  elbow.position.y = 0.4;
  mesh.add(shoulder);
  mesh.bind(new THREE.Skeleton([shoulder, elbow]));
  root.add(mesh);

  const clip = new THREE.AnimationClip('Ataque_Brazo', 1.2, [
    new THREE.QuaternionKeyframeTrack(elbow.uuid + '.quaternion',
      [0, 0.6, 1.2],
      [...new THREE.Quaternion().toArray(),
        ...new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2).toArray(),
        ...new THREE.Quaternion().toArray()])
  ]);
  assert.equal(clip.validate(), true);
  const result = await new GLTFExporter().parseAsync(root, { binary: true, animations: [clip] });
  const binary = Buffer.from(result);
  assert.equal(binary.toString('utf8', 0, 4), 'glTF');
  const jsonSize = binary.readUInt32LE(12);
  const json = JSON.parse(binary.toString('utf8', 20, 20 + jsonSize));
  assert.equal(json.animations.length, 1);
  assert.equal(json.animations[0].name, 'Ataque_Brazo');
  assert.equal(json.animations[0].channels.length, 1);
  assert.ok(json.skins?.length >= 1);
  const loaded = await new GLTFLoader().parseAsync(result, '');
  assert.equal(loaded.animations[0].name, 'Ataque_Brazo');
  assert.ok(loaded.scene.getObjectByName('Codo')?.isBone);
  assert.ok(loaded.scene.getObjectByName('Brazo')?.isSkinnedMesh);
});
