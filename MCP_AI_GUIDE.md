# 🧠 Guía de Arquitectura y Bitácora Multi-Agente (`MCP_AI_GUIDE.md`)

**Repositorio Oficial:** `https://github.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online`  
**URL de Despliegue (GitHub Pages):** `https://fundacionecopiensaevolution.github.io/creador-3d-online/`

---

## ⚠️ REGLA DE ORO PARA CUALQUIER IA QUE SE CONECTE A ESTE REPOSITORIO
Si eres un agente de IA (Claude Code, Cursor, Windsurf, GitHub Copilot, Gemini, OpenAI Codex o un agente conectado vía MCP):
1. **Lee primero** la sección **2. Protocolo de Visión y Control (`window.MCP_BRIDGE`)** y la tabla **5. Bitácora de Avances Multi-IA** al final de este documento antes de modificar cualquier línea de código.
2. **No rompas la retrocompatibilidad** de `window.MCP_BRIDGE` ni desactives `preserveDrawingBuffer: true` en el `THREE.WebGLRenderer`, ya que dejarías "ciegas" a las demás IAs que inspeccionan el lienzo 3D.
3. **Registra siempre tu trabajo:** Al finalizar cualquier mejora, agrega una nueva fila en la tabla de la **Sección 5 (Bitácora de Avances Multi-IA)** indicando fecha, tu nombre/modelo, qué implementaste, qué archivos modificaste y el siguiente paso recomendado.

---

## 1. Arquitectura del Proyecto
`creador-3d-online` es un estudio web de modelado y renderizado 3D hiperrealista tipo Blender que se ejecuta 100% en el navegador sobre **Three.js r160 (WebGL2)** y cuenta con un puente bidireccional **Model Context Protocol (MCP)**.

### Archivos Principales del Repositorio:
- `index.html`: Aplicación completa (Single-File Studio) con interfaz tipo Blender, motor PBR (`MeshPhysicalMaterial` + `RoomEnvironment` + `ACESFilmicToneMapping`), generador de texturas procedurales, importador/exportador `.GLB` y API `window.MCP_BRIDGE`.
- `MCP_AI_GUIDE.md`: Documento maestro de coordinación y memoria compartida entre diferentes inteligencias artificiales.
- `mcp-server.js`: Servidor puente en Node.js que enlaza clientes MCP de escritorio (Claude Desktop, Cursor, etc.) con el navegador mediante WebSockets (`ws://localhost:8765`).
- `package.json`: Configuración de dependencias para el puente MCP local.

---

## 2. Protocolo de Visión y Control para IAs (`window.MCP_BRIDGE`)

Toda IA puede ver y manipular la escena 3D invocando `window.MCP_BRIDGE.handleJsonRpc(request)` o a través del WebSocket `ws://localhost:8765`.

### Herramientas Disponibles (`tools/list`):

| Método MCP | Descripción | Parámetros (`params`) | Respuesta para la IA |
| :--- | :--- | :--- | :--- |
| `mcp_get_scene_graph` | Devuelve el estado exacto de la escena, cámara y materiales PBR de cada objeto. | `{}` | JSON con `camera` y arreglo `objects` (UUID, posición, rotación, escala, shader físico). |
| `mcp_capture_viewport` | Captura una fotografía PNG en Base64 de la cámara actual. | `{}` | `{ mimeType: "image/png", mode: "single", dataUrl: "data:image/png;base64,..." }` |
| `mcp_capture_quad_view` | **Visión Espacial 3D:** Renderiza 4 vistas simultáneas (Perspectiva, Frontal Z+, Superior Y+, Lateral X+) en una sola imagen de 800x600. | `{}` | `{ mimeType: "image/png", mode: "quad_orthographic", dataUrl: "data:image/png;base64,..." }` |
| `mcp_spawn_pbr_mesh` | Crea una primitiva o malla de alta densidad con material físico hiperrealista. | `{ type, name, color, metalness, roughness, clearcoat, transmission, ior, x, y, z }` | `{ status: "created", name, uuid }` |
| `mcp_modify_object` | Modifica transformaciones o propiedades PBR de un objeto existente. | `{ name, position, scale, color, metalness, roughness, transmission }` | `{ status: "updated", name }` |
| `mcp_execute_three_code` | Ejecuta código JavaScript/Three.js arbitrario con acceso directo a `(THREE, scene, app)`. | `{ code: "..." }` | `{ status: "executed", output }` |

---

## 3. Flujo Recomendado de Modelado Asistido por IA (Loop Visión-Acción)
Cuando un usuario pida a una IA *"Crea un modelo 3D hiperrealista de X"*:
1. **Inspeccionar:** Llamar a `mcp_get_scene_graph` para conocer qué objetos existen en el espacio.
2. **Construir:** Usar `mcp_spawn_pbr_mesh` o inyectar geometría compuesta mediante `mcp_execute_three_code`.
3. **Ver y Verificar:** Llamar a `mcp_capture_quad_view` para observar la proporción desde los 4 ángulos ortográficos y verificar reflejos, sombras e intersecciones.
4. **Refinar:** Ajustar posición, escala o parámetros de `MeshPhysicalMaterial` (`transmission`, `ior`, `clearcoat`, `roughness`) con `mcp_modify_object`.
5. **Documentar:** Generar la entrada de bitácora (botón `📝 Log para Guía IA` o edición directa) y guardarla en la Sección 5 de este archivo.

---

## 4. Roadmap Técnico para Siguientes IAs
- [x] **v1.0:** Motor PBR base, `RoomEnvironment`, TransformControls (`G`, `R`, `S`), exportador `.GLB` y `window.MCP_BRIDGE`.
- [x] **v1.1:** Vinculación oficial con `FUNDACIONECOPIENSAEVOLUTION/creador-3d-online`, sistema de **Visión Cuádruple (`mcp_capture_quad_view`)**, importación Drag & Drop de `.GLB`, subdivisión básica, texturas bump procedurales y servidor puente `mcp-server.js`.
- [ ] **v1.2 (Siguiente IA):** Implementar operaciones booleanas CSG (Unión, Diferencia, Intersección) usando `three-bvh-csg` para modelado de piezas complejas.
- [ ] **v1.3:** Añadir modo de escultura dinámica con pinceles (Inflate, Smooth, Grab) sobre los vértices de la malla.
- [ ] **v1.4:** Integrar soporte WebXR / Realidad Aumentada para previsualizar los modelos creados en el entorno físico real.

---

## 5. Bitácora de Avances Multi-IA (AI Changelog)

> **Instrucción:** Añade siempre tu fila al final de esta tabla sin borrar el historial previo.

| Fecha (YYYY-MM-DD) | Agente / Modelo IA | Cambios e Implementaciones Realizadas | Archivos Tocados | Próximo Paso Sugerido |
| :--- | :--- | :--- | :--- | :--- |
| 2026-10-19 | **Gemini (Arquitecto Inicial)** | Creación del motor PBR Three.js r160, interfaz estilo Blender, atajos `G/R/S/D/Supr`, exportador/importador `.GLB`, texturas procedurales, visión cuádruple (`mcp_capture_quad_view`) y puente `mcp-server.js` configurado para `FUNDACIONECOPIENSAEVOLUTION/creador-3d-online`. | `index.html`, `MCP_AI_GUIDE.md`, `mcp-server.js`, `package.json`, `README.md` | Integrar CSG Booleans (`three-bvh-csg`) y pinceles de escultura de vértices en `index.html`. |
| 2026-10-19 | **ChatGPT GPT-6 (implementación 1.2, rama feature)** | Separa CSS y JS, agrega encargo foto+texto para agentes, importar GLB riggeado con selección jerárquica, clips AnimationMixer, exportación con clips, visión ortográfica, MCP stdio/WS restringido con bloqueo de ejecución de JS remota, pruebas y ejemplo de ángel. **No incluye generación automática de humanos desde imágenes; requiere Blender u otro productor 3D.** | `index.html`, `styles/studio.css`, `src/studio.js`, `src/character-workflow.js`, `mcp-server.js`, `package.json`, `README.md`, `tests/`, `scripts/`, `examples/` | Ejecutar CI, revisar PR, comprobar con personaje GLB real y validar producción Blender+MPFB. |

---

## 6. Actualización 1.2 — ChatGPT: laboratorio de personajes (rama de desarrollo)

**Rama:** `feature/character-studio-mcp-v12`. Cambios sometidos a PR, sujetos a pruebas; no confundir con funcionalidades validadas sobre la rama `main`.

- Separación del antiguo `index.html` monolítico en HTML, `styles/studio.css`, `src/studio.js` y `src/character-workflow.js`.
- **Imagen + descripción:** usuario carga una referencia; se reduce localmente a JPEG de hasta 1024 px, no se envía por defecto. La IA local autorizada puede usar `mcp_get_creation_brief` y `mcp_get_reference_image`. Existe descarga de JSON con encargo.
- **Rig y clips:** importador acepta GLB autocontenido con jerarquía y animaciones glTF; las reproduce con `THREE.AnimationMixer` y busca conservarlas al exportar. Crear clips nuevos aún necesita Blender/otras herramientas.
- **Visión 4 vistas:** frontal, lateral, superior pasan a usar cámaras ortográficas de verdad; perspectiva mantiene cámara original.
- **Servidor:** WebSocket solo en `127.0.0.1`, lista explícita de Origins, protocolo MCP stdio (initialize, tools/list, tools/call). Se elimina `mcp_execute_three_code` del catálogo y se bloquea su ejecución del lado del navegador. Se usan operaciones tipadas en su lugar.
- **Validación:** `npm run check` y test de integración manual con GLB aún deben ejecutarse/verificarse tras revisión del PR.
- **Limitación fundamental:** WebGL/Three.js no genera automáticamente cuerpos humanos hiperrealistas desde fotografías. Para esa capacidad se necesitará integrar un pipeline de Blender + MPFB, un modelo 3D con licencia apropiada, rigging/retopología y eventualmente un servicio de IA adicional, dependiendo de presupuesto y calidad. La interfaz actual **solo prepara el encargo**.

**Seguridad de versiones anteriores:** jamás reconectar un servidor que exponga `mcp_execute_three_code` al público. El método original evaluaba JavaScript sin controles suficientes.

**Próximos pasos ordenados:** (1) pasar CI y probar un GLB riggeado real, (2) solucionar fallos de exportación y texturas externas, (3) crear una biblioteca legalmente distribuible de personajes base, (4) pipeline local Blender/MPFB para generación/refinado, (5) animaciones originales de batalla e integración ECOAJEDREZ, (6) optimización LOD/GLB <=15 MB con medidas reales.
