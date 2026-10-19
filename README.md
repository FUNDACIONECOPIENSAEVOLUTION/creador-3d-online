# Creador 3D Online · Estudio de animación libre 1.3

Estudio web **gratuito** basado en Three.js r160 para editar modelos GLB, previsualizar animaciones e intercambiar información con un agente MCP local autorizado. La base pública original se conserva en `main` hasta revisar esta rama.

## Editor web y límites reales

- `index.html`: estructura e interfaz web; `styles/studio.css`: apariencia.
- `src/studio.js`: cámara, PBR, transformaciones, importación/exportación GLB, grafo y puente de escena.
- `src/character-workflow.js`: imagen de referencia, encargo en JSON, reproductor de clips glTF.
- `mcp-server.js`: servidor **local** stdio/WS, restringido a `127.0.0.1` y orígenes permitidos.
- `tests/smoke.test.cjs`: verificaciones sin dependencias.

**Importante:** cargar una foto y escribir un prompt NO genera un humano hiperrealista automáticamente. El editor expone el encargo e imagen por MCP; para generar una malla humana anatómica y riggeada se necesita un motor 3D real (por ejemplo Blender + MPFB) u otro proveedor explícitamente elegido. En esta versión se pueden importar los GLB producidos por dichos motores y reproducir clips importados.

## Cómo probar (sin modificar main)

1. En GitHub abrir la rama `feature/character-studio-mcp-v12` o usar una vista de pruebas de GitHub Pages configurada para dicha rama.
2. Abrir el editor y cargar un `.glb` **autocontenido**, idealmente un humano riggeado con clips incorporados. Elegir un clip en **Movimiento de personajes GLB** para previsualizarlo.
3. En **Personajes IA** cargar una imagen, escribir la descripción, elegir destino y descargar el encargo JSON. La imagen no se sube a ningún servicio por defecto.
4. Exportar GLB y comprobar tamaño. **No existe todavía compresión automática** ni exportación garantizada de GLB de menos de 15 MB.

## Conexión MCP en Windows (servidor local, no remoto)

Requiere Node.js 20+ instalado. Clonar o descargar este repositorio en el PC y ejecutar desde la carpeta:

```powershell
npm install
npm test
npm run start-mcp
```

Abrir https://fundacionecopiensaevolution.github.io/creador-3d-online/ **solo después de que esta versión haya sido aprobada y publicada**, o probar el editor de la rama mediante un servidor local en puerto 5173/8000. Pulsar **Conectar WS** para enlazar `ws://localhost:8765`.

En el cliente MCP compatible, configurar un servidor por `stdio`: comando `node` y argumento la ruta absoluta a `mcp-server.js` (o mediante gestor MCP compatible). Cada cliente requiere su propia configuración.

El servidor **no** se publica desde GitHub Pages, no abre el puerto a otras máquinas y NO ejecuta código JavaScript entregado por la IA. Solo muestra operaciones tipadas: inspección, captura, lectura de imagen/encargo, crear primitivas y transformar objetos.

### Modelo de flujo de creación deseado (por desarrollar)

Foto + texto → agente MCP lee imagen y encargo → herramienta local Blender/MPFB produce personaje y rig → se aplican/hornean texturas → se generan/importan clips idle/attack/defense → se exporta GLB → se importa en el editor → se inspecciona y valida para videojuegos.

**Limitación de ChatGPT en esta conversación:** el acceso GitHub de la IA no concede acceso automático al WebSocket del navegador local ni a Blender del computador. Un cliente agente con MCP configurado (o una integración permitida) debe operar las herramientas.

### Seguridad

El anterior método `mcp_execute_three_code` queda **deshabilitado** aunque el nombre se conserva como señal de migración; no se anuncia desde el servidor. Nunca introducir claves de servicios en el HTML público. El puente local solo acepta Origin de la página GitHub Pages oficial y de las direcciones localhost de desarrollo conocidas. Iniciar solamente en un equipo de confianza.

## Desarrollo y pruebas

```bash
npm test
npm run check
```

La bitácora de agentes está en `MCP_AI_GUIDE.md`. Cada modificación requiere registrar cambios, pruebas efectivas y pendientes. Las operaciones de escultura avanzada, generación 2D→3D, humano a partir de foto y animación de batalla creada automáticamente **son trabajo futuro**, no funciones entregadas en 1.2.

---

## Versión 1.3 — Animar modelos 3D importados gratis (sin Tripo/Hunyuan/Meshy)

Esta actualización convierte NeoBlender de un simple reproductor de animaciones en un editor básico de **poses y fotogramas clave** usando Three.js, sin llamadas a servicios de generación de pago.

**Formatos importados:** GLB/GLTF autocontenidos, OBJ y FBX. Los OBJ generalmente no contienen rigs ni animaciones; FBX puede incluir esqueletos y clips (dependiendo del archivo). Archivos con texturas externas requieren empaquetar los recursos o conversiones posteriores.

### Cómo animar un GLB con esqueleto

1. Importa el modelo GLB o FBX y abre **Animación libre · Huesos y fotogramas clave**.
2. Marca **Mostrar huesos en Outliner**. Selecciona un hueso (por ejemplo, brazo o antebrazo).
3. Da nombre a la acción (Ataque, Defensa, Caminar), define duración y pulsa **Crear acción**.
4. En tiempo 0, coloca el hueso en la pose inicial y pulsa **Registrar pose**.
5. Mueve el control de tiempo hasta, por ejemplo, 0.5 segundos, rota el hueso y pulsa **Registrar pose**.
6. Sigue registrando las poses necesarias y pulsa **Guardar clip**.
7. En la lista de clips del modelo selecciona el nuevo movimiento para reproducirlo.
8. Pulsa **Exportar GLB** y comprueba que el modelo conserva la animación en otro visor.

### Cómo animar un modelo sin esqueleto

- Si es una sola malla: genera los presets gratuitos **Reposo**, **Ataque**, **Defensa**, **Golpe** o **Derrota** que mueven el objeto entero.
- Si tiene piezas independientes: selecciona una extremidad, escribe la coordenada mundial de su articulación y pulsa **Crear pivote**. Selecciona ese pivote y registra sus poses.
- Si el cuerpo es una sola malla sin huesos **no se pueden doblar brazos de forma anatómica** con pivotes. Necesita segmentación, armature y skinning; el rigging semiautomático con pesos por vértice es la siguiente fase pendiente. Esta versión no promete que cualquier figura pueda articularse de inmediato.

### Acceso por IA mediante herramientas propias

El MCP local ofrece herramientas de lectura y creación tipada:
`mcp_animation_inspect`,
`mcp_animation_create`,
`mcp_animation_keyframe`,
`mcp_animation_commit`,
`mcp_animation_preset`,
`mcp_animation_pivot` y
`mcp_animation_play`.

Una IA con cliente MCP local configurado puede inspeccionar los huesos, crear acciones, asignar poses numéricas, verlas y exportarlas mediante la interfaz. **Este ChatGPT todavía no tiene acceso directo a tu navegador local desde la nube**. No exponemos evaluación remota de JavaScript.

### Próxima etapa de código libre

1. Probar exportación e importación de GLB con animaciones de huesos reales.
2. Undo/Redo, guardado de proyectos y exploración de mallas.
3. Rigging humanoide guiado sobre mallas sin esqueleto: ubicar articulaciones, generar armature, asignar pesos con visualización y correcciones.
4. Timeline multicanal, curvas de interpolación, biblioteca abierta de movimiento.
5. Optimización de texturas, LOD y GLB <=15 MiB según medida real.

No integra APIs ni suscripciones obligatorias de Tripo, Hunyuan3D, Meshy ni otros generadores 3D.
