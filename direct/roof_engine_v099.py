"""EcoBlend Roof Engineering 0.9.9. Rectangular equal-pitch hip roofs, preliminary takeoff."""
import argparse,csv,json,math,os,pathlib,subprocess,sys,tempfile,html
from agent_v04 import locate
ROOT=pathlib.Path(os.environ.get("ECOBLEND_PROJECTS",str(pathlib.Path(__file__).resolve().parent.parent/"projects")))
def num(x,a,b):
    if type(x) not in (float,int) or not math.isfinite(x) or not a<=x<=b:raise ValueError("Dimension invalida")
    return float(x)
def build(spec):
    if not {"pitch","useful_width","spacing","stock","roofs"}<=set(spec) or set(spec)-{"pitch","useful_width","spacing","stock","roofs","wood_spacing","wood_contact","simulate_metal"}:raise ValueError("Campos invalidos")
    p=num(spec["pitch"],.05,1); u=num(spec["useful_width"],.5,1.2); s=num(spec["spacing"],.3,1.5); stock=num(spec["stock"],2,12)
    if not isinstance(spec["roofs"],list) or not 1<=len(spec["roofs"])<=12:raise ValueError("Numero de cubiertas")
    ws=num(spec.get("wood_spacing",.8),.3,1.5); wc=num(spec.get("wood_contact",.05),.02,.2)
    metal=spec.get("simulate_metal",False)
    if type(metal) is not bool:raise ValueError("simulate_metal debe ser booleano")
    k=math.sqrt(1+p*p); roofs=[]; names=set()
    for r in spec["roofs"]:
        if set(r)!={"id","width","depth","x","y"}:raise ValueError("Campos cubierta")
        import re
        name=r["id"]
        if not isinstance(name,str) or not re.fullmatch(r"T[0-9]{1,3}",name) or name in names:raise ValueError("ID")
        names.add(name);w=num(r["width"],1,30);d=num(r["depth"],1,30);x=num(r["x"],-100,100);y=num(r["y"],-100,100)
        h=min(w,d)/2; faces=[]; sheets=[]; bars=[]; wood=[]
        for side,L in (("S",w),("N",w),("W",d),("E",d)):
            def point(a,b):
                X,Y={"S":(a,b),"N":(w-a,d-b),"W":(b,d-a),"E":(w-b,a)}[side]
                return [x+X,y+Y,b*p]
            poly=[point(0,0),point(L,0),point(L-h,h),point(h,h)]
            faces.append(dict(side=side,vertices=poly))
            for i in range(math.ceil(L/u-1e-9)):
                a=i*u;b=min(L,(i+1)*u)
                # Clip strip against hip boundaries, including apex/central plateau breakpoints
                knots=sorted({a,b,*[v for v in (h,L-h) if a<v<b]})
                upper=[(v,min(v,L-v,h)) for v in knots]
                length=max(t for _,t in upper)*k
                verts=[point(a,0),point(b,0)]+[point(v,t) for v,t in reversed(upper)]
                clean=[]
                for v in verts:
                    if not clean or math.dist(v,clean[-1])>1e-8:clean.append(v)
                if math.dist(clean[0],clean[-1])<1e-8:clean.pop()
                sheets.append(dict(id=f"{name}_{side}_P{i+1:02}",side=side,length=length,width=b-a,vertices=clean))
            # Existing rafters follow the fall, with a nominal 0.8 m axis spacing.
            # Grid starts at half pitch; actual phase and timber depth require survey.
            for i in range(math.ceil(L/ws)):
                a=(i+.5)*ws
                if a>=L:continue
                left=max(0,a-wc/2);right=min(L,a+wc/2)
                top=min(a,L-a,h); tl=min(left,L-left,h);tr=min(right,L-right,h)
                if top<=0:continue
                ribbon=[point(left,0),point(right,0),point(right,tr),point(left,tl)]
                wood.append(dict(id=f"{name}_{side}_W{i+1:02}",side=side,length=top*k,contact_width=wc,vertices=[point(a,0),point(a,top)],ribbon=ribbon))
            n=math.ceil(h*k/s-1e-9)
            for i in range(n+1):
                b=h*i/n; a=b; end=L-b
                if end-a>1e-8:bars.append(dict(id=f"{name}_{side}_C{i+1:02}",side=side,length=end-a,vertices=[point(a,b),point(end,b)]))
        # Merge coincident ridge segments only within the same roof.
        unique={}
        for b in bars:
            key=tuple(sorted(tuple(round(c,7) for c in v) for v in b["vertices"]))
            unique.setdefault(key,b)
        bars=list(unique.values()) if metal else []
        # First-fit decreasing, no diagonal scrap recovery; variable-length transverse cuts.
        bins=[]
        for a in sorted(sheets,key=lambda a:-a["length"]):
            length=a["length"]
            if length>stock:raise ValueError("Faldon supera largo comercial; requiere diseno de traslapo")
            for b in bins:
                if b["used"]+length+.003<=stock+1e-9:
                    b["used"]+=length+.003;b["pieces"].append(a["id"]);break
            else:bins.append(dict(used=length,pieces=[a["id"]]))
        roofs.append(dict(id=name,width=w,depth=d,x=x,y=y,area_plan=w*d,area_slope=w*d*k,faces=faces,sheets=sheets,bars=bars,stock_bins=bins,bar_m=sum(a["length"] for a in bars),wood=wood,wood_m=sum(a["length"] for a in wood),wood_contact=wc,wood_spacing=ws,metal_simulated=metal))
    return roofs
def svg(roofs,out,spec):
    # Draw each roof independently so dimensions, direction and legend remain legible.
    W=1000;H=100+len(roofs)*380
    a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/><g font-family="Arial" fill="#17252b"><text x="30" y="32" font-size="23">EcoBlend | Despiece preliminar de cubiertas</text><text x="30" y="59" font-size="14">Terracota: tejas / Marron: madera existente / Azul: metal opcional / Negro: limatesas. No constructivo.</text>']
    for i,r in enumerate(roofs):
        X=45;Y=100+i*380;k=min(540/r["width"],290/r["depth"])
        def xy(v):return f'{X+(v[0]-r["x"])*k:.2f},{Y+(r["depth"]-(v[1]-r["y"]))*k:.2f}'
        for f in r["sheets"]:a.append('<polygon points="'+" ".join(map(xy,f["vertices"]))+'" fill="#f3d5c4" stroke="#b6512c" stroke-width="1"/>')
        for f in r["faces"]:a.append('<polygon points="'+" ".join(map(xy,f["vertices"]))+'" fill="none" stroke="#17252b" stroke-width="2"/>')
        for b in r["wood"]:a.append('<polygon points="'+" ".join(map(xy,b["ribbon"]))+'" fill="#79502e" stroke="#79502e" stroke-width="0.5"/>')
        for b in r["bars"]:a.append('<polyline points="'+" ".join(map(xy,b["vertices"]))+'" fill="none" stroke="#1463a3" stroke-width="2"/>')
        for j,t in enumerate([r["id"],f'{r["width"]:.2f} x {r["depth"]:.2f} m',f'Area inclinada: {r["area_slope"]:.2f} m2',f'Piezas cortadas: {len(r["sheets"])}',f'Tejas comerciales: {len(r["stock_bins"])}',f'Madera: {len(r["wood"])} piezas estimadas',f'Madera: {r["wood_m"]:.2f} m lineales',f'Contacto: {r["wood_contact"]*100:.0f} cm | ejes: {r["wood_spacing"]:.2f} m',f'Metal opcional: {r["bar_m"]:.2f} m']):
            a.append(f'<text x="635" y="{Y+25+j*26}" font-size="17">{html.escape(t)}</text>')
    a.append('</g></svg>');out.write_text("".join(a),encoding="utf-8")
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--spec",type=pathlib.Path);ap.add_argument("--engine",choices=["both","freecad","blender"],default="both");ap.add_argument("--selftest",action="store_true");ap.add_argument("--preview",action="store_true");a=ap.parse_args()
    if a.selftest:
        s={"pitch":.35,"useful_width":.96,"spacing":.8,"stock":11.8,"roofs":[{"id":"T9","width":8,"depth":6,"x":0,"y":0}]}
        r=build(s)[0];assert abs(r["area_slope"]-48*math.sqrt(1+.35**2))<1e-8
        assert all(b["used"]<=11.8+1e-8 for b in r["stock_bins"])
        assert sum(len(b["pieces"]) for b in r["stock_bins"])==len(r["sheets"])
        assert len(r["wood"])>0 and not r["bars"]
        assert build(dict(s,simulate_metal=True))[0]["bar_m"]>0
        assert all(q["contact_width"]==.05 for q in r["wood"])
        print("ROOF SELFTEST OK");return
    spec=json.loads(a.spec.read_text(encoding="utf-8-sig"));roofs=build(spec)
    ROOT.mkdir(exist_ok=True);out=pathlib.Path(tempfile.mkdtemp(prefix="job-",dir=ROOT))
    (out/"roof_data.json").write_text(json.dumps(roofs,indent=2),encoding="utf-8")
    svg(roofs,out/"plano_cubiertas.svg",spec)
    with (out/"despiece.csv").open("w",newline="",encoding="utf-8-sig") as f:
        wr=csv.writer(f,delimiter=";");wr.writerow(["cubierta","tipo","id","largo_m","ancho_util_m","teja_comercial"])
        for r in roofs:
            ids={v:i+1 for i,b in enumerate(r["stock_bins"]) for v in b["pieces"]}
            for q in r["sheets"]:wr.writerow([r["id"],"teja",q["id"],round(q["length"],4),round(q["width"],4),ids[q["id"]]])
            for q in r["wood"]:wr.writerow([r["id"],"madera_existente_estimada",q["id"],round(q["length"],4),q["contact_width"],""])
            for q in r["bars"]:wr.writerow([r["id"],"correa",q["id"],round(q["length"],4),"",""])
    summary=[dict(id=r["id"],area=round(r["area_slope"],2),pieces=len(r["sheets"]),stock=len(r["stock_bins"]),bars=len(r["bars"]),bar_m=round(r["bar_m"],2),wood_count=len(r["wood"]),wood_m=round(r["wood_m"],2)) for r in roofs]
    (out/"resumen.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    results={}
    if not a.preview:
        for engine in (["freecad","blender"] if a.engine=="both" else [a.engine]):
            exe=locate(engine)
            if not exe:results[engine]=False;continue
            if engine=="freecad":
                script="""import FreeCAD as App, Part, pathlib, json
out=pathlib.Path(__file__).parent
data=json.loads((out/'roof_data.json').read_text())
doc=App.newDocument('RoofEngineering')
objects=[]
for r in data:
    group=doc.addObject('App::DocumentObjectGroup',r['id'])
    for key in ('sheets','wood','bars'):
        for q in r[key]:
            vs=[App.Vector(*[1000*c for c in v]) for v in q['vertices']]
            if key=='sheets':
                shape=Part.Face(Part.makePolygon(vs+[vs[0]])).extrude(App.Vector(0,0,2.5))
            elif key=='wood':
                rv=[App.Vector(*[1000*c for c in v]) for v in q['ribbon']]
                shape=Part.Face(Part.makePolygon(rv+[rv[0]]))
            else:
                shape=Part.makeLine(vs[0],vs[1])
            assert shape.isValid() and not shape.isNull()
            obj=doc.addObject('Part::Feature',q['id']);obj.Shape=shape;group.addObject(obj)
            obj.addProperty('App::PropertyLength','CutLength','EcoBlend');obj.CutLength=q['length']*1000
            if key=='wood':
                obj.addProperty('App::PropertyLength','ContactWidth','EcoBlend');obj.ContactWidth=q['contact_width']*1000
            if App.GuiUp:
                obj.ViewObject.ShapeColor=(.48,.28,.12) if key=='wood' else (.65,.23,.12) if key=='sheets' else (.12,.35,.75)
            objects.append(obj)
table=doc.addObject('Spreadsheet::Sheet','Quantities')
table.Label='Cuantificacion preliminar'
for i,h in enumerate(['Cubierta','Area inclinada m2','Piezas','Tejas comerciales','Segmentos metal opcional','Metal m','Madera piezas','Madera m']):
    table.set(chr(65+i)+'1',h)
for row,r in enumerate(data,2):
    for i,v in enumerate([r['id'],round(r['area_slope'],3),len(r['sheets']),len(r['stock_bins']),len(r['bars']),round(r['bar_m'],3),len(r['wood']),round(r['wood_m'],3)]):
        table.set(chr(65+i)+str(row),str(v))
doc.recompute();doc.saveAs(str(out/'demo.FCStd'));Part.export(objects,str(out/'demo.step'))
"""
                cmd=[exe];expected=["demo.FCStd","demo.step"]
            else:
                script="""import bpy, pathlib,json
out=pathlib.Path(__file__).parent
data=json.loads((out/'roof_data.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
from mathutils import Vector
def mat(n,c):
    m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);return m
tile=mat('UPVC terracota',(.55,.15,.07));metal=mat('Correas azul',(.06,.25,.65));wood=mat('Madera existente',(.35,.17,.07))
for r in data:
    for q in r['sheets']:
        mesh=bpy.data.meshes.new(q['id']);mesh.from_pydata(q['vertices'],[],[list(range(len(q['vertices'])))]);mesh.update()
        ob=bpy.data.objects.new(q['id'],mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(tile)
    for q in r['wood']:
        verts=[(v[0],v[1],v[2]-.004) for v in q['ribbon']]
        mesh=bpy.data.meshes.new(q['id']);mesh.from_pydata(verts,[],[[0,1,2,3]]);mesh.update()
        ob=bpy.data.objects.new(q['id'],mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(wood)
    for q in r['bars']:
        a,b=map(Vector,q['vertices']);a.z-=.035;b.z-=.035
        bpy.ops.mesh.primitive_cube_add(size=1,location=(a+b)/2)
        ob=bpy.context.object;ob.name=q['id'];ob.dimensions=(.04,.04,(b-a).length);ob.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();ob.data.materials.append(metal)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'demo.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'demo.glb'),export_format='GLB')
"""
                cmd=[exe,"--background","--threads",os.environ.get("ECOBLEND_THREADS","2"),"--factory-startup","--disable-autoexec","--python-exit-code","1","--python"];expected=["demo.blend","demo.glb"]
            path=out/(engine+"_roof.py");path.write_text(script,encoding="utf-8")
            with (out/(engine+".log")).open("w",encoding="utf-8") as log:
                proc=subprocess.run(cmd+[str(path)],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=240)
            results[engine]=proc.returncode==0 and all((out/f).is_file() and (out/f).stat().st_size>0 for f in expected)
    ok=all(results.values());print(json.dumps(dict(ok=ok,folder=str(out),engines=results,summary=summary)))
    if not ok:sys.exit(1)
if __name__=="__main__":main()
