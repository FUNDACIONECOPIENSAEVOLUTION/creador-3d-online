import * as THREE from 'three';

/**
 * Capabilities deliberately separated from scene editing.
 * A reference image is a CREATION BRIEF, not an automatic image-to-3D service.
 * Actual articulated/photoreal characters must be imported as GLB (or produced
 * by a separate consented Blender/AI pipeline).
 */
export class CharacterWorkflow {
  constructor(studio) {
    this.studio = studio;
    this.imageDataUrl = null;
    this.imageMimeType = null;
    this.animationSets = new Map();
    this.active = null;
    this.clock = new THREE.Clock();
  }

  async loadReference(file) {
    if (!file) return;
    if (!file.type.startsWith('image/') || file.size > 12 * 1024 * 1024) {
      throw new Error('Selecciona una imagen válida de máximo 12 MB.');
    }
    const imageUrl = URL.createObjectURL(file);
    try {
      const image = new Image();
      await new Promise((resolve, reject) => {
        image.onload = resolve;
        image.onerror = () => reject(new Error('La imagen no se puede abrir.'));
        image.src = imageUrl;
      });
      const ratio = Math.min(1, 1024 / Math.max(image.naturalWidth, image.naturalHeight));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(image.naturalWidth * ratio));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * ratio));
      canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
      this.imageMimeType = 'image/jpeg';
      this.imageDataUrl = canvas.toDataURL('image/jpeg', 0.83);
      const preview = document.getElementById('reference-preview');
      preview.src = this.imageDataUrl;
      preview.style.display = 'block';
      this.studio.setStatus('Referencia cargada. Escribe la descripción y comparte el encargo mediante MCP.');
    } finally {
      URL.revokeObjectURL(imageUrl);
    }
  }

  getBrief() {
    const description = document.getElementById('character-prompt').value.trim();
    return {
      schemaVersion: 'ecoblend.brief.v1',
      type: 'universal_3d_reference',
      description,
      intendedUse: document.getElementById('character-use').value,
      exportFormat: 'glb',
      targetMaxMegabytes: 15,
      animationDesired: true,
      rigPreference: 'when_moving_parts_needed',
      referenceImageAvailable: !!this.imageDataUrl,
      blueprintSchema: 'ecoblend.asset.v1',
      instructions: 'Si una IA con visión y MCP está conectada, analizar primero la referencia, identificar objeto, silueta, partes, materiales y articulaciones; generar planos declarativos EcoBlend, previsualizar las cuatro vistas y corregir. MPFB2 es opcional solo para anatomía humana fuera de GitHub Pages. No depender de APIs 3D comerciales.',
      limitations: 'Los comandos locales crean plantillas y geometría por partes; un sistema multimodal conectado debe interpretar la imagen. No hay reconstrucción fotogramétrica ni generación hiperrealista arbitraria automática en la web.'
    };
  }

  getImage() {
    if (!this.imageDataUrl) throw new Error('No se ha cargado una imagen de referencia.');
    return { mimeType: this.imageMimeType, dataUrl: this.imageDataUrl };
  }

  downloadBrief() {
    const brief = { ...this.getBrief(), referenceImageDataUrl: this.imageDataUrl };
    if (!brief.description) throw new Error('Escribe primero la descripción del personaje.');
    const blob = new Blob([JSON.stringify(brief, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'encargo-personaje-3d.json';
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 3000);
    this.studio.setStatus('Encargo descargado: imagen + instrucciones. También está disponible por MCP local.');
  }

  ensureModel(root) {
    if (!root) throw new Error('Selecciona un modelo antes de animarlo.');
    let set = this.animationSets.get(root.uuid);
    if (!set) {
      set = { root, clips: [], mixer: new THREE.AnimationMixer(root) };
      this.animationSets.set(root.uuid, set);
    }
    this.active = root.uuid;
    return set;
  }

  registerImportedModel(root, clips = []) {
    const data = this.ensureModel(root);
    data.clips = [...clips];
    this.populateClips();
    this.studio.setStatus(
      data.clips.length
        ? 'Modelo cargado con ' + data.clips.length + ' clips editables mediante nuevos fotogramas.'
        : 'Modelo sin clips: puedes crear acciones con fotogramas clave sobre sus piezas o huesos.'
    );
  }

  registerAuthoredClip(root, clip) {
    const data = this.ensureModel(root);
    const previous = data.clips.findIndex(item => item.name === clip.name);
    data.mixer.stopAllAction();
    if (previous >= 0) {
      data.mixer.uncacheClip(data.clips[previous]);
      data.clips.splice(previous, 1, clip);
    } else data.clips.push(clip);
    this.populateClips();
    this.studio.setStatus('Animación creada localmente: ' + clip.name + '. Exporta GLB para conservarla.');
  }

  getClipsFor(root) {
    return this.animationSets.get(root.uuid)?.clips || [];
  }

  stopForEdit(root) {
    const data = this.animationSets.get(root.uuid);
    if (data) {
      data.mixer.stopAllAction();
      data.mixer.timeScale = 1;
    }
  }

  selectModel(obj) {
    let parent = obj;
    while (parent && !this.animationSets.has(parent.uuid)) parent = parent.parent;
    if (parent) this.active = parent.uuid;
    else this.active = null;
    this.populateClips();
  }

  populateClips() {
    const select = document.getElementById('animation-list');
    select.replaceChildren();
    const data = this.animationSets.get(this.active);
    if (!data || !data.clips.length) {
      const option = new Option('Sin clips: crea una acción nueva', '');
      select.add(option);
      return;
    }
    select.add(new Option('Elegir animación…', ''));
    data.clips.forEach((clip, i) => select.add(new Option(clip.name || 'Acción ' + (i + 1), String(i))));
  }

  play(index) {
    const data = this.animationSets.get(this.active);
    if (!data || index === '') return;
    const clip = data.clips[Number(index)];
    if (!clip) throw new Error('Clip no encontrado.');
    data.mixer.stopAllAction();
    const action = data.mixer.clipAction(clip);
    action.reset().play();
    data.mixer.timeScale = Number(document.getElementById('animation-speed').value);
    this.studio.setStatus('Reproduciendo: ' + clip.name);
  }

  seek(time) {
    const data = this.animationSets.get(this.active);
    if (!data) return;
    const speed = data.mixer.timeScale;
    data.mixer.timeScale = 1;
    data.mixer.setTime(Math.max(0, Number(time) || 0));
    data.mixer.timeScale = speed;
  }

  pause() {
    const data = this.animationSets.get(this.active);
    if (data) data.mixer.timeScale = 0;
  }

  resume() {
    const data = this.animationSets.get(this.active);
    if (data) data.mixer.timeScale = Number(document.getElementById('animation-speed').value);
  }

  setSpeed(value) {
    const data = this.animationSets.get(this.active);
    if (data && data.mixer.timeScale !== 0) data.mixer.timeScale = Number(value);
  }

  getExportClips() {
    return Array.from(this.animationSets.values()).flatMap((set) => set.clips);
  }

  update() {
    const dt = Math.min(this.clock.getDelta(), 0.1);
    for (const set of this.animationSets.values()) set.mixer.update(dt);
  }

  forget(root) {
    const ids = [];
    root.traverse((node) => { if (this.animationSets.has(node.uuid)) ids.push(node.uuid); });
    for (const id of ids) {
      const item = this.animationSets.get(id);
      item.mixer.stopAllAction();
      item.mixer.uncacheRoot(item.root);
      this.animationSets.delete(id);
      if (this.active === id) this.active = null;
    }
    this.populateClips();
  }
}
