"""Architecture v0.8: local visual briefs and conceptual facade-to-shell workflow."""
import argparse,json,pathlib,tempfile,re,subprocess,sys,html
from architecture_v05 import build,ROOT
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
def brief(spec,style):
    pieces,surfaces=build(spec)
    shared="Maintain identical architecture and palette across views. "+style
    result=[]
    for s in surfaces:
        k=s["id"]
        if k=="C01":continue
        w=spec["width"];d=spec["depth"];h=spec["height"];t=spec["wall"]
        size=[w,d] if k=="P01" else [w if k in ("F01","F02") else d-2*t,h]
        openings=[o for o in spec["openings"] if o["side"]==k]
        # Convert model offsets to the left-to-right image convention of Reality Engine.
        if k in ("F02","F03"):
            openings=[dict(o,offset=size[0]-o["offset"]-o["width"]) for o in openings]
        result.append({"id":k,"file":k+".png","dimensions_m":size,"openings_image_left_m":openings,"prompt":shared+" | "+k+" "+s["label"]+" | exact aspect ratio "+str(size[0]/size[1])+" | openings from image left, bottom from floor: "+json.dumps(openings)+" | "+("orthographic top-down seamless floor material" if k=="P01" else "flat orthographic elevation, facade fills frame, no perspective, no sky, no ground, no people or vehicles, diffuse neutral light, preserve all opening positions")+" | no labels or text"})
    return result
def proposal(data):
    if not isinstance(data,dict) or set(data)!={"spec","dimension_status","notes"}:raise ValueError("Campos: spec, dimension_status, notes")
    spec=data["spec"];build(spec)
    status=data["dimension_status"]
    if not isinstance(status,dict) or set(status)!={"width","depth","height","wall","openings"} or any(x not in ("verified","estimated","proposed") for x in status.values()):raise ValueError("Declare estado de cada dimension")
    if not isinstance(data["notes"],str) or len(data["notes"])>4000:raise ValueError("Notas invalidas")
    return spec
def plan_svg(spec):
    pieces,_=build(spec); w,d=spec["width"],spec["depth"];k=480/max(w,d);x0,y0=70,60
    rect=[]
    for p in pieces:
        if p["id"]=="P01" or p["xyz"][2]>.01:continue
        x,y,z=p["xyz"];a,b,c=p["size"]
        rect.append(f'<rect x="{x0+x*k}" y="{y0+(d-y-b)*k}" width="{a*k}" height="{b*k}" fill="#314e53"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="620"><rect width="640" height="620" fill="white"/><g font-family="Arial" font-size="14"><text x="20" y="25">Anteproyecto conceptual - planta exterior - no constructivo</text><text x="70" y="45">{w} x {d} m</text>{"".join(rect)}<text x="{x0}" y="{y0+d*k+22}">F01 Frente - sin distribucion interior</text></g></svg>'
def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="action",required=True)
    b=sub.add_parser("brief");b.add_argument("--project",required=True);b.add_argument("--style",required=True)
    a=sub.add_parser("proposal");a.add_argument("--input",type=pathlib.Path,required=True);a.add_argument("--build",action="store_true")
    sub.add_parser("selftest");args=p.parse_args()
    if args.action=="selftest":
        from architecture_v05 import DEMO
        r=brief(DEMO,"campestre");assert len(r)==5 and r[0]["id"]=="F01"
        assert abs(next(x for x in r if x["id"]=="F03")["openings_image_left_m"][0]["offset"]-2.2)<1e-8
        assert "<svg" in plan_svg(DEMO)
        try:proposal({"spec":DEMO,"dimension_status":{},"notes":""})
        except ValueError:pass
        else:raise AssertionError("Missing provenance accepted")
        print("SELFTEST OK: briefs, orientation, conceptual plan and provenance");return
    if args.action=="brief":
        if not re.fullmatch(r"job-[A-Za-z0-9_-]+",args.project):p.error("Proyecto invalido")
        src=(ROOT/args.project).resolve()
        if not src.is_relative_to(ROOT.resolve()):p.error("Proyecto invalido")
        spec=json.loads((src/"surface_inventory.json").read_text(encoding="utf-8"))["spec"]
        out=src/"visual_briefs";out.mkdir(exist_ok=True)
        dest=pathlib.Path(tempfile.mkdtemp(prefix="brief-",dir=out))
        write(dest/"image_briefs.json",brief(spec,args.style))
        print(dest);return
    data=json.loads(args.input.read_text(encoding="utf-8-sig"));spec=proposal(data)
    ROOT.mkdir(exist_ok=True);out=pathlib.Path(tempfile.mkdtemp(prefix="concept-",dir=ROOT))
    write(out/"proposal.json",data);write(out/"spec.json",spec)
    (out/"concept_plan.svg").write_text(plan_svg(spec),encoding="utf-8")
    print(str(out),flush=True)
    if args.build:
        r=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name("architecture_v05.py")),"--spec",str(out/"spec.json"),"--engine","both"],capture_output=True,text=True,timeout=540)
        print(r.stdout);print(r.stderr,file=sys.stderr)
        if r.returncode:raise SystemExit(r.returncode)
        result=json.loads(r.stdout.strip().splitlines()[-1]);dest=pathlib.Path(result["folder"])
        if not result["ok"] or not dest.resolve().is_relative_to(ROOT.resolve()):raise RuntimeError("Build invalid")
        write(dest/"concept_provenance.json",data)
        (dest/"concept_plan.svg").write_text(plan_svg(spec),encoding="utf-8")
if __name__=="__main__":main()
