**Nombre oficial de la aplicación: EcoBlend.** Se conserva el repositorio y la URL `creador-3d-online` para no romper enlaces existentes. El cambio de marca no implica cambiar propietario, dominio ni URL.

# EcoBlend — estudio 3D online libre y multi-IA (v1.4)

Estudio web **gratuito** basado en Three.js r160 para editar modelos GLB, previsualizar animaciones e intercambiar información con un agente MCP local autorizado. Los cambios se desarrollan y comprueban antes de integrarse en la rama pública `main`.

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

---

## NeoBlender Web-first: tecnología libre para equipos modestos (1.3)

**Regla de accesibilidad:** abrir https://fundacionecopiensaevolution.github.io/creador-3d-online/ debe permitir modelar y animar figuras sin instalar software adicional, sin crear cuenta y sin pagar suscripciones. El MCP local es opcional para asistentes externos de escritorio; nunca es necesario para los botones del visor.

### Prueba rápida: crear un ángel sin descargar ningún modelo

1. Abre el editor actualizado en un navegador con WebGL y selecciona **Ligero** en Rendimiento.
2. Pulsa **Crear guardián alado** en **Personajes creados en la web — Gratis**.
3. El modelo aparece con pivotes en hombros, codos, muñecas, dedos, caderas, rodillas y alas.
4. En **Animación libre**, selecciona una articulación en el Outliner, crea una acción, rota la articulación en dos momentos y registra las poses.
5. Guarda el clip y selecciónalo para reproducirlo.
6. Usa **Exportar personaje .GLB** para descargar únicamente el personaje con sus clips.

Alternativamente, **Crear humano articulado** genera una base sin alas. Ambos se construyen proceduralmente en JavaScript+Three.js con geometría de bajo costo y materiales estándar PBR. Son **maniquíes estilizados de partida**, no humanos hiperrealistas ni reconstrucciones IA de una fotografía. Su geometría se puede reproducir gratis sin servidores ni pesos de modelo IA.

### Importar tus propios modelos

GLB/GLTF, OBJ y FBX pueden abrirse localmente. Las mallas con esqueleto y pesos se pueden posar y animar por huesos; las piezas independientes pueden articularse mediante pivotes. **Una única malla sin esqueleto no puede doblar los brazos de manera anatómica** hasta crear un rig con pesos. Algunas importaciones FBX/OBJ necesitarán empacar texturas o materiales antes de lograr fidelidad de apariencia.

### Modo Ligero y calidad

En equipos modestos el perfil **Ligero** limita el dibujo a 30 cuadros por segundo, la relación de píxeles a 1 y desactiva sombras en tiempo real. Esto **no elimina por completo la carga de GPU**, ni garantiza un rendimiento determinado en cualquier teléfono. Los perfiles Equilibrado y Visual son opcionales.

### Qué sigue pendiente y cómo pensamos resolverlo sin cobrar

- Manos/cara y cuerpos con mejor malla, topología y materiales, mediante edición y plantillas abiertas verificadas.
- Autorrig guiado de malla única (marcadores de articulación, huesos y pintura/propagación de pesos), inicialmente para humanoides estándar.
- Biblioteca comunitaria de mallas y animaciones de licencia libre compatible: licencias y procedencia registradas por asset.
- Animación por curvas (timeline), edición no destructiva, deshacer/rehacer y proyectos guardados.
- Texturas PBR optimizadas, normal mapping, LOD y GLB pequeño para realidad aumentada.
- Asistencia IA desde chats mediante un puente seguro compatible; cualquier nube compartida requiere límites de infraestructura y presupuesto.

**No se incluyen Tripo, Hunyuan3D, Meshy ni APIs de pago en el editor.** La IA controla herramientas de código, no ejecuta un modelo generativo enorme en los computadores de los usuarios. Los artefactos originales producidos por la herramienta de geometría procedural se ofrecen para libre uso; verificar licencias de modelos externos importados.

---

## Comandos guiados gratuitos en español

El usuario puede escribir instrucciones básicas en el panel **Comandos guiados en español** y pulsar **Aplicar instrucciones disponibles**:

- `crea un ángel con movimiento de ataque y modo ligero`
- `crea humanoide`
- `modo equilibrado`
- `defensa` (con el personaje seleccionado)
- `descarga personaje GLB`

El intérprete ubicado en `src/free-command-assistant.js` usa reglas estrictas **sin servidores, modelos de IA ni pagos**. Cuando no entiende una instrucción, lo avisa y no pretende haber generado una figura compleja a partir del texto. La futura integración de chats de IA debe utilizar las herramientas MCP autorizadas, no evaluación de código remoto.

## Licencia y colaboración

Este repositorio incluye `LICENSE` con la licencia MIT para su código, de modo que otras personas puedan copiarlo, aprender, modificarlo y compartir mejoras conservando el aviso de licencia. Esta licencia **no cambia las licencias de los archivos importados por el usuario**, ni las de las dependencias de terceros. Aportar mejoras preferentemente mediante un Pull Request y documentar los cambios en `MCP_AI_GUIDE.md`.

---

## EcoBlend 1.4 — Más allá de los humanos

El objetivo del software no es únicamente crear modelos MPFB2. **EcoBlend es un editor 3D universal**, diseñado para seres humanos, personajes antropomorfos, animales, dragones, robots, armas, objetos, vehículos, arquitectura y cualquier figura que pueda descomponerse en partes y geometrías soportadas.

La interfaz ya ofrece:

- Plantillas web editables de gato antropomorfo, dragón, robot, árbol, silla, vehículo y torre de castillo, además del humanoide y ángel anteriores.
- Formato `ecoblend.asset.v1` para que personas e IA describan jerarquías de piezas, articulaciones y materiales físicos, sin scripts ejecutables.
- Herramientas MCP `mcp_asset_validate`, `mcp_asset_build` y `mcp_asset_preset`, complementadas con `mcp_get_reference_image` y capturas de cuatro vistas.
- Descripciones en español que identifican **solo ciertas plantillas**. La comprensión libre de toda fotografía no está incluida en el editor estático: una IA multimodal conectada mediante MCP debe interpretarla y redactar un plano. No se inventarán resultados hiperrealistas.
- Cada figura por partes puede seleccionar articulaciones, añadir clips básicos y exportarse a GLB desde la web.

**Guía técnica:** [IA_IMAGEN_A_3D_ECOBLEND.md](docs/IA_IMAGEN_A_3D_ECOBLEND.md). MPFB2 permanece como posibilidad futura opcional para bases humanas; no es necesario para generar criaturas u objetos.

Sin Tripo, Hunyuan, Meshy ni suscripciones obligatorias; software MIT con herramientas web gratuitas. El rendimiento y el nivel de detalle tienen límites reales en equipos modestos. El hiperrealismo auténtico, la reconstrucción exacta desde una foto y la deformación automática de mallas orgánicas siguen en desarrollo.

### Descripción especializada de personas en EcoBlend

En el mismo campo de descripción también puedes escribir `mujer de ojos verdes, acuerpada, cabello negro largo y piel canela`. EcoBlend reconoce los atributos explícitos y crea una base humanoide con cambios visibles de color de ojos, cabello, piel y proporciones simples. El formato de ficha está en `src/character-spec.js` y la aplicación de rasgos en `src/character-appearance.js`. Estos cambios **son estilizados**, no un resultado humano hiperrealista ni ejecución real de MPFB2 en el navegador.

Un agente autorizado puede acceder a `mcp_human_describe`, `mcp_human_create` y `mcp_human_update`. El motor general `mcp_asset_build` sigue siendo el camino para cualquier otro tipo de figura.