"""EcoBlend Architecture 0.5: local rectangular shell, explicit dimensions in metres.
No network, no automatic plan inference. Original inputs are not modified.
"""
import argparse, json, math, pathlib, subprocess, sys, tempfile, html
from agent_v04 import locate
ROOT=pathlib.Path(__file__).resolve().parent.parent/"projects"
DEMO={"width":8,"depth":6,"height":2.8,"wall":0.2,"openings":[{"side":"F01","offset":3,"width":1,"bottom":0,"height":2.1},{"side":"F03","offset":2,"width":1.4,"bottom":1,"height":1.1}]}
def number(v,lo,hi):
    if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi: raise ValueError("Dimension fuera de rango")
    return float(v)
def build(spec):
    if set(spec)!={"width","depth","height","wall","openings"}: raise ValueError("Campos esperados: width, depth, height, wall, openings")
    w=number(spec["width"],2,100); d=number(spec["depth"],2,100); h=number(spec["height"],2,12); t=number(spec["wall"],.08,.6)
    openings=spec["openings"]
    if not isinstance(openings,list) or len(openings)>30: raise ValueError("Maximo 30 aberturas")
    sides={"F01":(w,0,0,True),"F02":(w,0,d-t,True),"F03":(d-2*t,0,t,False),"F04":(d-2*t,w-t,t,False)}
    pieces=[dict(id="P01",xyz=[0,0,-t],size=[w,d,t],color=[.46,.42,.36])]
    surfaces=[]
    for side,(length,x,y,horiz) in sides.items():
        cuts=[]
        for o in openings:
            if not isinstance(o,dict) or set(o)!={"side","offset","width","bottom","height"} or o["side"] not in sides: raise ValueError("Abertura invalida")
            if o["side"]!=side: continue
            a=number(o["offset"],0,length); b=a+number(o["width"],.2,length)
            c=number(o["bottom"],0,h); e=c+number(o["height"],.2,h)
            if a<.05 or b>length-.05 or e>h-.05: raise ValueError("Abertura fuera del muro")
            if any(a<B and b>A and c<E and e>C for A,B,C,E in cuts): raise ValueError("Aberturas superpuestas")
            cuts.append((a,b,c,e))
        xs=sorted({0,length,*[v for a,b,c,e in cuts for v in (a,b)]})
        zs=sorted({0,h,*[v for a,b,c,e in cuts for v in (c,e)]})
        for a,b in zip(xs,xs[1:]):
            for c,e in zip(zs,zs[1:]):
                if any(A<=(a+b)/2<=B and C<=(c+e)/2<=E for A,B,C,E in cuts): continue
                xyz=[x+a,y,c] if horiz else [x,y+a,c]
                size=[b-a,t,e-c] if horiz else [t,b-a,e-c]
                pieces.append(dict(id=side+"_"+str(len(pieces)),xyz=xyz,size=size,color=[.8,.78,.72]))
        surfaces.append(dict(id=side,label={"F01":"Frente","F02":"Posterior","F03":"Izquierda","F04":"Derecha"}[side],length_m=length,height_m=h,reference_status="pendiente",photo_request="Foto perpendicular y dos oblicuas; evitar objetos transitorios"))
    surfaces.extend([dict(id="P01",label="Piso",reference_status="pendiente",photo_request="Foto de material a escala"),dict(id="C01",label="Cubierta no modelada",reference_status="pendiente",photo_request="Plano de cubierta y alturas")])
    return pieces,surfaces
def main():
    p=argparse.ArgumentParser(); p.add_argument("--demo",action="store_true"); p.add_argument("--spec",type=pathlib.Path); p.add_argument("--selftest",action="store_true"); p.add_argument("--engine",choices=["blender","freecad","both"],default="both"); a=p.parse_args()
    if a.selftest:
        pieces,surfaces=build(DEMO)
        assert len(surfaces)==6 and len({o["id"] for o in pieces})==len(pieces)
        assert all(min(o["size"])>0 for o in pieces)
        actual=sum(math.prod(o["size"]) for o in pieces)
        expected=8*6*.2+(2*8+2*(6-.4))*2.8*.2-(1*2.1+1.4*1.1)*.2
        assert abs(actual-expected)<1e-8
        try: build(dict(DEMO,wall=-1))
        except ValueError: pass
        else: raise AssertionError("Invalid wall accepted")
        print("SELFTEST OK: dimensiones, volumen, identificadores, rechazo de datos invalidos"); return
    if a.demo==bool(a.spec): p.error("Seleccione --demo o --spec")
    spec=DEMO if a.demo else json.loads(a.spec.read_text(encoding="utf-8-sig"))
    pieces,surfaces=build(spec)
    ROOT.mkdir(exist_ok=True); out=pathlib.Path(tempfile.mkdtemp(prefix="job-",dir=ROOT))
    report={"units":"m","demo":a.demo,"spec":spec,"surfaces":surfaces,"pieces":pieces,"limitations":["Una planta rectangular","Sin cubierta, divisiones interiores ni materiales fotograficos","No es plano de construccion"]}
    (out/"surface_inventory.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    w,d=spec["width"],spec["depth"]; k=340/max(w,d); X=70; Y=60; W=w*k; D=d*k
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="470" viewBox="0 0 500 470"><rect width="500" height="470" fill="white"/><g font-family="Arial" font-size="13" fill="#173e3b"><text x="20" y="25">EcoBlend - mapa de referencias (frente abajo)</text><rect x="{X}" y="{Y}" width="{W}" height="{D}" fill="#e2f1ee" stroke="#173e3b" stroke-width="3"/><text x="{X+W/2}" y="{Y+D+20}" text-anchor="middle">F01 Frente</text><text x="{X+W/2}" y="{Y-10}" text-anchor="middle">F02 Posterior</text><text x="{X-8}" y="{Y+D/2}" text-anchor="end">F03</text><text x="{X+W+8}" y="{Y+D/2}">F04</text><text x="{X+W/2}" y="{Y+D/2}" text-anchor="middle">P01 Piso / C01 Cubierta</text></g></svg>'
    (out/"surface_map.svg").write_text(svg,encoding="utf-8")
    engines=["blender","freecad"] if a.engine=="both" else [a.engine]; results={}
    for engine in engines:
        exe=locate(engine)
        if not exe: results[engine]=False; continue
        if engine=="blender":
            script=f"""import bpy, pathlib
out=pathlib.Path({str(out)!r})
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
for p in {pieces!r}:
    bpy.ops.mesh.primitive_cube_add(size=1,location=[x+s/2 for x,s in zip(p['xyz'],p['size'])])
    o=bpy.context.object
    o.name=p['id']; o.dimensions=p['size']
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mat=bpy.data.materials.get('Floor' if p['id']=='P01' else 'Wall')
    if not mat:
        mat=bpy.data.materials.new('Floor' if p['id']=='P01' else 'Wall')
        mat.diffuse_color=(*p['color'],1)
        mat.use_nodes=True
        mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*p['color'],1)
    o.data.materials.append(mat)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'demo.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'demo.glb'),export_format='GLB')
"""
            cmd=[exe,"--background","--factory-startup","--disable-autoexec","--python-exit-code","1","--python"]; expected=["demo.blend","demo.glb"]
        else:
            script=f"""import FreeCAD as App, Part, pathlib
out=pathlib.Path({str(out)!r})
doc=App.newDocument('Architecture')
objects=[]
for p in {pieces!r}:
    o=doc.addObject('Part::Box',p['id'])
    o.Length,o.Width,o.Height=[v*1000 for v in p['size']]
    o.Placement.Base=App.Vector(*[v*1000 for v in p['xyz']])
    objects.append(o)
doc.recompute()
assert all(o.Shape.isValid() and o.Shape.Volume>0 for o in objects)
doc.saveAs(str(out/'demo.FCStd'))
Part.export(objects,str(out/'demo.step'))
"""
            cmd=[exe]; expected=["demo.FCStd","demo.step"]
        path=out/(engine+"_build.py"); path.write_text(script,encoding="utf-8")
        with (out/(engine+".log")).open("w",encoding="utf-8") as log:
            try:
                proc=subprocess.run(cmd+[str(path)],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=240)
                results[engine]=proc.returncode==0 and all((out/f).is_file() and (out/f).stat().st_size>0 for f in expected)
            except subprocess.TimeoutExpired: results[engine]=False
    print(json.dumps({"ok":all(results.values()),"folder":str(out),"engines":results,"pieces":len(pieces),"surfaces":len(surfaces)}))
    if not all(results.values()): sys.exit(1)
if __name__=="__main__": main()
