"""EcoBlend Direct: local, allowlisted CLI. No network listener or remote code."""
import argparse, json, os, pathlib, shutil, subprocess, sys, math
ROOT=pathlib.Path.home()/"EcoBlendDirect"
def locate(name):
    env=os.environ.get("ECOBLEND_"+name.upper())
    if env and pathlib.Path(env).is_file(): return env
    for n in (["blender.exe","blender"] if name=="blender" else ["FreeCADCmd.exe","freecadcmd","FreeCADCmd"]):
        p=shutil.which(n)
        if p: return p
    base=pathlib.Path(os.environ.get("ProgramFiles",r"C:\Program Files"))
    patterns=["Blender Foundation/Blender 4.4*/blender.exe","Blender Foundation/Blender */blender.exe"] if name=="blender" else ["FreeCAD*/bin/FreeCADCmd.exe","FreeCAD*/bin/freecadcmd.exe"]
    for pat in patterns:
        found=sorted(base.glob(pat),reverse=True)
        if found: return str(found[0])
    return None
def main():
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=["status","demo"])
    p.add_argument("--engine",choices=["blender","freecad"],default="blender")
    p.add_argument("--size",type=float,default=2)
    a=p.parse_args()
    engines={n:locate(n) for n in ("blender","freecad")}
    if a.action=="status":
        print(json.dumps(engines)); return
    if not math.isfinite(a.size) or not 0.01<=a.size<=10000: p.error("Invalid size")
    exe=engines[a.engine]
    if not exe: p.error("Engine not found; set ECOBLEND_"+a.engine.upper())
    import tempfile
    ROOT.mkdir(exist_ok=True)
    out=pathlib.Path(tempfile.mkdtemp(prefix="job-",dir=ROOT))
    s=repr(str(out))
    if a.engine=="blender":
        code=f"""import bpy, pathlib
out=pathlib.Path({s})
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size={a.size})
obj=bpy.context.object
obj.name='EcoBlend demo'
mat=bpy.data.materials.new('EcoBlend teal')
mat.diffuse_color=(0.04,0.55,0.42,1)
obj.data.materials.append(mat)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'demo.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'demo.glb'),export_format='GLB')
"""
        args=[exe,"--background","--factory-startup","--disable-autoexec","--python-exit-code","1","--python",str(out/"job.py")]
        expected=["demo.blend","demo.glb"]
    else:
        code=f"""import FreeCAD as App, Part, pathlib
out=pathlib.Path({s})
doc=App.newDocument('EcoBlendDemo')
obj=doc.addObject('Part::Box','Box')
obj.Length={a.size}
obj.Width={a.size}
obj.Height={a.size}
doc.recompute()
doc.saveAs(str(out/'demo.FCStd'))
Part.export([obj],str(out/'demo.step'))
"""
        args=[exe,str(out/"job.py")]
        expected=["demo.FCStd","demo.step"]
    (out/"job.py").write_text(code,encoding="utf-8")
    with (out/"engine.log").open("w",encoding="utf-8") as log:
        result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180,cwd=out)
    ok=result.returncode==0 and all((out/f).is_file() and (out/f).stat().st_size>0 for f in expected)
    print(json.dumps({"ok":ok,"engine":a.engine,"folder":str(out),"files":[f for f in expected if (out/f).exists()],"exit":result.returncode}))
    if not ok: sys.exit(1)
if __name__=="__main__": main()
