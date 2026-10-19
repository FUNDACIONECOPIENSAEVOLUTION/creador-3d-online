# EcoBlend · Protocolo universal: imagen o idea → figura 3D

**Estado:** 1.4, primera infraestructura funcional de planos declarativos. No es un modelo IA generativo.

## Objetivo

EcoBlend será un editor web de código abierto para humanos, animales, antropomorfos, robots, criaturas originales, objetos, muebles, vehículos, arquitectura y escenarios. MPFB2 podrá emplearse solo en un futuro adaptador especializado en anatomía humana; **no es requisito para ejecutar EcoBlend**.

No exige Tripo, Hunyuan, Meshy, instalaciones de IA pesada, API de pago ni Blender en el PC para usar las herramientas web actuales. El código fuente del motor se puede revisar y adaptar en GitHub.

## Trabajo de una IA multimodal conectada

1. El usuario carga una imagen mediante el campo de **Imagen de referencia** y escribe qué desea construir. La imagen se mantiene en el navegador y se reduce antes de exponerla a un agente autorizado.
2. El cliente MCP que realmente disponga de capacidad de visión llama a `mcp_get_reference_image`, `mcp_get_creation_brief` y opcionalmente `mcp_get_scene_graph`.
3. La IA identifica la silueta y subdivide visualmente el objeto en piezas (cabeza, torso, alas, patas, ruedas, ventanas, tronco, etc.). Señala la incertidumbre de las superficies no visibles y no inventa dimensiones exactas sin evidencia.
4. Construye un plano JSON conforme a `ecoblend.asset.v1` con **máximo 120 partes**, sin código JavaScript.
5. Llama a `mcp_asset_validate` con `{"blueprint": plano}`. Si hay errores, corrige el plano antes de construirlo.
6. Llama a `mcp_asset_build` con el mismo `blueprint`, que crea mallas PBR y articulaciones en la escena del navegador.
7. Inspecciona `mcp_capture_quad_view` y `mcp_get_scene_graph`, compara con la referencia, ajusta el plano y solicita confirmación antes de reemplazar trabajos existentes.
8. Si debe moverse, crea fotogramas mediante `mcp_animation_create`, `mcp_animation_keyframe`, `mcp_animation_commit` y reproduce con `mcp_animation_play`. El usuario descarga su GLB desde la web.

**Limitación principal:** el esquema actual genera geometría de primitivas y piezas rígidas. No realiza generación neural de mallas, UV atlas automático, sculpt, fotogrametría, topología orgánica fina ni pesos de piel automáticos. Los resultados pueden ser aproximaciones geométricas, no una copia hiperrealista exacta de cualquier fotografía.

## Formato seguro de planos

Ejemplo (creación de un ser imaginario de tres piezas con articulación):

```json
{
  "version": "ecoblend.asset.v1",
  "name": "Mi_Criatura",
  "category": "creature",
  "parts": [
    {
      "id": "cuerpo",
      "shape": "capsule",
      "position": [0, 1.2, 0],
      "scale": [1, 1.2, 0.8],
      "color": "#527d69",
      "roughness": 0.7
    },
    {
      "id": "cuello",
      "kind": "joint",
      "position": [0, 1.75, -0.1]
    },
    {
      "id": "cabeza",
      "parent": "cuello",
      "shape": "sphere",
      "position": [0, 0.3, -0.2],
      "scale": [0.5, 0.5, 0.55],
      "color": "#527d69"
    }
  ]
}
```

### Diccionario

- `version`: `ecoblend.asset.v1`
- `name`: nombre legible (máximo 80 caracteres)
- `category`: `human`, `anthropomorphic`, `animal`, `creature`, `robot`, `vehicle`, `building`, `prop`, `abstract` u `other`
- `parts`: máximo 120 partes, todas nombradas por `id` único. `parent` debe corresponder a una parte **anterior** o `root`
- `kind`: `mesh` (predeterminado) o `joint` (grupo articulado sin geometría)
- `shape`: `box`, `sphere`, `cylinder`, `cone`, `capsule`, `torus` (solo en mallas)
- `position`: XYZ relativos al padre (rango ±25)
- `rotationDeg`: rotación XYZ en grados
- `scale`: escala XYZ positiva
- `color`: hexadecimal #RRGGBB
- `metalness` y `roughness`: entre 0 y 1

**Seguridad:** los nombres son texto y el motor solo permite operaciones declarativas. No se aceptan `script`, `eval`, archivos externos ni ejecución arbitraria.

## Qué funciona sin IA conectada

Se pueden generar plantillas editables de gato antropomorfo, dragón, robot, árbol, silla, vehículo y torre de castillo directamente en el navegador. También pegar cualquier plano JSON válido, construirlo, seleccionar piezas/articulaciones, animarlo y exportar GLB. El editor anterior mantiene humanoides y ángeles paramétricos.

El reconocimiento básico de texto identifica **solamente** esas plantillas; una instrucción desconocida debe producir un mensaje honesto, no una figura distinta presentada como resultado final.

## Comunicación entre chat y web

Desde un chat que disponga de herramientas MCP compatibles se pueden invocar `mcp_get_reference_image` y `mcp_asset_build`. **Esta conversación de ChatGPT, por tener acceso a GitHub, no obtiene automáticamente acceso al WebSocket `localhost` del usuario.** Habilitar una conexión remota desde servicios de IA requerirá un servidor MCP HTTPS, autenticación, permisos y un cliente compatible, y no debe exponer sesiones mediante un ID de sala sin autenticar.

## Mejoras siguientes

1. Visualización y edición de partes seleccionadas con materiales PBR avanzados y geometrías personalizadas.
2. Curvas Bézier, extrusión, revolución, superficies de subdivisión y CSG para ampliar las formas disponibles.
3. Rigging automático guiado y pesos para personajes orgánicos que necesiten flexionar piel.
4. Plantillas comunitarias de alta calidad con licencias verificadas, materiales y texturas optimizadas para móviles.
5. Refinamiento iterativo con IA visual autorizada y captura multivista.
6. Guardado, deshacer/rehacer, LOD y compresión GLB para juegos/WebAR.

**Licencia del código:** MIT. Los assets externos requieren comprobar sus licencias por separado.
