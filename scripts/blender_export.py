"""
Exportar un personaje ya modelado/riggeado en Blender a GLB para NeoBlender.
NO convierte imágenes en humanos automáticamente. Necesita archivo .blend real.
Ejemplo:
  blender --background personaje.blend --python scripts/blender_export.py -- --output salida/personaje.glb
"""
import argparse
import os
import sys
from pathlib import Path

try:
    import bpy
except ImportError:
    raise SystemExit("Ejecuta este script mediante Blender: blender --background archivo.blend --python scripts/blender_export.py -- ...")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Ruta del archivo GLB generado")
    parser.add_argument("--max-mb", type=float, default=15.0, help="Presupuesto de tamaño, solo advertencia")
    args = parser.parse_args(argv)
    if not bpy.data.filepath:
        raise SystemExit("Abre primero un .blend con el personaje creado.")
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    # Exporta esqueletos, materiales, morphs y acciones NLA/activas si están configuradas.
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        use_selection=False,
        export_cameras=False,
        export_lights=False,
        export_animations=True,
        export_skins=True,
        export_morph=True,
    )
    mb = output.stat().st_size / 1048576
    print(f"GLB EXPORTADO: {output} ({mb:.2f} MiB)")
    if mb > args.max_mb:
        print(
            f"ADVERTENCIA: supera el objetivo de {args.max_mb:g} MiB; "
            "optimiza texturas/mallas antes de usar WebAR.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
