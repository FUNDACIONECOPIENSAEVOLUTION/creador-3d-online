import * as THREE from 'three';
    import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
    import { TransformControls } from 'three/addons/controls/TransformControls.js';
    import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
    import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
    import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
    import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
    import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
    import { CharacterWorkflow } from './character-workflow.js';
    import { AnimationEditor } from './animation-editor.js';

    class Creador3DOnlineStudio {
      constructor() {
        this.container = document.getElementById('viewport-container');
        this.objects = [];
        this.selectedObject = null;
        this.ws = null;
        this.aiActionHistory = [];
        this.characterWorkflow = new CharacterWorkflow(this);
        this.animationEditor = new AnimationEditor(this);

        this.initEngine();
        this.initLightingAndHDRI();
        this.initControls();
        this.initDragAndDrop();
        this.initDefaultScene();
        this.initMCPBridge();
        this.animate();
      }

      initEngine() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x141417);

        this.camera = new THREE.PerspectiveCamera(
          45,
          this.container.clientWidth / this.container.clientHeight,
          0.1,
          1000
        );
        this.camera.position.set(5, 4, 6);

        this.renderer = new THREE.WebGLRenderer({
          antialias: true,
          preserveDrawingBuffer: true,
          powerPreference: 'high-performance'
        });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.15;
        this.container.appendChild(this.renderer.domElement);

        const grid = new THREE.GridHelper(20, 20, 0xea580c, 0x2e2e38);
        grid.position.y = -0.001;
        this.scene.add(grid);

        window.addEventListener('resize', () => this.onResize());
      }

      initLightingAndHDRI() {
        const pmremGenerator = new THREE.PMREMGenerator(this.renderer);
        this.scene.environment = pmremGenerator.fromScene(new RoomEnvironment(), 0.04).texture;

        this.keyLight = new THREE.DirectionalLight(0xfff7ed, 3.5);
        this.keyLight.position.set(6, 10, 6);
        this.keyLight.castShadow = true;
        this.keyLight.shadow.mapSize.set(2048, 2048);
        this.keyLight.shadow.bias = -0.0005;
        this.scene.add(this.keyLight);

        this.rimLight = new THREE.SpotLight(0x38bdf8, 2.5);
        this.rimLight.position.set(-6, 5, -6);
        this.scene.add(this.rimLight);
      }

      initControls() {
        this.orbit = new OrbitControls(this.camera, this.renderer.domElement);
        this.orbit.enableDamping = true;
        this.orbit.dampingFactor = 0.06;

        this.transformControl = new TransformControls(this.camera, this.renderer.domElement);
        this.transformControl.addEventListener('dragging-changed', (e) => {
          this.orbit.enabled = !e.value;
        });
        this.transformControl.addEventListener('change', () => {
          if (this.selectedObject) this.syncInspectorFromObject();
        });
        this.scene.add(this.transformControl);

        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();

        this.renderer.domElement.addEventListener('pointerdown', (e) => {
          if (e.button !== 0 || this.transformControl.dragging) return;
          const rect = this.renderer.domElement.getBoundingClientRect();
          this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
          this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

          this.raycaster.setFromCamera(this.mouse, this.camera);
          const intersects = this.raycaster.intersectObjects(this.objects, true);
          if (intersects.length > 0) {
            let target = intersects[0].object;
            while (target.parent && target.parent !== this.scene && !this.objects.includes(target)) {
              target = target.parent;
            }
            this.selectObject(target);
          }
        });

        window.addEventListener('keydown', (e) => {
          if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') return;
          const key = e.key.toLowerCase();
          if (key === 'g') this.setTransformMode('translate');
          if (key === 'r') this.setTransformMode('rotate');
          if (key === 's') this.setTransformMode('scale');
          if (key === 'd') this.duplicateSelected();
          if (e.key === 'Delete' || e.key === 'Backspace') this.deleteSelected();
        });
      }

      initDragAndDrop() {
        this.container.addEventListener('dragover', (e) => e.preventDefault());
        this.container.addEventListener('drop', (e) => {
          e.preventDefault();
          const file = e.dataTransfer.files[0];
          if (file && (/\.(glb|gltf|obj|fbx)$/i.test(file.name))) {
            this.loadGLBFile(file);
          }
        });
      }

      initDefaultScene() {
        const floorGeo = new THREE.PlaneGeometry(20, 20);
        const floorMat = new THREE.MeshPhysicalMaterial({
          color: 0x1c1c22,
          roughness: 0.35,
          metalness: 0.1,
          clearcoat: 0.2
        });
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.receiveShadow = true;
        floor.name = 'Studio_Floor';
        this.registerMesh(floor, false);

        this.addHyperRealisticAssembly();
      }

      registerMesh(mesh, select = true) {
        mesh.traverse((node) => {
          if (node.isMesh) {
            node.castShadow = true;
            node.receiveShadow = true;
          }
        });
        this.scene.add(mesh);
        this.objects.push(mesh);
        this.refreshOutliner();
        if (select) this.selectObject(mesh);
        return mesh;
      }

      addPrimitive(type, customParams = {}) {
        let geo;
        const prefix = type.charAt(0).toUpperCase() + type.slice(1);
        switch (type) {
          case 'sphere':
            geo = new THREE.SphereGeometry(customParams.radius || 0.9, 64, 64);
            break;
          case 'box':
            geo = new THREE.BoxGeometry(1.4, 1.4, 1.4, 8, 8, 8);
            break;
          case 'cylinder':
            geo = new THREE.CylinderGeometry(0.8, 0.8, 1.8, 64, 16);
            break;
          case 'torusknot':
          default:
            geo = new THREE.TorusKnotGeometry(0.75, 0.24, 160, 32);
            break;
        }

        const mat = new THREE.MeshPhysicalMaterial({
          color: customParams.color ?? 0xea580c,
          metalness: customParams.metalness ?? 0.7,
          roughness: customParams.roughness ?? 0.15,
          clearcoat: customParams.clearcoat ?? 0.8,
          transmission: customParams.transmission ?? 0.0,
          ior: customParams.ior ?? 1.5,
          thickness: 1.5
        });

        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(
          customParams.x ?? (Math.random() - 0.5) * 2,
          customParams.y ?? 1.1,
          customParams.z ?? (Math.random() - 0.5) * 2
        );
        mesh.name = customParams.name || `${prefix}_${this.objects.length}`;
        this.logAIAction(`Creado objeto ${mesh.name} (${type})`);
        return this.registerMesh(mesh, true);
      }

      addHyperRealisticAssembly() {
        const core = this.addPrimitive('torusknot', {
          name: 'Nucleo_Oro_PBR',
          color: 0xffb703,
          metalness: 1.0,
          roughness: 0.08,
          clearcoat: 1.0,
          x: 0, y: 1.2, z: 0
        });

        const glassShellGeo = new THREE.SphereGeometry(1.45, 64, 64);
        const glassShellMat = new THREE.MeshPhysicalMaterial({
          color: 0xffffff,
          metalness: 0.0,
          roughness: 0.02,
          transmission: 0.95,
          ior: 1.52,
          thickness: 2.0,
          clearcoat: 1.0
        });
        const shell = new THREE.Mesh(glassShellGeo, glassShellMat);
        shell.position.set(2.4, 1.45, 0);
        shell.name = 'Orbe_Cristal_Refractor';
        this.registerMesh(shell, false);
        this.selectObject(core);
      }

      duplicateSelected() {
        if (!this.selectedObject || this.selectedObject.name === 'Studio_Floor') return;
        if (this.selectedObject.isSkinnedMesh || this.selectedObject.getObjectByProperty('type', 'SkinnedMesh')) {
          this.setStatus('Duplicar personajes riggeados requiere clonación de esqueletos (pendiente).');
          return;
        }
        const clone = this.selectedObject.clone(true);
        clone.traverse((node) => {
          if (node.isMesh && node.material) {
            node.material = Array.isArray(node.material)
              ? node.material.map(m => m.clone())
              : node.material.clone();
          }
        });
        clone.position.x += 0.8;
        clone.name = this.selectedObject.name + '_Copy';
        this.registerMesh(clone, true);
      }

      subdivideSelected() {
        if (!this.selectedObject || !this.selectedObject.geometry) return;
        const obj = this.selectedObject;
        if (obj.geometry.type === 'SphereGeometry') {
          obj.geometry.dispose();
          obj.geometry = new THREE.SphereGeometry(0.9, 128, 128);
          this.setStatus(`Geometría de ${obj.name} refinada a 128x128 segmentos.`);
        } else if (obj.geometry.type === 'BoxGeometry') {
          obj.geometry.dispose();
          obj.geometry = new THREE.BoxGeometry(1.4, 1.4, 1.4, 32, 32, 32);
          this.setStatus(`Geometría de ${obj.name} refinada a 32x32x32 segmentos.`);
        } else {
          obj.geometry.computeVertexNormals();
          this.setStatus(`Normales recalculadas para ${obj.name}.`);
        }
      }

      applyProceduralBump(style) {
        if (!this.selectedObject || !this.selectedObject.material) return;
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 256;
        const ctx = canvas.getContext('2d');
        const imgData = ctx.createImageData(256, 256);
        for (let i = 0; i < imgData.data.length; i += 4) {
          let val = style === 'mineral'
            ? Math.floor(Math.random() * 255)
            : Math.floor(128 + Math.sin(i / 32) * 80 + (Math.random() * 30));
          imgData.data[i] = val;
          imgData.data[i + 1] = val;
          imgData.data[i + 2] = val;
          imgData.data[i + 3] = 255;
        }
        ctx.putImageData(imgData, 0, 0);
        const tex = new THREE.CanvasTexture(canvas);
        tex.wrapS = THREE.RepeatWrapping;
        tex.wrapT = THREE.RepeatWrapping;
        tex.repeat.set(4, 4);

        this.selectedObject.material.bumpMap = tex;
        this.selectedObject.material.bumpScale = style === 'mineral' ? 0.035 : 0.015;
        this.selectedObject.material.needsUpdate = true;
        this.setStatus(`Textura procedural (${style}) aplicada a ${this.selectedObject.name}`);
      }

      selectObject(obj) {
        this.selectedObject = obj;
        this.transformControl.attach(obj);
        this.characterWorkflow.selectModel(obj);
        this.syncInspectorFromObject();
        this.animationEditor.updateControls();
        this.refreshOutliner();
        this.setStatus(`Seleccionado: ${obj.name}`);
      }

      deleteSelected() {
        const target = this.selectedObject;
        if (!target || target.name === 'Studio_Floor') return;
        if (target.isBone) {
          this.setStatus('No se puede borrar un hueso de un rig importado: destruiría la deformación del personaje.');
          return;
        }
        this.transformControl.detach();
        this.characterWorkflow.forget(target);
        if (target.parent) target.parent.remove(target);
        this.objects = this.objects.filter(o => o !== target);
        this.selectedObject = null;
        this.refreshOutliner();
        this.setStatus('Objeto eliminado de la escena.');
      }

      setTransformMode(mode) {
        this.transformControl.setMode(mode);
        ['translate', 'rotate', 'scale'].forEach((m) => {
          document.getElementById(`btn-${m}`).classList.toggle('active', m === mode);
        });
      }

      syncInspectorFromObject() {
        const obj = this.selectedObject;
        if (!obj) return;
        document.getElementById('prop-name').value = obj.name;
        document.getElementById('pos-x').value = obj.position.x.toFixed(2);
        document.getElementById('pos-y').value = obj.position.y.toFixed(2);
        document.getElementById('pos-z').value = obj.position.z.toFixed(2);

        document.getElementById('rot-x').value = THREE.MathUtils.radToDeg(obj.rotation.x).toFixed(0);
        document.getElementById('rot-y').value = THREE.MathUtils.radToDeg(obj.rotation.y).toFixed(0);
        document.getElementById('rot-z').value = THREE.MathUtils.radToDeg(obj.rotation.z).toFixed(0);

        document.getElementById('scl-x').value = obj.scale.x.toFixed(2);
        document.getElementById('scl-y').value = obj.scale.y.toFixed(2);
        document.getElementById('scl-z').value = obj.scale.z.toFixed(2);

        const chosenMaterial = Array.isArray(obj.material) ? obj.material[0] : obj.material;
        if (chosenMaterial && chosenMaterial.color) {
          document.getElementById('mat-color').value = '#' + chosenMaterial.color.getHexString();
          document.getElementById('mat-metalness').value = chosenMaterial.metalness ?? 0;
          document.getElementById('mat-roughness').value = chosenMaterial.roughness ?? 0.5;
          document.getElementById('mat-clearcoat').value = chosenMaterial.clearcoat ?? 0;
          document.getElementById('mat-transmission').value = chosenMaterial.transmission ?? 0;
          document.getElementById('mat-ior').value = chosenMaterial.ior ?? 1.5;
          document.getElementById('mat-wireframe').checked = !!chosenMaterial.wireframe;
        }
      }

      updateSelectedTransform() {
        const obj = this.selectedObject;
        if (!obj) return;
        obj.name = document.getElementById('prop-name').value || obj.name;
        obj.position.set(
          parseFloat(document.getElementById('pos-x').value) || 0,
          parseFloat(document.getElementById('pos-y').value) || 0,
          parseFloat(document.getElementById('pos-z').value) || 0
        );
        obj.rotation.set(
          THREE.MathUtils.degToRad(parseFloat(document.getElementById('rot-x').value) || 0),
          THREE.MathUtils.degToRad(parseFloat(document.getElementById('rot-y').value) || 0),
          THREE.MathUtils.degToRad(parseFloat(document.getElementById('rot-z').value) || 0)
        );
        obj.scale.set(
          parseFloat(document.getElementById('scl-x').value) || 1,
          parseFloat(document.getElementById('scl-y').value) || 1,
          parseFloat(document.getElementById('scl-z').value) || 1
        );
        this.refreshOutliner();
      }

      updateSelectedMaterial() {
        const obj = this.selectedObject;
        if (!obj?.material) { this.setStatus('Selecciona una malla con material.'); return; }
        const material = Array.isArray(obj.material) ? obj.material[0] : obj.material;
        if (!material?.color) return;
        material.color.set(document.getElementById('mat-color').value);
        material.metalness = parseFloat(document.getElementById('mat-metalness').value);
        material.roughness = parseFloat(document.getElementById('mat-roughness').value);
        material.clearcoat = parseFloat(document.getElementById('mat-clearcoat').value);
        material.transmission = parseFloat(document.getElementById('mat-transmission').value);
        material.ior = parseFloat(document.getElementById('mat-ior').value);
        material.wireframe = document.getElementById('mat-wireframe').checked;
        material.needsUpdate = true;
      }

      applyMaterialPreset(preset) {
        const obj = this.selectedObject;
        const m = Array.isArray(obj?.material) ? obj.material[0] : obj?.material;
        if (!m?.color) { this.setStatus('Selecciona una malla con material.'); return; }
        const presets = {
          gold:     { color: '#ffb703', metalness: 1.0, roughness: 0.08, clearcoat: 0.5, transmission: 0.0, ior: 1.5 },
          glass:    { color: '#ffffff', metalness: 0.0, roughness: 0.02, clearcoat: 1.0, transmission: 0.96, ior: 1.52 },
          ceramic:  { color: '#f8fafc', metalness: 0.05, roughness: 0.12, clearcoat: 1.0, transmission: 0.0, ior: 1.6 },
          clay:     { color: '#b45309', metalness: 0.0, roughness: 0.82, clearcoat: 0.08, transmission: 0.0, ior: 1.45 },
          charcoal: { color: '#18181b', metalness: 0.15, roughness: 0.65, clearcoat: 0.25, transmission: 0.0, ior: 1.5 },
          honey:    { color: '#f59e0b', metalness: 0.0, roughness: 0.06, clearcoat: 1.0, transmission: 0.88, ior: 1.49 }
        };
        const p = presets[preset];
        if (!p) return;
        m.color.set(p.color);
        m.metalness = p.metalness;
        m.roughness = p.roughness;
        m.clearcoat = p.clearcoat;
        m.transmission = p.transmission;
        m.ior = p.ior;
        m.needsUpdate = true;
        this.syncInspectorFromObject();
      }

      updateEnvironment() {
        this.renderer.toneMappingExposure = parseFloat(document.getElementById('env-exposure').value);
        this.keyLight.intensity = parseFloat(document.getElementById('light-intensity').value);
      }

      refreshOutliner() {
        const list = document.getElementById('outliner');
        list.replaceChildren();
        let count = 0;
        for (const root of this.objects) {
          root.traverse((obj) => {
            if ((obj.isBone && !document.getElementById('show-bones')?.checked) || obj.isLight || obj.isCamera) return;
            if (count >= 450) return;
            count++;
            let depth = 0, parent = obj.parent;
            while (parent && parent !== this.scene && depth < 8) {
              depth++;
              parent = parent.parent;
            }
            const item = document.createElement('div');
            item.className = 'outliner-item' + (obj === this.selectedObject ? ' selected' : '');
            item.style.paddingLeft = (8 + depth * 12) + 'px';
            const label = document.createElement('span');
            label.textContent = (depth ? '↳ ' : '📦 ') + (obj.name || obj.type);
            const type = document.createElement('span');
            type.style.color = 'var(--text-muted)';
            type.style.fontSize = '10px';
            type.textContent = obj.isSkinnedMesh ? 'SkinnedMesh' : obj.isMesh ? 'Mesh' : obj.type;
            item.append(label, type);
            item.addEventListener('click', () => this.selectObject(obj));
            list.appendChild(item);
          });
        }
        document.getElementById('obj-count').textContent = count + ' objs';
      }

      importGLB(event) {
        const file = event.target.files[0];
        if (file) this.loadGLBFile(file);
        event.target.value = '';
      }

      loadGLBFile(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['glb', 'gltf', 'obj', 'fbx'].includes(ext)) {
          this.setStatus('Importación disponible para .glb, .gltf, .obj y .fbx.');
          return;
        }
        if (file.size > 100 * 1024 * 1024) {
          this.setStatus('El archivo supera el límite de 100 MB.');
          return;
        }
        const reader = new FileReader();
        reader.onerror = () => this.setStatus('Error leyendo el archivo importado.');
        const imported = (root, clips = []) => {
          root.name = file.name.replace(/\.(glb|gltf|obj|fbx)$/i, '');
          this.registerMesh(root, true);
          this.characterWorkflow.registerImportedModel(root, clips);
          this.logAIAction('Importado ' + ext.toUpperCase() + ' ' + root.name);
          this.setStatus('Importado: ' + root.name + '. Ahora puedes animarlo con poses y fotogramas.');
        };
        reader.onload = event => {
          try {
            if (ext === 'obj') {
              imported(new OBJLoader().parse(event.target.result));
            } else if (ext === 'fbx') {
              const root = new FBXLoader().parse(event.target.result, '');
              imported(root, root.animations || []);
            } else {
              new GLTFLoader().parse(event.target.result, '', gltf => {
                imported(gltf.scene, gltf.animations || []);
              }, err => this.setStatus('Error en GLB/GLTF: ' + err.message + '. Empaqueta texturas externas.'));
            }
          } catch (err) {
            this.setStatus('No se pudo importar ' + ext.toUpperCase() + ': ' + err.message);
          }
        };
        if (ext === 'obj') reader.readAsText(file);
        else reader.readAsArrayBuffer(file);
      }

      exportGLB() {
        const roots = this.objects.filter(o => o.name !== 'Studio_Floor');
        if (!roots.length) {
          this.setStatus('No hay modelos para exportar.');
          return;
        }
        const exporter = new GLTFExporter();
        const clips = this.characterWorkflow.getExportClips();
        exporter.parse(
          roots,
          (result) => {
            const blob = new Blob([result], { type: 'model/gltf-binary' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'modelo_creador3d_ecopiensa.glb';
            link.click();
            setTimeout(() => URL.revokeObjectURL(url), 3000);
            const sizeMB = (blob.size / 1048576).toFixed(2);
            this.setStatus('Exportado GLB (' + sizeMB + ' MB, ' + clips.length + ' clips). Meta AR: ≤ 15 MB; aún no hay compresión automática.');
          },
          (err) => this.setStatus('No se pudo exportar el GLB: ' + err.message),
          { binary: true, animations: clips }
        );
      }

      async handleReferenceChange(event) {
        try {
          await this.characterWorkflow.loadReference(event.target.files[0]);
        } catch (error) {
          this.setStatus(error.message);
        }
        event.target.value = '';
      }

      downloadCreationBrief() {
        try {
          this.characterWorkflow.downloadBrief();
        } catch (error) {
          this.setStatus(error.message);
        }
      }

      playAnimation(index) {
        try { this.characterWorkflow.play(index); }
        catch (error) { this.setStatus(error.message); }
      }

      pauseAnimation() { this.characterWorkflow.pause(); this.setStatus('Animación en pausa.'); }
      resumeAnimation() { this.characterWorkflow.resume(); this.setStatus('Animación reanudada.'); }
      setAnimationSpeed(value) { this.characterWorkflow.setSpeed(value); }

      animationErrorSafe(action) {
        try {
          const response = action();
          this.setStatus(typeof response === 'string' ? response : JSON.stringify(response));
          this.refreshOutliner();
          return response;
        } catch (error) {
          this.setStatus('Animación: ' + error.message);
          return null;
        }
      }

      createAnimationAction() {
        return this.animationErrorSafe(() => this.animationEditor.createAction(
          document.getElementById('new-animation-name').value,
          Number(document.getElementById('new-animation-duration').value)
        ));
      }

      addAnimationKeyframe() {
        return this.animationErrorSafe(() => this.animationEditor.poseAndRecord({
          time: Number(document.getElementById('keyframe-time').value)
        }));
      }

      removeAnimationKeyframe() {
        return this.animationErrorSafe(() => this.animationEditor.deleteFrame(
          this.selectedObject?.uuid, Number(document.getElementById('keyframe-time').value)
        ));
      }

      saveAnimationAction() {
        return this.animationErrorSafe(() => this.animationEditor.saveAction());
      }

      createAnimationPreset() {
        return this.animationErrorSafe(() => this.animationEditor.makeRigidPreset(
          document.getElementById('animation-preset').value
        ));
      }

      createArticulation() {
        return this.animationErrorSafe(() => this.animationEditor.addPivot({
          worldPosition: ['pivot-x', 'pivot-y', 'pivot-z'].map(id => Number(document.getElementById(id).value))
        }));
      }

      previewAnimationTime(time) {
        const t = Number(time);
        if (!Number.isFinite(t)) return;
        this.animationEditor.playhead = t;
        this.characterWorkflow.seek(t);
        this.animationEditor.updateControls();
      }

      getSceneGraphData() {
        const objects = [];
        this.objects.forEach(root => root.traverse(o => {
          if (objects.length >= 1500) return;
          const material = Array.isArray(o.material) ? o.material[0] : o.material;
          objects.push({
            uuid: o.uuid, parentUuid: o.parent?.uuid || null,
            name: o.name, objectType: o.type,
            geometry: o.geometry?.type || null,
            position: o.position.toArray().map(n => Number(n.toFixed(3))),
            rotation: [o.rotation.x, o.rotation.y, o.rotation.z].map(n => Number(n.toFixed(3))),
            scale: o.scale.toArray().map(n => Number(n.toFixed(3))),
            bones: o.isSkinnedMesh ? o.skeleton.bones.length : 0,
            material: material?.color ? {
              color: '#' + material.color.getHexString(),
              metalness: material.metalness ?? 0,
              roughness: material.roughness ?? 0.5
            } : null
          });
        }));
        return {
          timestamp: new Date().toISOString(),
          camera: { position: this.camera.position.toArray(), target: this.orbit.target.toArray() },
          objects
        };
      }

      logAIAction(summary) {
        this.aiActionHistory.push({
          time: new Date().toISOString(),
          summary
        });
      }

      generateAIMarkdownLog() {
        const dateStr = new Date().toISOString().split('T')[0];
        const summary = this.aiActionHistory.slice(-3).map(a => a.summary).join('; ') || 'Ajuste de escena y materiales PBR';
        const mdRow = `| ${dateStr} | **Agente MCP Activo** | ${summary} (${this.objects.length} objetos en escena). | \`src/studio.js\` | Continuar refinamiento geométrico o texturizado PBR. |`;
        document.getElementById('mcp-console').value = mdRow;
        this.setStatus('Fila Markdown generada para pegar en MCP_AI_GUIDE.md');
      }

      /* ========================================================
         PUENTE MCP (MODEL CONTEXT PROTOCOL) CON VISIÓN CUÁDRUPLE
         ======================================================== */
      initMCPBridge() {
        const self = this;
        window.MCP_BRIDGE = {
          version: '1.3.0',
          repository: 'https://github.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online',
          listTools() {
            return [
              { name: 'mcp_get_scene_graph', description: 'Devuelve el grafo completo de objetos 3D, cámara y materiales PBR.' },
              { name: 'mcp_capture_viewport', description: 'Captura la vista actual en Base64 PNG.' },
              { name: 'mcp_capture_quad_view', description: 'Captura 4 ángulos simultáneos (Perspectiva, Frontal, Superior, Lateral) en un solo collage PNG Base64 para análisis espacial 3D de la IA.' },
              { name: 'mcp_spawn_pbr_mesh', description: 'Crea una nueva malla 3D con shader físico MeshPhysicalMaterial.' },
              { name: 'mcp_modify_object', description: 'Modifica posición, escala o material de un objeto existente.' },
              { name: 'mcp_get_creation_brief', description: 'Lee el encargo de creación de personaje y los requisitos.' },
              { name: 'mcp_get_reference_image', description: 'Obtiene la imagen de referencia en JPEG para análisis visual.' },
              { name: 'mcp_animation_inspect', description: 'Inspecciona huesos, articulaciones, clips y fotogramas del modelo.' },
              { name: 'mcp_animation_create', description: 'Crear una acción nueva para un modelo.' },
              { name: 'mcp_animation_keyframe', description: 'Registrar fotograma clave de un hueso o pieza individual con tiempo, posición y rotación.' },
              { name: 'mcp_animation_commit', description: 'Convertir los fotogramas a AnimationClip glTF exportable.' },
              { name: 'mcp_animation_preset', description: 'Movimiento básico gratis de pieza completa.' },
              { name: 'mcp_animation_pivot', description: 'Crear articulación en una extremidad de malla separada.' }
            ];
          },
          getSceneGraph() {
            return self.getSceneGraphData();
          },
          captureViewport() {
            self.renderer.render(self.scene, self.camera);
            const dataUrl = self.renderer.domElement.toDataURL('image/png');
            const box = document.getElementById('vision-box');
            box.innerHTML = `<img src="${dataUrl}" alt="MCP Vision" /><span class="vision-label">1-Vista ${new Date().toLocaleTimeString()}</span>`;
            return { mimeType: 'image/png', mode: 'single', dataUrl };
          },
          captureQuadView() {
            const quadCanvas = document.createElement('canvas');
            quadCanvas.width = 800;
            quadCanvas.height = 600;
            const ctx = quadCanvas.getContext('2d');
            const bounds = new THREE.Box3();
            self.objects.filter(o => o.name !== 'Studio_Floor').forEach(o => bounds.expandByObject(o));
            const center = bounds.isEmpty() ? new THREE.Vector3(0, 1, 0) : bounds.getCenter(new THREE.Vector3());
            const size = bounds.isEmpty() ? 3 : Math.max(3, ...bounds.getSize(new THREE.Vector3()).toArray());
            const halfWidth = size * 0.8;
            const halfHeight = size * 0.6;
            const views = [
              { label: 'PERSPECTIVA', camera: self.camera },
              { label: 'FRONTAL (Z+)', pos: center.clone().add(new THREE.Vector3(0, 0, 10)) },
              { label: 'SUPERIOR (Y+)', pos: center.clone().add(new THREE.Vector3(0, 10, 0.001)) },
              { label: 'LATERAL (X+)', pos: center.clone().add(new THREE.Vector3(10, 0, 0)) }
            ];
            for (let i = 0; i < views.length; i++) {
              const view = views[i];
              let activeCamera = view.camera;
              if (!activeCamera) {
                activeCamera = new THREE.OrthographicCamera(-halfWidth, halfWidth, halfHeight, -halfHeight, 0.01, 1000);
                activeCamera.position.copy(view.pos);
                activeCamera.lookAt(center);
                activeCamera.updateProjectionMatrix();
              }
              self.renderer.render(self.scene, activeCamera);
              const x = (i % 2) * 400, y = Math.floor(i / 2) * 300;
              ctx.drawImage(self.renderer.domElement, x, y, 400, 300);
              ctx.fillStyle = 'rgba(0,0,0,0.65)';
              ctx.fillRect(x + 6, y + 6, 130, 20);
              ctx.fillStyle = '#10b981';
              ctx.font = 'bold 11px sans-serif';
              ctx.fillText(view.label, x + 12, y + 20);
            }
            // No se mueve la cámara interactiva: OrbitControls mantiene su estado.
            self.renderer.render(self.scene, self.camera);
            const dataUrl = quadCanvas.toDataURL('image/png');
            const box = document.getElementById('vision-box');
            box.replaceChildren();
            const preview = document.createElement('img');
            preview.src = dataUrl;
            preview.alt = '4 vistas del modelo';
            const label = document.createElement('span');
            label.className = 'vision-label';
            label.textContent = '4 Vistas IA';
            box.append(preview, label);
            return { mimeType: 'image/png', mode: 'quad_orthographic', dataUrl };
          },
          modifyObject(params = {}) {
            if (typeof params.name !== 'string' && typeof params.uuid !== 'string')
              throw new Error('Indica nombre o UUID del objeto.');
            let target = null;
            for (const root of self.objects) {
              root.traverse((node) => {
                if (!target && (node.name === params.name || node.uuid === params.uuid)) target = node;
              });
              if (target) break;
            }
            if (!target || target.name === 'Studio_Floor') throw new Error('Objeto no editable o inexistente.');
            const vector = (value, label, limit) => {
              if (!Array.isArray(value) || value.length !== 3 ||
                  !value.every(v => typeof v === 'number' && Number.isFinite(v) && Math.abs(v) <= limit)) {
                throw new Error(label + ' requiere tres números válidos.');
              }
              return value;
            };
            if (params.position !== undefined) target.position.fromArray(vector(params.position, 'position', 10000));
            if (params.scale !== undefined) target.scale.fromArray(vector(params.scale, 'scale', 1000));
            const material = Array.isArray(target.material) ? target.material[0] : target.material;
            if (params.color !== undefined || params.metalness !== undefined ||
                params.roughness !== undefined || params.transmission !== undefined) {
              if (!material?.color) throw new Error('Selecciona una malla con material, no un Group.');
              if (params.color !== undefined) {
                if (!/^#[0-9a-fA-F]{6}$/.test(params.color)) throw new Error('Color hexadecimal inválido.');
                material.color.set(params.color);
              }
              for (const name of ['metalness', 'roughness', 'transmission']) {
                if (params[name] === undefined) continue;
                if (typeof params[name] !== 'number' || !Number.isFinite(params[name]) ||
                    params[name] < 0 || params[name] > 1) throw new Error(name + ' fuera de rango.');
                material[name] = params[name];
              }
              material.needsUpdate = true;
            }
            if (self.selectedObject === target) self.syncInspectorFromObject();
            self.logAIAction('Modificado objeto ' + target.name);
            return { status: 'updated', name: target.name, uuid: target.uuid };
          },
          handleJsonRpc(request) {
            const { id, method, params = {} } = request;
            try {
              let result;
              if (method === 'tools/list') result = this.listTools();
              else if (method === 'mcp_get_scene_graph') result = this.getSceneGraph();
              else if (method === 'mcp_capture_viewport') result = this.captureViewport();
              else if (method === 'mcp_capture_quad_view') result = this.captureQuadView();
              else if (method === 'mcp_get_creation_brief') result = self.characterWorkflow.getBrief();
              else if (method === 'mcp_get_reference_image') result = self.characterWorkflow.getImage();
              else if (method === 'mcp_animation_inspect') result = self.animationEditor.inspect();
              else if (method === 'mcp_animation_create') result = self.animationEditor.createAction(
                params.name, params.duration,
                params.rootUuid ? self.animationEditor.resolve(params.rootUuid) : self.selectedObject
              );
              else if (method === 'mcp_animation_keyframe') result = self.animationEditor.poseAndRecord(params);
              else if (method === 'mcp_animation_commit') result = self.animationEditor.saveAction();
              else if (method === 'mcp_animation_preset') result = self.animationEditor.makeRigidPreset(params.kind);
              else if (method === 'mcp_animation_pivot') result = self.animationEditor.addPivot(params);
              else if (method === 'mcp_spawn_pbr_mesh') {
                const mesh = self.addPrimitive(params.type || 'sphere', params);
                result = { status: 'created', name: mesh.name, uuid: mesh.uuid };
              } else if (method === 'mcp_modify_object') {
                result = this.modifyObject(params);
              } else if (method === 'mcp_execute_three_code') {
                throw new Error('Ejecución arbitraria de JavaScript deshabilitada por seguridad; usa herramientas MCP declarativas.');
              } else {
                throw new Error(`Método MCP desconocido: ${method}`);
              }
              return { jsonrpc: '2.0', id, result };
            } catch (err) {
              return { jsonrpc: '2.0', id, error: { code: -32603, message: err.message } };
            }
          }
        };

        document.getElementById('mcp-console').value = JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "mcp_spawn_pbr_mesh",
          params: {
            type: "torusknot",
            name: "Escultura_IA_Ecopiensa",
            color: "#10b981",
            metalness: 0.92,
            roughness: 0.06,
            clearcoat: 1.0,
            x: -2.2,
            y: 1.3,
            z: 0
          }
        }, null, 2);
      }

      mcpCaptureVision() {
        const snap = window.MCP_BRIDGE.captureViewport();
        this.setStatus(`Captura simple lista (${Math.round(snap.dataUrl.length / 1024)} KB).`);
      }

      mcpCaptureQuadVision() {
        const snap = window.MCP_BRIDGE.captureQuadView();
        this.setStatus(`Captura 4-Vistas (Perspectiva/Frontal/Superior/Lateral) lista para IA (${Math.round(snap.dataUrl.length / 1024)} KB).`);
      }

      mcpDumpScene() {
        const graph = window.MCP_BRIDGE.getSceneGraph();
        document.getElementById('mcp-console').value = JSON.stringify(graph, null, 2);
        this.setStatus('Grafo de escena serializado en consola MCP.');
      }

      runMCPConsoleCommand() {
        const raw = document.getElementById('mcp-console').value.trim();
        try {
          const payload = JSON.parse(raw);
          const response = window.MCP_BRIDGE.handleJsonRpc(payload);
          this.setStatus(`Comando MCP ejecutado: ${payload.method}`);
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(response));
          }
        } catch (e) {
          this.setStatus(`Error JSON-RPC: ${e.message}`);
        }
      }

      connectMCPSocket() {
        const url = document.getElementById('ws-url').value;
        try {
          this.ws = new WebSocket(url);
          this.ws.onopen = () => {
            document.getElementById('ws-state').textContent = 'Conectado a MCP Server';
            document.getElementById('ws-state').style.color = '#10b981';
            this.setStatus(`Conectado al servidor MCP en ${url}`);
          };
          this.ws.onmessage = (event) => {
            const req = JSON.parse(event.data);
            const res = window.MCP_BRIDGE.handleJsonRpc(req);
            this.ws.send(JSON.stringify(res));
          };
          this.ws.onerror = () => {
            document.getElementById('ws-state').textContent = 'Modo DOM Local';
            this.setStatus(`Sin servidor local activo en ${url}. Usando window.MCP_BRIDGE directo.`);
          };
        } catch (err) {
          this.setStatus(`Error WebSocket: ${err.message}`);
        }
      }

      setStatus(msg) {
        document.getElementById('status-bar').textContent = msg;
      }

      onResize() {
        this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
      }

      animate() {
        requestAnimationFrame(() => this.animate());
        this.characterWorkflow.update();
        this.orbit.update();
        this.renderer.render(this.scene, this.camera);
      }
    }

    window.app = new Creador3DOnlineStudio();
