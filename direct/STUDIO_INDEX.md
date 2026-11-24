# EcoBlend Studio — índice de desarrollo

## Componentes
| Archivo | Función | Estado |
|---|---|---|
| agent.py | CLI inicial | Validado localmente |
| agent_v04.py | Ensamblajes Blender / FreeCAD | Validado localmente |
| panel_v031.py | Panel y buzón JSON | Base validada |
| gallery.py | Visor GLB | Validado localmente |
| cad_preview.py | Teselación CAD | Pendiente de integración |
| architecture_v05.py | Geometría rectangular, aberturas e inventario | Pendiente de prueba Windows |
| STUDIO_SKILLS.md | Procedimientos especializados | Documentación |
| install_v05.ps1 | Instalador del módulo arquitectura | Pendiente de prueba Windows |

## Instalación y versiones
Ejecutar install_v05.ps1 desde PowerShell tras revisar su contenido. No requiere administrador. No modifica el panel, el visor ni los proyectos existentes. Descarga los archivos de una revisión fija y ejecuta la prueba de geometría; la demo de los motores es opcional.

## Próximos módulos
1. Architecture: planos arbitrarios, niveles, interiores, cubiertas e inventario fotográfico.
2. Reality: referencias locales, UV, materiales PBR y proyección fotográfica.
3. Explorer: visor ligero, CAD, recorrido, panoramas y exportación AR.
4. Anatomy: inventario y licencias, capas, atlas, etiquetas y revisión especializada.
5. Engineering: CAD paramétrico, despieces y validaciones.
6. Games: rigging y clips reutilizables.
7. Product Studio: renders y video.

## Privacidad
Repositorio público: solo código, documentación y demos sintéticas. Planos reales, fotos, credenciales y datos clínicos permanecen locales. El buzón público no es una API privada. Nunca ejecutar código arbitrario recibido en un encargo. No afirmar capacidades pendientes como operativas.
