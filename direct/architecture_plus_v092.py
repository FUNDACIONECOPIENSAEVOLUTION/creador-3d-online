"""EcoBlend Architecture 0.5: local rectangular shell, explicit dimensions in metres.
No network, no automatic plan inference. Original inputs are not modified.
"""
import argparse, json, math, pathlib, subprocess, sys, tempfile, html, re
from agent_v04 import locate
ROOT=pathlib.Path(__file__).resolve().parent.parent/"projects"
DEMO={"width":8,"depth":6,"height":2.8,"wall":0.2,"openings":[{"side":"F01","offset":3,"width":1,"bottom":0,"height":2.1},{"side":"F03","offset":2,"width":1.4,"bottom":1,"height":1.1}]}
def number(v,lo,hi):
    if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi: raise ValueError("Dimension fuera de rango")
    return float(v)
def shell(spec):
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
BASE_DEMO=DEMO
DEMO=dict(BASE_DEMO,partitions=[{"id":"M01","axis":"y","x":4,"y":.2,"length":5.6,"thickness":.12,"doors":[{"offset":1,"width":.9,"height":2.1}]},{"id":"M02","axis":"x","x":.2,"y":3,"length":3.8,"thickness":.12,"doors":[{"offset":1,"width":.9,"height":2.1}]}],rooms=[{"id":"I01","name":"Sala y cocina","rect":[4.12,.2,3.68,5.6]},{"id":"I02","name":"Habitacion","rect":[.2,.2,3.8,2.8]},{"id":"I03","name":"Estudio","rect":[.2,3.12,3.8,2.68]}])
# Demonstration only: not a construction plan.
DEMO["roof"]={"type":"flat","thickness":.15,"overhang":.25}
def build(spec):
    if set(spec)-{"width","depth","height","wall","openings","partitions","rooms","roof"}:raise ValueError("Campos invalidos")
    pieces,surfaces=shell({k:spec[k] for k in ("width","depth","height","wall","openings")})
    w,d,h,t=[spec[k] for k in ("width","depth","height","wall")]
    bounds=[];ids=set()
    for m in spec.get("partitions",[]):
        import re
        k=m["id"]
        if not re.fullmatch(r"M[0-9]{2,4}",k) or k in ids:raise ValueError("ID muro invalido")
        ids.add(k)
        if m["axis"] not in ("x","y"):raise ValueError("Eje invalido")
        x=number(m["x"],t,w-t);y=number(m["y"],t,d-t);L=number(m["length"],.3,max(w,d));T=number(m["thickness"],.08,.4);horizontal=m["axis"]=="x"
        a,b=(L,T) if horizontal else (T,L)
        if x+a>w-t+1e-8 or y+b>d-t+1e-8:raise ValueError("Muro fuera de planta")
        if any(min(x+a,X+A)-max(x,X)>1e-8 and min(y+b,Y+B)-max(y,Y)>1e-8 for X,Y,A,B in bounds):raise ValueError("Muros interiores superpuestos")
        bounds.append((x,y,a,b))
        cuts=[]
        for door in m.get("doors",[]):
            u=number(door["offset"],.05,L);v=u+number(door["width"],.6,L);z=number(door["height"],1.8,h-.05)
            if v>L-.05 or any(u<V and v>U for U,V,Z in cuts):raise ValueError("Puerta invalida")
            cuts.append((u,v,z))
        xs=sorted({0,L,*[q for u,v,z in cuts for q in (u,v)]})
        for u,v in zip(xs,xs[1:]):
            z=next((Z for U,V,Z in cuts if U<(u+v)/2<V),0)
            pieces.append(dict(id=k+"_"+str(len(pieces)),xyz=[x+u,y,z] if horizontal else [x,y+u,z],size=[v-u,T,h-z] if horizontal else [T,v-u,h-z],color=[.75,.78,.8]))
        for face in ("A","B"):
            surfaces.append(dict(id=k+"-"+face,label="Muro interior "+k+" cara "+face,length_m=L,height_m=h,reference_status="pendiente",axis=m["axis"],face=face))
    room_bounds=[]
    for r in spec.get("rooms",[]):
        k=r["id"]
        if not re.fullmatch(r"I[0-9]{2,4}",k) or k in ids:raise ValueError("ID ambiente invalido")
        ids.add(k)
        x,y,a,b=r["rect"];number(x,t,w-t);number(y,t,d-t);number(a,.5,w);number(b,.5,d)
        if x+a>w-t+1e-8 or y+b>d-t+1e-8:raise ValueError("Ambiente fuera de planta")
        if any(min(x+a,X+A)-max(x,X)>1e-8 and min(y+b,Y+B)-max(y,Y)>1e-8 for X,Y,A,B in bounds+room_bounds):raise ValueError("Ambiente superpuesto")
        room_bounds.append((x,y,a,b))
        surfaces.append(dict(id=k+"-P",label=r["name"]+" piso",dimensions_m=[a,b],reference_status="pendiente",rect=r["rect"]))
        pieces.append(dict(id=k+"-P",xyz=[x,y,0],size=[a,b,.005],color=[.55,.48,.40]))
    for k in ("F01","F02","F03","F04"):
        original=next(v for v in surfaces if v["id"]==k)
        surfaces.append(dict(original,id=k+"-IN",label="Interior "+original["label"]))
    roof=spec.get("roof")
    if roof:
        if roof.get("type")!="flat" or set(roof)!={"type","thickness","overhang"}:raise ValueError("Cubierta plana: type, thickness, overhang")
        rt=number(roof["thickness"],.05,.5);oh=number(roof["overhang"],0,1.5)
        pieces.append(dict(id="C01",xyz=[-oh,-oh,h],size=[w+2*oh,d+2*oh,rt],color=[.32,.34,.36]))
        surfaces=[s for s in surfaces if s["id"]!="C01"]
        surfaces.extend([dict(id="C01",label="Cubierta superior",dimensions_m=[w+2*oh,d+2*oh],reference_status="pendiente"),dict(id="C01-IN",label="Cielo raso",dimensions_m=[w+2*oh,d+2*oh],reference_status="pendiente")])
    return pieces,surfaces
def interior_svg(spec,pieces):
    w,d=spec["width"],spec["depth"];k=480/max(w,d);X,Y=60,60
    elements=[]
    for r in spec.get("rooms",[]):
        x,y,a,b=r["rect"];elements.append(f'<rect x="{X+x*k}" y="{Y+(d-y-b)*k}" width="{a*k}" height="{b*k}" fill="#e3f1ed"/><text x="{X+(x+a/2)*k}" y="{Y+(d-y-b/2)*k}" text-anchor="middle">{html.escape(r["name"])} ({a*b:.1f} m2)</text>')
    for p in pieces:
        if p["id"]=="P01" or p["id"].endswith('-P') or p["xyz"][2]>.01:continue
        x,y,z=p["xyz"];a,b,c=p["size"];elements.append(f'<rect x="{X+x*k}" y="{Y+(d-y-b)*k}" width="{a*k}" height="{b*k}" fill="#29464a"/>')
    return '<svg xmlns="http://www.w3.org/2000/svg" width="620" height="620"><rect width="620" height="620" fill="white"/><g font-family="Arial" font-size="12"><text x="20" y="25">EcoBlend - anteproyecto conceptual, no constructivo</text>'+''.join(elements)+'</g></svg>'
def main():
    p=argparse.ArgumentParser(); p.add_argument("--demo",action="store_true"); p.add_argument("--spec",type=pathlib.Path); p.add_argument("--selftest",action="store_true"); p.add_argument("--engine",choices=["blender","freecad","both"],default="both"); a=p.parse_args()
    if a.selftest:
        pieces,surfaces=build(DEMO)
        assert len(surfaces)==18 and len({o["id"] for o in pieces})==len(pieces)
        assert all(min(o["size"])>0 for o in pieces)
        actual=sum(math.prod(o["size"]) for o in pieces)
        expected=8*6*.2+(2*8+2*(6-.4))*2.8*.2-(1*2.1+1.4*1.1)*.2
        assert abs(sum(math.prod(o["size"]) for o in shell(BASE_DEMO)[0])-expected)<1e-8
        assert len([o for o in pieces if o["id"].startswith("M")])==6
        assert "<svg" in interior_svg(DEMO,pieces)
        try: build(dict(DEMO,wall=-1))
        except ValueError: pass
        else: raise AssertionError("Invalid wall accepted")
        print("SELFTEST OK: dimensiones, volumen, identificadores, rechazo de datos invalidos"); return
    if a.demo==bool(a.spec): p.error("Seleccione --demo o --spec")
    spec=DEMO if a.demo else json.loads(a.spec.read_text(encoding="utf-8-sig"))
    pieces,surfaces=build(spec)
    ROOT.mkdir(exist_ok=True); out=pathlib.Path(tempfile.mkdtemp(prefix="job-",dir=ROOT))
    report={"units":"m","demo":a.demo,"spec":spec,"surfaces":surfaces,"pieces":pieces,"limitations":["Una planta rectangular","Cubierta plana opcional; sin calculo estructural ni materiales fotograficos","No es plano de construccion"]}
    (out/"surface_inventory.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    w,d=spec["width"],spec["depth"]; k=340/max(w,d); X=70; Y=60; W=w*k; D=d*k
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="470" viewBox="0 0 500 470"><rect width="500" height="470" fill="white"/><g font-family="Arial" font-size="13" fill="#173e3b"><text x="20" y="25">EcoBlend - mapa de referencias (frente abajo)</text><rect x="{X}" y="{Y}" width="{W}" height="{D}" fill="#e2f1ee" stroke="#173e3b" stroke-width="3"/><text x="{X+W/2}" y="{Y+D+20}" text-anchor="middle">F01 Frente</text><text x="{X+W/2}" y="{Y-10}" text-anchor="middle">F02 Posterior</text><text x="{X-8}" y="{Y+D/2}" text-anchor="end">F03</text><text x="{X+W+8}" y="{Y+D/2}">F04</text><text x="{X+W/2}" y="{Y+D/2}" text-anchor="middle">P01 Piso / C01 Cubierta</text></g></svg>'
    (out/"surface_map.svg").write_text(svg,encoding="utf-8")
    (out/"interior_plan.svg").write_text(interior_svg(spec,pieces),encoding="utf-8")
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
    o.name=p['id']; o.data.name=p['id']; o.dimensions=p['size']
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    key='Roof' if p['id']=='C01' else 'Floor' if p['id']=='P01' or p['id'].endswith('-P') else 'Wall'
    mat=bpy.data.materials.get(key)
    if not mat:
        mat=bpy.data.materials.new(key)
        mat.diffuse_color=(*p['color'],1)
        mat.use_nodes=True
        mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*p['color'],1)
    o.data.materials.append(mat)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'demo.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'demo.glb'),export_format='GLB',export_extras=True)
"""
            cmd=[exe,"--background","--factory-startup","--disable-autoexec","--python-exit-code","1","--python"]; expected=["demo.blend","demo.glb"]
        else:
            script=f"""import FreeCAD as App, Part, pathlib
out=pathlib.Path({str(out)!r})
doc=App.newDocument('Architecture')
objects=[]
for p in {pieces!r}:
    o=doc.addObject('Part::Box',p['id'].replace('-','_'))
    o.Label=p['id']
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
