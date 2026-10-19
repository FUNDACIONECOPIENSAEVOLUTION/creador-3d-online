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
