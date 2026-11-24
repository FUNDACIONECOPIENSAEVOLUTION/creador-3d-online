# EcoBlend Studio — perfiles especializados
Estado: especificaciones de trabajo, no certificación de capacidades implementadas.

## Núcleo común
- Motores CLI locales; no MCP para Blender/FreeCAD. Sin código remoto arbitrario.
- Archivos privados y fotografías permanecen locales; el buzón público solo admite pruebas no confidenciales.
- Versionar geometría, materiales, referencias, informes y exportaciones. No sobrescribir originales.
- Unidades explícitas: CAD mm, glTF m. Identificadores estables por elemento.
- Previsualizar bajo demanda, CPU preferida, preservar editables. Validar exportaciones y registrar errores.
- Las habilidades son guías Markdown del repositorio; no plugins instalados automáticamente.

## Architecture
1. Interpretar plano y escala; separar medidas verificadas, supuestas y faltantes.
2. Definir frente con el usuario, ejes, niveles, muros, aberturas, cubierta y espacios. No inferir norte real sin referencia.
3. Crear inventario de superficies con ID, orientación, dimensiones, referencia fotográfica y estado.
4. Solicitar fotos por superficie: frontal, posterior, laterales, cubierta, interiores. Registrar vista y derechos.
5. Rectificar perspectiva y limpiar objetos transitorios; marcar reconstrucciones inventadas. Conservar originales.
6. Para diseños nuevos, generar propuesta de fachada coherente en varias vistas, aprobarla y traducir a geometría y materiales.
7. Mapear UV a escala, separar albedo de sombras, PBR, decals y geometría de detalles sobresalientes.
8. Preparar recorrido con cámara a altura humana, puertas transitables, colisiones y puntos de interés.
9. Exportar BLEND, FCStd/STEP si aplica, GLB en metros, USDZ cuando haya herramienta validada. AR requiere dispositivo compatible y prueba.
10. Comparar renders con planos y referencias, verificar dimensiones y obtener aprobación.

## Anatomy
Inventariar activos existentes, licencia, fuente anatómica, lateralidad, estructura, nivel de detalle y faltantes.
Usar terminología anatómica normalizada, IDs estables, capas y etiquetas.
Separar modelos educativos de modelos clínicos; revisión por especialistas. No presentar reconstrucción generativa como anatomía verificada.
Libro: capítulo, estructura, texto, referencia, modelo, hotspot, QR/enlace AR. Telemedicina requiere evaluación clínica, privacidad y validación.

## Engineering
Definir requisitos, materiales, unidades, interfaces, tolerancias y supuestos. CAD paramétrico, despiece, verificación geométrica y documentación.
Simulaciones solo cuando herramientas, condiciones y materiales sean conocidos.
Hidrógeno: balance energético y seguridad; electrólisis requiere energía externa, el agua no es combustible neto. No diseñar mezclas explosivas ni sistemas de combustión improvisados.

## Games
Importar GLB/FBX/OBJ, validar licencia y malla, topología y rig. Retopología y skinning si procede.
Clips: idle, walk, attack, hit, death, return; definir duración, root motion, eventos y transiciones.
Probar deformaciones, contactos y exportación en motor de destino. Un modelo generado por IA no implica rig funcional.

## Product
Geometría fiel, materiales PBR, iluminación de estudio, cámaras, storyboard, turntable y clips.
Distinguir renders de fotografías reales. No inventar prestaciones comerciales.
