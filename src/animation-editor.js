import * as THREE from 'three';

/**
 * Native, offline Three.js animation authoring.
 * Supports glTF skeleton bones, named child meshes and custom rigid pivots.
 * A single fused mesh cannot bend its limbs until it has skinning weights or is split.
 */
export class AnimationEditor {
  constructor(studio) {
    this.studio = studio;
    this.drafts = new Map();
    this.playhead = 0;
  }

  rootFor(node) {
    let obj = node;
    while (obj && !this.studio.objects.includes(obj)) obj = obj.parent;
    if (!obj || obj.name === 'Studio_Floor') throw new Error('Selecciona un personaje o una pieza de escena.');
    return obj;
  }

  resolve(uuid) {
    if (typeof uuid !== 'string' || uuid.length > 100) throw new Error('UUID inválido.');
    for (const root of this.studio.objects) {
      const found = root.getObjectByProperty('uuid', uuid);
      if (found && found.name !== 'Studio_Floor') return found;
    }
    throw new Error('No existe un objeto con ese UUID en la escena.');
  }

  createAction(name, duration = 2, rootNode = this.studio.selectedObject) {
    if (typeof name !== 'string' || !name.trim() || name.length > 80) throw new Error('Nombre de acción inválido.');
    if (typeof duration !== 'number' || !Number.isFinite(duration) || duration <= 0 || duration > 60)
      throw new Error('La duración debe estar entre 0 y 60 segundos.');
    const root = this.rootFor(rootNode);
    const action = { name: name.trim(), duration, root, channels: new Map() };
    this.drafts.set(root.uuid, action);
    this.studio.characterWorkflow.ensureModel(root);
    this.studio.characterWorkflow.stopForEdit(root);
    this.playhead = 0;
    this.updateControls();
    return this.inspect();
  }

  getDraft(node = this.studio.selectedObject) {
    const root = this.rootFor(node);
    const action = this.drafts.get(root.uuid);
    if (!action) throw new Error('Crea primero una acción con un nombre.');
    return action;
  }

  poseAndRecord({ uuid, time, position, rotationDeg, scale }) {
    const obj = uuid ? this.resolve(uuid) : this.studio.selectedObject;
    if (!obj || obj.name === 'Studio_Floor') throw new Error('Selecciona un objeto o hueso.');
    const action = this.getDraft(obj);
    const t = Number(time);
    if (!Number.isFinite(t) || t < 0 || t > action.duration) throw new Error('Tiempo fuera de la acción.');
    const vector = (value, label, max) => {
      if (!Array.isArray(value) || value.length !== 3 || !value.every(n => typeof n === 'number' && Number.isFinite(n) && Math.abs(n) <= max))
        throw new Error(label + ' debe contener 3 números válidos.');
      return value;
    };
    if (position !== undefined) obj.position.fromArray(vector(position, 'position', 10000));
    if (rotationDeg !== undefined) {
      const v = vector(rotationDeg, 'rotationDeg', 36000);
      obj.rotation.set(...v.map(n => THREE.MathUtils.degToRad(n)));
    }
    if (scale !== undefined) obj.scale.fromArray(vector(scale, 'scale', 1000));
    const current = action.channels.get(obj.uuid) || { node: obj, frames: new Map() };
    current.frames.set(t, {
      time: t,
      position: obj.position.toArray(),
      quaternion: obj.quaternion.toArray(),
      scale: obj.scale.toArray()
    });
    action.channels.set(obj.uuid, current);
    this.playhead = t;
    this.updateControls();
    return {
      action: action.name, node: obj.name, uuid: obj.uuid, time: t,
      keyCount: current.frames.size
    };
  }

  deleteFrame(uuid, time) {
    const node = uuid ? this.resolve(uuid) : this.studio.selectedObject;
    const action = this.getDraft(node);
    const channel = action.channels.get(node.uuid);
    if (!channel || !channel.frames.delete(Number(time))) throw new Error('No existe ese fotograma.');
    if (!channel.frames.size) action.channels.delete(node.uuid);
    this.updateControls();
    return this.inspect();
  }

  buildClip(action) {
    if (!action?.channels?.size) throw new Error('La acción todavía no tiene fotogramas.');
    const tracks = [];
    for (const { node, frames } of action.channels.values()) {
      const sorted = Array.from(frames.values()).sort((a, b) => a.time - b.time);
      const times = sorted.map(frame => frame.time);
      const base = node.uuid; // glTFExporter and AnimationMixer resolve UUID paths.
      tracks.push(new THREE.VectorKeyframeTrack(base + '.position', times, sorted.flatMap(frame => frame.position)));
      tracks.push(new THREE.QuaternionKeyframeTrack(base + '.quaternion', times, sorted.flatMap(frame => frame.quaternion)));
      tracks.push(new THREE.VectorKeyframeTrack(base + '.scale', times, sorted.flatMap(frame => frame.scale)));
    }
    const clip = new THREE.AnimationClip(action.name, action.duration, tracks);
    clip.validate();
    return clip;
  }

  saveAction(node = this.studio.selectedObject) {
    const action = this.getDraft(node);
    const clip = this.buildClip(action);
    this.studio.characterWorkflow.registerAuthoredClip(action.root, clip);
    this.studio.logAIAction('Acción animada creada: ' + clip.name);
    return { name: clip.name, duration: clip.duration, tracks: clip.tracks.length, root: action.root.name };
  }

  inspect() {
    const target = this.studio.selectedObject;
    if (!target || target.name === 'Studio_Floor') return { action: null };
    const root = this.rootFor(target);
    const draft = this.drafts.get(root.uuid);
    const clips = this.studio.characterWorkflow.getClipsFor(root);
    const joints = [];
    root.traverse(obj => {
      if (obj.isBone || obj.userData.neoJoint) joints.push({ uuid: obj.uuid, name: obj.name, type: obj.isBone ? 'bone' : 'pivot' });
    });
    return {
      model: root.name, rootUuid: root.uuid, skinned: !!root.getObjectByProperty('type', 'SkinnedMesh'),
      draft: draft ? {
        name: draft.name, duration: draft.duration,
        frames: Array.from(draft.channels.values()).reduce((n, ch) => n + ch.frames.size, 0)
      } : null,
      clips: clips.map(clip => ({ name: clip.name, duration: clip.duration })),
      joints
    };
  }

  // A pivot is an ordinary transform group. Useful for separated limbs/armor parts.
  // It does not invent skin weights and cannot bend a fused single-mesh character.
  addPivot({ uuid, name = 'Articulacion', worldPosition } = {}) {
    const node = uuid ? this.resolve(uuid) : this.studio.selectedObject;
    if (!node || node.isBone || node.isSkinnedMesh || node.name === 'Studio_Floor')
      throw new Error('Selecciona una pieza rígida independiente (malla o grupo).');
    const root = this.rootFor(node);
    if (node === root && this.studio.characterWorkflow.getClipsFor(root).length)
      throw new Error('No puedes reemplazar la raíz de un modelo con clips existentes; selecciona una pieza hija.');
    const parent = node.parent;
    if (!parent) throw new Error('El objeto no tiene padre.');
    const world = new THREE.Vector3();
    node.getWorldPosition(world);
    if (worldPosition !== undefined) {
      if (!Array.isArray(worldPosition) || worldPosition.length !== 3 ||
          !worldPosition.every(n => typeof n === 'number' && Number.isFinite(n) && Math.abs(n) <= 10000))
        throw new Error('worldPosition inválida.');
      world.fromArray(worldPosition);
    }
    const pivot = new THREE.Group();
    pivot.name = String(name).slice(0, 80) || 'Articulacion';
    pivot.userData.neoJoint = true;
    parent.updateWorldMatrix(true, false);
    pivot.position.copy(parent.worldToLocal(world.clone()));
    parent.add(pivot);
    pivot.attach(node); // Conserva la posición mundial de la pieza.
    const i = this.studio.objects.indexOf(node);
    if (i >= 0) this.studio.objects.splice(i, 1, pivot);
    this.studio.selectObject(pivot);
    this.studio.refreshOutliner();
    return { name: pivot.name, uuid: pivot.uuid, contains: node.name, model: root.name };
  }

  /**
   * Optional FREE procedural motion starter: moves whole model like a chess piece.
   * Arms can be animated separately by keyframing existing bones or rigid pivots.
   */
  makeRigidPreset(kind = 'idle', rootNode = this.studio.selectedObject) {
    const allowed = ['idle', 'attack', 'defend', 'hit', 'defeat'];
    if (!allowed.includes(kind)) throw new Error('Preset no válido.');
    const root = this.rootFor(rootNode);
    const original = { position: root.position.clone(), quaternion: root.quaternion.clone(), scale: root.scale.clone() };
    const samples = {
      idle: [[0,0,0,0,0], [0.8,0,0.04,0.03,0], [1.6,0,0,0,0]],
      attack: [[0,0,0,0,0], [0.3,0,0,-0.12,-0.1], [0.65,0,0,-0.68,0.14], [1.2,0,0,0,0]],
      defend: [[0,0,0,0,0], [0.3,0,0,0,0.2], [0.85,0,0,0,0.2], [1.3,0,0,0,0]],
      hit: [[0,0,0,0,0], [0.25,0,0,0.25,0.16], [0.85,0,0,0,0]],
      defeat: [[0,0,0,0,0], [0.6,0,-0.45,0.2,1], [1.8,0,-0.45,0.2,1]]
    }[kind];
    const tracks = [];
    const times = samples.map(s => s[0]);
    const positions = [], quaternions = [], scales = [];
    for (const [, x, y, z, tilt] of samples) {
      positions.push(...original.position.clone().add(new THREE.Vector3(x, y, z)).toArray());
      const q = original.quaternion.clone().multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), tilt));
      quaternions.push(...q.toArray());
      scales.push(...original.scale.toArray());
    }
    tracks.push(new THREE.VectorKeyframeTrack(root.uuid + '.position', times, positions));
    tracks.push(new THREE.QuaternionKeyframeTrack(root.uuid + '.quaternion', times, quaternions));
    tracks.push(new THREE.VectorKeyframeTrack(root.uuid + '.scale', times, scales));
    const clip = new THREE.AnimationClip('Neo_' + kind, samples.at(-1)[0], tracks);
    this.studio.characterWorkflow.registerAuthoredClip(root, clip);
    return { name: clip.name, type: 'whole_model', note: 'Animación rígida inicial. Para brazos independientes, usa huesos o pivotes.' };
  }

  updateControls() {
    const node = this.studio.selectedObject;
    if (!node || node.name === 'Studio_Floor') return;
    const action = this.drafts.get(this.rootFor(node).uuid);
    const label = document.getElementById('keyframe-state');
    if (label) label.textContent = action
      ? action.name + ': ' + Array.from(action.channels.values()).reduce((n, ch) => n + ch.frames.size, 0) + ' fotogramas registrados'
      : 'Crea una acción para registrar poses';
    const slider = document.getElementById('keyframe-time');
    if (slider) {
      slider.max = String(action?.duration ?? 2);
      slider.value = String(Math.min(this.playhead, Number(slider.max)));
    }
  }
}
