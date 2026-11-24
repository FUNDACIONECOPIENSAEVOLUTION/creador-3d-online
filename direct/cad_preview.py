"""Generate lightweight CAD previews from locally generated FCStd files using FreeCAD CLI."""
import os, pathlib, subprocess, sys, tempfile
ROOT=pathlib.Path(__file__).resolve().parent.parent/"projects"
exe=os.environ.get("ECOBLEND_FREECAD")
if not exe or not pathlib.Path(exe).is_file(): raise SystemExit("FreeCAD CLI not configured")
for job in ROOT.glob("job-*"):
    src=job/"demo.FCStd"; dst=job/"preview.json"
    if not src.is_file() or (dst.exists() and dst.stat().st_mtime>=src.stat().st_mtime): continue
    code=f"""import FreeCAD as App, json, pathlib
doc=App.openDocument({str(src)!r})
items=[]
for o in doc.Objects:
    if not hasattr(o,'Shape') or o.Shape.isNull(): continue
    shape=o.Shape
    v,f=shape.tessellate(0.2)
    items.append(dict(name=o.Name,vertices=[[p.x,p.y,p.z] for p in v],faces=[list(t) for t in f],valid=shape.isValid(),volume=shape.Volume))
pathlib.Path({str(dst)!r}).write_text(json.dumps(items),encoding='utf-8')
App.closeDocument(doc.Name)
"""
    with tempfile.TemporaryDirectory() as t:
        script=pathlib.Path(t)/"preview.py"; script.write_text(code,encoding="utf-8")
        with (job/"preview.log").open("w") as log:
            p=subprocess.run([exe,str(script)],stdout=log,stderr=subprocess.STDOUT,timeout=120)
    print(job.name, "OK" if p.returncode==0 and dst.exists() else "ERROR",flush=True)
