"""Local timber assembly: preserve source projects; transform only copies.
Input is a local JSON specification, never arbitrary executable code."""
import argparse,csv,json,math,os,pathlib,re,struct,subprocess,tempfile
from roof_polygon_frame_v0921 import build
from roof_frame_v0913 import CAD,BLENDER
from agent_v04 import locate

def assemble(spec,root):
    if set(spec)-{"facets","sources"}:raise ValueError("Unknown fields")
    result=build({"facets":spec["facets"]}) if spec.get("facets") else []
    for src in spec.get("sources",[]):
        if set(src)!={"project","rotation_deg","translation_m"}:raise ValueError("Source fields")
        name=src["project"]
        if not re.fullmatch(r"job-[A-Za-z0-9_-]+",name):raise ValueError("Project id")
        folder=(root/name).resolve()
        if folder.parent!=root.resolve():raise ValueError("Project path")
        t=src["translation_m"];angle=src["rotation_deg"]
        if len(t)!=3 or not all(math.isfinite(v) and abs(v)<=100 for v in t) or not math.isfinite(angle):raise ValueError("Transform")
        a=math.radians(angle);c,s=math.cos(a),math.sin(a)
        def transform(p):
            x,y,z=p;return [c*x-s*y+t[0],s*x+c*y+t[1],z+t[2]]
        for q in json.loads((folder/"frame.json").read_text(encoding="utf-8")):
            q=dict(q);q["a"]=transform(q["a"]);q["b"]=transform(q["b"]);result.append(q)
    ids=set()
    for q in result:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,100}",q["id"]) or q["id"] in ids:raise ValueError("Duplicate/invalid member "+q["id"])
        ids.add(q["id"])
        if q["width"] not in (50,100) or q["depth"]!=100:raise ValueError("Timber section")
        q["length"]=math.dist(q["a"],q["b"])*1000
        if not math.isfinite(q["length"]) or not 1<=q["length"]<=100000:raise ValueError("Member length")
    if not 1<=len(result)<=3000:raise ValueError("Member count")
    return result

def summary(q):
    return {k:{"count":sum((x["kind"]=="secundaria")== (k=="secondary") for x in q),"meters":round(sum(x["length"] for x in q if (x["kind"]=="secundaria")== (k=="secondary"))/1000,3)} for k in ("primary","secondary")}

def execute(spec,root):
    q=assemble(spec,root)
    out=pathlib.Path(tempfile.mkdtemp(prefix="job-",dir=root))
    (out/"studio_project.json").write_text(json.dumps({"name":"Ensamblaje CAD en proceso","state":"draft"}),encoding="utf-8")
    (out/"frame.json").write_text(json.dumps(q),encoding="utf-8")
    (out/"assembly_spec.json").write_text(json.dumps(spec),encoding="utf-8")
    report={"ok":False,"folder":str(out),"members":len(q),"summary":summary(q),"stages":{},"limitations":"Nominal axes; joints, contacts and structural capacity not certified"}
    def save():
        (out/"assembly_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    save()
    try:
        for engine,code,files in [("freecad",CAD,["demo.FCStd","demo.step","cad_mesh.json"]),("blender",BLENDER,["demo.blend","demo.glb"])]:
            exe=locate(engine)
            if not exe:raise RuntimeError(engine+" unavailable")
            macro=out/(engine+"_assembly.py")
            code="import traceback\ntry:\n"+ "".join("    "+l+"\n" for l in code.splitlines())+"except BaseException:\n    traceback.print_exc()\n    raise\n"
            macro.write_text(code,encoding="utf-8")
            cmd=[exe] if engine=="freecad" else [exe,"--background","--threads","2","--factory-startup","--disable-autoexec","--python-exit-code","1","--python"]
            with (out/(engine+".log")).open("w",encoding="utf-8") as log:
                p=subprocess.run(cmd+[str(macro)],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=480)
            if p.returncode or any(not (out/f).is_file() or not (out/f).stat().st_size for f in files):raise RuntimeError(engine+" failed; consult "+str(out))
            if engine=="freecad":
                mesh=json.loads((out/"cad_mesh.json").read_text())
                if sorted(x["id"] for x in mesh)!=sorted(x["id"] for x in q):raise RuntimeError("CAD inventory mismatch")
                if any(x["volume_mm3"]<=0 for x in mesh):raise RuntimeError("Invalid CAD volume")
            else:
                with (out/"demo.glb").open("rb") as f:
                    magic,ver,size=struct.unpack("<4sII",f.read(12))
                    if magic!=b"glTF" or ver!=2 or size!=(out/"demo.glb").stat().st_size:raise RuntimeError("Invalid GLB")
            report["stages"][engine]="verified exports";save()
        with (out/"madera.csv").open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.writer(f,delimiter=";");w.writerow(["ID","Tipo","Ancho mm","Profundidad mm","Longitud eje mm"])
            for x in q:w.writerow([x["id"],x["kind"],x["width"],x["depth"],round(x["length"],2)])
        report["ok"]=True;save()
        (out/"studio_project.json").write_text(json.dumps({"name":"Estructura maestra | ensamblaje CAD","state":"active"}),encoding="utf-8")
        return report
    except Exception as e:
        report["error"]=str(e);save();raise

def main():
    p=argparse.ArgumentParser();p.add_argument("--spec",type=pathlib.Path);p.add_argument("--selftest",action="store_true");a=p.parse_args()
    if a.selftest:
        with tempfile.TemporaryDirectory() as t:
            root=pathlib.Path(t);folder=root/"job-test";folder.mkdir()
            (folder/"frame.json").write_text(json.dumps([dict(id="OLD_W1",kind="secundaria",a=[0,0,0],b=[2,0,0],width=50,depth=100,length=2000)]))
            q=assemble({"sources":[dict(project="job-test",rotation_deg=90,translation_m=[1,2,3])],"facets":[dict(id="NEW",polygon=[[0,0],[3,0],[3,2],[0,2]],gradient=[.35,0],z0=0)]},root)
            old=next(x for x in q if x["id"]=="OLD_W1")
            assert math.dist(old["b"],[1,4,3])<1e-8 and old["length"]==2000
            assert summary(q)["primary"]["count"]>0
            compile(CAD,"cad","exec");compile(BLENDER,"blender","exec")
        print("CAD ASSEMBLY SELFTEST OK");return
    if not a.spec:p.error("spec required")
    print(json.dumps(execute(json.loads(a.spec.read_text(encoding="utf-8-sig")),pathlib.Path(os.environ["ECOBLEND_PROJECTS"]))))
if __name__=="__main__":main()
