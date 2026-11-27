"""Roof assembly visualization, preserving validated cut geometry and existing wood."""
import argparse,json,math,pathlib,tempfile,subprocess,sys,os
from agent_v04 import locate
from roof_stock_v0910 import pack
def assembly(roofs,overlap=.09):
    if not 0<=overlap<=.2:raise ValueError("Invalid overlap")
    result=[]
    for r in roofs:
        w,d,x,y=[r[k] for k in ("width","depth","x","y")]
        h=min(w,d)/2
        for side in ("S","N","W","E"):
            L=w if side in ("S","N") else d
            def ab(v):
                X,Y=v[0]-x,v[1]-y
                return {"S":(X,Y),"N":(w-X,d-Y),"W":(d-Y,X),"E":(Y,w-X)}[side]
            f=next(f for f in r["faces"] if f["side"]==side)
            p=max(v[2] for v in f["vertices"])/h
            def pt(a,b,z=0):
                X,Y={"S":(a,b),"N":(w-a,d-b),"W":(b,d-a),"E":(w-b,a)}[side]
                return [x+X,y+Y,b*p+z]
            sheets=[q for q in r["sheets"] if q["side"]==side]
            for i,q in enumerate(sheets):
                lo=min(ab(v)[0] for v in q["vertices"]);hi=max(ab(v)[0] for v in q["vertices"])
                # Extend only toward next sheet, clipping to actual hip; no change to core cut IDs.
                end=min(L,hi+overlap) if i<len(sheets)-1 else hi
                knots=sorted({lo,end,*[t for t in (h,L-h) if lo<t<end]})
                z=.003 if i%2==0 else .006
                verts=[pt(lo,0,z),pt(end,0,z)]+[pt(a,min(a,L-a,h),z) for a in reversed(knots)]
                clean=[]
                for v in verts:
                    if not clean or math.dist(v,clean[-1])>1e-8:clean.append(v)
                if math.dist(clean[0],clean[-1])<1e-8:clean.pop()
                actual=max(min(a,L-a,h) for a in knots)*math.hypot(1,p)
                result.append(dict(id=q["id"],kind="tile",color=i%2,vertices=clean,length=actual,width=end-lo,overlap=end-hi))
        for q in r["wood"]:
            result.append(dict(id=q["id"],kind="wood",vertices=q["ribbon"],length=q["length"],width=q["contact_width"]))
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument("--project",type=pathlib.Path);p.add_argument("--selftest",action="store_true");a=p.parse_args()
    if a.selftest:
        from roof_engine_v099 import build
        r=build({"pitch":.35,"useful_width":.96,"spacing":.8,"stock":11.8,"roofs":[{"id":"T9","width":8,"depth":6,"x":0,"y":0}]})
        q=assembly(r);assert len(q)==len(r[0]["sheets"])+len(r[0]["wood"])
        assert all(v["width"]<=1.05+1e-8 for v in q if v["kind"]=="tile")
        assert any(v.get("overlap",0)>.08 for v in q)
        print("ASSEMBLY SELFTEST OK");return
    if not a.project:p.error("project required")
    src=a.project.resolve();roofs=json.loads((src/"roof_data.json").read_text(encoding="utf-8"))
    objects=assembly(roofs)
    out=pathlib.Path(tempfile.mkdtemp(prefix="job-",dir=src.parent))
    (out/"assembly.json").write_text(json.dumps(objects),encoding="utf-8")
    (out/"studio_project.json").write_text(json.dumps({"name":"Cubiertas | montaje transparente","state":"active"}),encoding="utf-8")
    tiles=[q for q in objects if q["kind"]=="tile"]
    options=[]
    for stock in (11.8,5.9,5.8):
        bins=pack(tiles,stock)
        options.append({"stock":stock,"count":len(bins),"unused":round(len(bins)*stock-sum(b["used"] for b in bins),3),"bins":bins})
    (out/"assembly_stock.json").write_text(json.dumps(options,indent=2),encoding="utf-8")
    (out/"roof_data.json").write_text(json.dumps(roofs),encoding="utf-8")
    blender="""import bpy,json,pathlib
out=pathlib.Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(name,c,alpha):
    m=bpy.data.materials.new(name);m.diffuse_color=(*c,alpha);m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*c,1);b.inputs['Alpha'].default_value=alpha
    if alpha<1:m.surface_render_method='DITHERED'
    return m
mats=[mat('UPVC naranja',(.82,.23,.07),.52),mat('UPVC verde claro',(.48,.82,.30),.52),mat('Madera existente',(.28,.12,.045),1)]
for q in json.loads((out/'assembly.json').read_text()):
    mesh=bpy.data.meshes.new(q['id']);vs=q['vertices']
    if q['kind']=='wood':
        vs=[(v[0],v[1],v[2]-.006) for v in vs]
    mesh.from_pydata(vs,[],[list(range(len(vs)))]);mesh.update()
    ob=bpy.data.objects.new(q['id'],mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(mats[q['color'] if q['kind']=='tile' else 2])
    if q['kind']=='wood':
        # Visual depth only: actual timber height unknown.
        mod=ob.modifiers.new('Profundidad ilustrativa','SOLIDIFY');mod.thickness=.05;mod.offset=-1
    ob['cut_length_m']=q['length'];ob['contact_or_sheet_width_m']=q['width']
bpy.ops.wm.save_as_mainfile(filepath=str(out/'demo.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'demo.glb'),export_format='GLB',export_extras=True,export_apply=True)
"""
    freecad="""import FreeCAD as App,Part,pathlib,json
out=pathlib.Path(__file__).parent
doc=App.newDocument('RoofAssembly')
groups={}
for q in json.loads((out/'assembly.json').read_text()):
    key=q['id'].split('_')[0]+'_'+q['kind']
    if key not in groups:groups[key]=doc.addObject('App::DocumentObjectGroup',key)
    v=[App.Vector(*[c*1000 for c in p]) for p in q['vertices']]
    shape=Part.Face(Part.makePolygon(v+[v[0]]))
    assert shape.isValid()
    ob=doc.addObject('Part::Feature',q['id']);ob.Shape=shape;groups[key].addObject(ob)
    ob.addProperty('App::PropertyLength','CutLength','EcoBlend');ob.CutLength=q['length']*1000
    if App.GuiUp:
        ob.ViewObject.ShapeColor=(.8,.25,.08) if q.get('color')==0 else (.5,.8,.3) if q['kind']=='tile' else (.35,.18,.08)
        ob.ViewObject.Transparency=48 if q['kind']=='tile' else 0
doc.recompute();doc.saveAs(str(out/'demo.FCStd'))
"""
    results={}
    for engine,script,expected in [("blender",blender,["demo.blend","demo.glb"]),("freecad",freecad,["demo.FCStd"])]:
        exe=locate(engine)
        if not exe:raise RuntimeError(engine+" unavailable")
        macro=out/(engine+"_assembly.py");macro.write_text(script,encoding="utf-8")
        cmd=[exe,"--background","--threads","2","--factory-startup","--disable-autoexec","--python-exit-code","1","--python"] if engine=="blender" else [exe]
        with (out/(engine+".log")).open("w",encoding="utf-8") as log:
            proc=subprocess.run(cmd+[str(macro)],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=240)
        results[engine]=proc.returncode==0 and all((out/f).is_file() and (out/f).stat().st_size for f in expected)
    print(json.dumps({"ok":all(results.values()),"folder":str(out),"engines":results,"tiles":len(tiles),"wood":len(objects)-len(tiles),"stock":[{k:v for k,v in o.items() if k!="bins"} for o in options]}))
    if not all(results.values()):sys.exit(1)
if __name__=="__main__":main()
