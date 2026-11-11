# Propuesta técnica ChatGPT — NeoBlender Web 3D, edición web + personajes realistas + MCP seguro

**Fecha:** 2026-10-19  
**Autor:** ChatGPT (GPT-6)  
**Estado:** PROPUESTA EN REVISIÓN. No equivale a aprobación ni a implementación.  
**Rama:** propuesta/chatgpt-neoblender-2026-10-19  
**Alcance de esta contribución:** documentos únicamente; NO se modifica index.html, NO se publica una versión nueva ni se inicia ningún servicio.

## 1. Objetivo y criterios

Convertir el prototipo NeoBlender Web 3D en un **estudio de personajes 3D orientado a videojuegos**, utilizable desde navegador, con una interfaz de creación guiada, edición manual, vistas/mediciones/validación por IA y exportación GLB/GLTF eficiente. Enfocar primero personajes humanos anatómicamente coherentes, después piezas para ajedrez fantástico y criaturas/objetos.

**Objetivos verificables:**
1. Importar y previsualizar un personaje humano con texturas, esqueleto y animación sin romper la escena.
2. Crear un personaje a partir de una **malla humana base con topología y rig válidos**, no de esferas/cilindros unidos.
3. Ajustar antropometría, rostro, apariencia, ropa y pose con controles comprensibles.
4. Obtener imágenes desde frontal, perfil, espalda y tres cuartos para revisión humana/IA.
5. Exportar modelos con validación y presupuesto de tamaño **preferentemente <=15 MB para uso web/AR**, según caso y calidad. La apariencia fotorrealista NO se garantiza por peso ni por añadir PBR: depende de geometría, texturas, iluminación y dirección artística.
6. Permitir a agentes aprobados **leer** la escena y proponer/ejecutar acciones explícitas con permiso, reversión y registro.

## 2. Estado verificado en main — inspección de código

Archivos encontrados: index.html (~35 KB, aplicación monolítica) y gemini-code-1792434602885.md (guía multi-IA). No se halló un servidor local MCP, backend, paquete npm, tests automatizados, licencia del repositorio ni pipeline de optimización.

**Lo que SÍ existe en el código:** Three.js fijado a 0.160.0 mediante importmap; WebGLRenderer; entorno RoomEnvironment; iluminación PBR; OrbitControls, TransformControls, raycaster; selección, outliner; primitivas; inspector de materiales; GLTFExporter binario; puente window.MCP_BRIDGE; captura PNG y WebSocket cliente hacia ws://localhost:8765.

**Límites reales, observables en código:**
- La opción titulada 'Escultura Hiperrealista' crea un nudo toroidal dorado y una esfera de vidrio; NO esculpe un cuerpo humano ni utiliza IA generativa.
- No existe GLTFLoader ni importador de archivos; el outliner y el scene graph presuponen mallas simples y no estructuras jerárquicas SkinnedMesh/Group.
- No hay interfaz antropométrica, shape keys/morph targets, rigging, ropa, cabello, animación, edición de malla, retratado de rostro ni retopología.
- El GLB sale sin un proceso de optimización, presupuesto de tamaño o validación; incluye Studio_Floor dentro de this.objects.
- Sin Undo/Redo, guardado de proyecto, guardas de edición, tests ni tratamiento completo de la liberación de recursos GPU.
- El servidor MCP prometido en la guía **no existe**: el navegador es cliente WebSocket. tools/list devuelve una lista ad hoc y no hay negociación MCP initialize ni estructura estándar tools/call.
- **Seguridad P0:** mcp_execute_three_code usa new Function con código recibido, ejecutable desde la vía WebSocket si se conecta a un servicio; debe quedar bloqueado para peticiones remotas y sustituirse por comandos declarativos limitados.
- **Seguridad P0:** refreshOutliner inserta nombres de objetos mediante innerHTML, propenso a XSS con nombres importados/no confiables; sustituir por textContent y nodos DOM seguros.
- La etiqueta en pantalla que indica 'MCP Vision Ready' significa capacidad local en el prototipo; **no demuestra** que una IA externa esté conectada ni que haya render fotorealista. La web publicada no pudo probarse interactivamente desde esta revisión; diagnósticos provenientes de inspección estática.

## 3. Decisión de arquitectura propuesta

**NO intentar portar todo Blender al navegador.** Priorizar una aplicación 3D fácil y modular en dos modos complementarios:

**Modo Web 100% estático (GitHub Pages):** importar GLB/GLTF localmente, crear desde plantillas, materiales PBR reales, iluminación/presets de estudio, sliders sobre morph targets compatibles, poses sencillas, cámara, revisión multiángulo, deshacer/rehacer, guardar proyectos, exportar GLB/PNG. Todo corre con WebGL y archivos locales sin pagos por uso. Las plantillas humanas deben disponer de derechos de redistribución.

**Modo avanzado gratuito, opcional, en el equipo del usuario:** asistente local (Node.js para MCP + Python/Blender CLI para operaciones 3D) que invoque Blender y MPFB instalado para generar bases humanas, rigs, variaciones anatómicas, ropa, UV, bake de normales, retopología y render de alta calidad. El navegador presenta resultados generados localmente. **GitHub Pages no puede alojar procesos Blender, Python ni Node como backend persistente.**

Esquema:

  Usuario / agente autorizado
       | visor web (Three.js)
       | operaciones tipadas + confirmación
       v
  Bridge local seguro (Node.js / SDK oficial MCP)  <--- cliente MCP local vía stdio
       |                                           (CLI / editor / agente habilitado)
       +---- Worker Blender + MPFB (Python; opcional)
       +---- glTF Transform + compresores (CLI; opcional)
       +---- Archivos locales GLB/PNG + manifiesto

**Compatibilidad:** conservar window.MCP_BRIDGE y un adaptador para los cuatro nombres históricos en lectura/uso local. No exponer ejecución arbitraria de JS a clientes remotos: mcp_execute_three_code queda bloqueado externamente y se reemplaza por herramientas autorizadas. Versionar nuevas APIs y documentar deprecación. NO activar conexiones abiertas en internet por defecto.

## 4. Prioridades y entregas propuestas (se aprueban por separado)

### P0 — Fiabilidad, seguridad y manejo de archivos (antes de conectar IAs)
- Modularizar index.html en app, scene, ui, io, mcp, materials, tests, sin reescribir todo ni romper GitHub Pages; usar Vite únicamente si el pipeline de Pages queda probado.
- Reemplazar innerHTML de nombres por textContent; desactivar JS arbitrario para entrada externa; validar JSON por esquema, tamaños, límites y nombres.
- Implementar GLTFLoader + OBJLoader opcional + DRACOLoader/KTX2Loader/Meshopt según necesidad; drag-and-drop de GLB/GLTF con dependencias, carga local y errores comprensibles.
- Jerarquía Group/Mesh/SkinnedMesh, selección recursiva, inspección segura de materiales, rig y animaciones.
- Guardar/abrir escena, undo/redo, controles adecuados en móvil, errores de WebGL, limpieza y dispose de materiales/texturas/geometría. Excluir suelo/luz/ayudas de exportación.
- Crear build/check de GitHub Pages, validación de import/export y prueba de apertura de un humano riggeado.

**Aprobación P0:** proyecto abre en PC/móvil, importa GLB y exporta sin perder jerarquía/animación; no ejecuta JS remoto; no degrada editor previo.

### P1 — Estudio de personas y personajes (la prioridad de producto)
- Biblioteca inicial de mallas humanas **base, licenciadas y redistribuibles**, preferiblemente creadas con MPFB/MakeHuman (núcleo gráfico CC0). El código de MPFB es GPLv3; revisar obligaciones si se redistribuye código. Respetar licencias independientes de ropa y texturas descargadas.
- Plantillas adulto masculino/femenino y variantes de proporción basadas en bases editables; sliders de altura, cabeza, hombros, torso, extremidades, complexión y rostro **solo cuando la topología/morph targets los soporten**.
- Rig compatible con animación glTF, control poses, vista A/T pose, manos con cinco dedos separados, ojos, rostro y cabello; verificador de huesos y pesos.
- Biblioteca modular: ropa/telas, armaduras, alas, halo, accesorios y piezas de ajedrez (peón, reina, rey, torre, alfil, caballo/pegaso). Reutilizar cuerpo y rigs y variar atuendos.
- Materiales de piel/metal/cuero/tela con color, rugosidad, mapas normal/roughness/AO, HDRI y sombras. Evitar metalness alto en piel; clearcoat/transmission no convierten cualquier forma en fotorrealista.
- Editor guiado con secuencia: Elegir base -> Ajustar anatomía -> Vestir -> Posar -> Revisar (4 vistas) -> Optimizar -> Exportar.

**Aprobación P1:** un humano base está completo y riggeado, con ambas manos anatómicamente válidas, cara y materiales coherentes, puede adoptar al menos una pose y se exporta.

### P2 — Conexión multiagente MCP real y auditable
- Implementar servidor MCP local usando el **SDK oficial** con initialize, tools/list, tools/call, recursos y transporte stdio para clientes locales; hacer adaptador explícito al WebSocket existente entre el bridge y la pestaña del navegador.
- Herramientas DE LECTURA: scene.get_graph, viewport.capture, object.inspect, material.inspect, model.stats, render.status.
- Herramientas DE ESCRITURA: object.create_from_preset, object.transform, material.set_properties, character.set_morph, character.set_pose, camera.set_view, scene.import_asset, scene.export_glb, render.start, optimize.start; validar parámetros y permisos.
- Permisos separados READ/WRITE/RENDER/EXPORT; cada cambio irreversible necesita confirmación, con undo y snapshot; sesión ligada a proyecto/revisión.
- Solo vincular localhost, comprobar Origin y Host, secreto efímero por sesión, TLS cuando aplique, revocación rápida, límites de payload, tareas, logs y cancelación; no aceptar tokens por URL ni incrustar claves API en HTML.
- Seguridad frente a DNS rebinding, acceso entre sitios, archivos arbitrarios y prompts no confiables. Sin túneles ni servidor público inicial.
- Herramientas para agentes: inspeccionar imagen y grafo de escena, ejecutar ediciones tipadas, renderizar 4 vistas, comparar revisiones y reportar métricas.
- La conexión del ChatGPT alojado en la nube a localhost **NO es automática**. Desde este chat existe acceso al repo GitHub, no al navegador local. Una integración directa requiere un cliente/plugin con permisos o un relay autenticado y soportado, probado por separado.

**Aprobación P2:** un cliente MCP compatible hace initialize, lista herramientas, lee grafo y PNG, solicita un cambio permitido, recibe consentimiento, ve revisión y puede revertirlo; prueba negativa bloquea JS remoto.

### P3 — Calidad visual y peso para videojuegos / AR
- Geometrías LOD0/LOD1/LOD2; retopología y rig conservado; baking normal/AO; atlas de texturas; variantes de detalle.
- Optimización con glTF Transform (dedup, prune, resample cuando aplique, compresión Meshopt o Draco y WebP/KTX2 según destino), sin duplicar estrategias incompatibles y con decodificadores configurados.
- Validación de GLB antes y después: bytes, triángulos, draws, materiales, texturas, huesos, morphs, animaciones, fps PC/móvil y similitud visual de renders.
- Presupuestos **iniciales para experimentación**, NO garantías: objetivo GLB completo <=15 MB; texturas 1K/2K por perfil; malla 15k-60k triángulos LOD0 dependiendo de rostro/manos/ropa; mejorar o revisar según dispositivo, render y juego.
- Entregar preset 'Juego móvil', 'Juego PC' y 'WebAR <=15 MB'. Si al comprimir aparecen artefactos, preferir fidelidad o advertir.

**Aprobación P3:** referencia y exportación comprimida lado a lado, tamaño final <=15 MB (si viable), rig/animación conservados y test de FPS/memoria con dispositivo real.

## 5. Riesgos, costos y límites

1. **Gratis** = software libre y ejecución local sin cuota; requiere hardware del usuario y tiempo de render. La generación IA de texto/imagen a 3D en servicios externos puede cobrar, limitar descargas, imponer créditos o restricciones; NO basar el producto en ello.
2. Un rostro ultrarrealista no surge automáticamente de un prompt, primitivas o material shiny. Requiere malla detallada, topología, texturas, ojos/cabello, iluminación y revisiones.
3. MPFB no se ejecuta en GitHub Pages; se usa dentro de Blender local para producción de plantillas y trabajos avanzados. No prometer equivalencia con Cycles dentro de Three.js.
4. El acceso MCP debe ser opcional y restringido: no permitir evaluar JS remoto, controlar cargas y leer archivos únicamente de directorios explícitamente autorizados.
5. No asumir que las herramientas de IA de este chat se conectan automáticamente al servidor WebSocket del usuario: es una **integración pendiente**.
6. No hay licencia raíz en el repo inspeccionado; definirla antes de publicar paquetes/distribuir assets. Verificar individualmente licencias de modelos y texturas.

## 6. Entregas documentales y protocolo multi-IA

- Esta propuesta pertenece solo a ChatGPT y se presenta como PR **borrador no fusionado** para revisión humana.
- La IA siguiente debe escribir su propia propuesta en propuestas/FECHA-agente-titulo.md y agregar una entrada al registro; evitar editar directamente el texto de la otra IA.
- Si dos propuestas se contradicen, incluir una tabla Comparación: decisión, opción A, opción B, costo/beneficio/riesgo, criterio para decidir, y marcar PENDIENTE DE APROBACIÓN.
- Nadie fusiona cambios de arquitectura o código a main sin aprobación del propietario.
- Cada agente reporta: fecha, agente, rama/commit/PR, hallazgos, archivos cambiados, tests reales, limitaciones, siguiente acción y estado (propuesta/implementado/verificado). Distinguir objetivos de capacidades probadas.
- Nunca enviar el documento completo de otros proyectos a servicios externos. No guardar claves, tokens ni archivos privados en repositorio público.

## 7. Próxima decisión humana sugerida

**Recomiendo aprobar P0 primero y encargar una prueba de P1 muy concreta:** importar un GLB humano riggeado y mostrarlo con piel, ropa y vista múltiple; luego habilitar bridge MCP de solo lectura. El pipeline local avanzado Blender+MPFB se conecta después, con permisos.

## 8. Referencias técnicas a verificar al implementar

- Three.js GLTFLoader: https://threejs.org/docs/pages/GLTFLoader
- glTF Transform: https://gltf-transform.dev/cli
- Khronos KTX2 y optimización de glTF: https://www.khronos.org/blog/optimize-3d-assets-with-khronos-new-gltf-compressor-tool
- SDK MCP oficial TypeScript v2: https://github.com/modelcontextprotocol/typescript-sdk
- Seguridad MCP local: https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/docs/2026-07-28/tutorials/security/local-server-security.mdx
- MPFB2 y su licencia dividida: https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.md

## 9. Registro de la intervención

| Fecha ISO | Agente | Estado | Archivos | Trabajo realizado | Falta |
| --- | --- | --- | --- | --- | --- |
| 2026-10-19 | ChatGPT GPT-6 | PROPUESTA / sin implementar | Este documento + guía multi-IA en rama de propuesta | Auditoría estática del editor, modelo híbrido, prioridades, seguridad MCP, human workflow, validaciones de GLB | Revisión por otra IA y aprobación del propietario; pruebas funcionales navegador real |
