# 🎨 Creador 3D Online — Studio PBR & MCP AI Vision

Estudio web de modelado y renderizado 3D hiperrealista (estilo Blender) impulsado por **Three.js r160 (`MeshPhysicalMaterial`)** y diseñado para conectarse con múltiples Inteligencias Artificiales mediante el **Model Context Protocol (MCP)**.

🔗 **Repositorio:** [https://github.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online](https://github.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online)  
🌐 **Demo en Vivo (GitHub Pages):** `https://fundacionecopiensaevolution.github.io/creador-3d-online/`

---

## ✨ Características Principales
- **Renderizado Hiperrealista PBR:** Iluminación de estudio HDRI (`RoomEnvironment`), `ACESFilmicToneMapping`, índice de refracción real (`IOR`), transmisión de vidrio, laca (`Clearcoat`) y texturas de micro-relieve procedurales.
- **Visión Espacial Cuádruple para IAs (`mcp_capture_quad_view`):** Permite a cualquier IA capturar simultáneamente las vistas **Perspectiva, Frontal, Superior y Lateral** en un solo fotograma para entender la profundidad y proporciones del modelo 3D.
- **Importación y Exportación `.GLB`:** Arrastra archivos `.glb` directamente al lienzo o exporta tus creaciones con un clic.
- **Coordinación Multi-IA:** Consulta [`MCP_AI_GUIDE.md`](./MCP_AI_GUIDE.md) para ver las reglas de arquitectura y la bitácora donde cada IA registra sus avances.
