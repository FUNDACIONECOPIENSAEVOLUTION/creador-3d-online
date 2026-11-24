"""Local Reality Painter: select prepared photographs, rectify and blend, then export.
Run on localhost only. No image upload to external services.
"""
import argparse, pathlib, json, re, tempfile, subprocess, sys, math
from PIL import Image, ImageOps, ImageChops
from reality_v08 import validate, ROOT, IDS
Image.MAX_IMAGE_PIXELS=30_000_000
def prepare(path, corners=None, size=(1024,1024)):
    with Image.open(path) as src:
        if src.width*src.height>30_000_000: raise ValueError("Imagen demasiado grande")
        im=ImageOps.exif_transpose(src).convert("RGB")
    if corners is None: return im.resize(size,Image.Resampling.LANCZOS)
    if len(corners)!=4 or any(len(p)!=2 or any(not math.isfinite(v) or not 0<=v<=1 for v in p) for p in corners): raise ValueError("Cuatro esquinas normalizadas requeridas")
    pts=[(x*im.width,y*im.height) for x,y in corners]
    # Solve projective transform output -> input, TL TR BR BL.
    W,H=size
    A=[]
    for (u,v),(x,y) in zip([(0,0),(W,0),(W,H),(0,H)],pts):
        A.extend([[u,v,1,0,0,0,-x*u,-x*v,x],[0,0,0,u,v,1,-y*u,-y*v,y]])
    for i in range(8):
        k=max(range(i,8),key=lambda j:abs(A[j][i]))
        A[i],A[k]=A[k],A[i]
        q=A[i][i]
        if abs(q)<1e-10: raise ValueError("Esquinas degeneradas")
        A[i]=[v/q for v in A[i]]
        for j in range(8):
            if j!=i:
                q=A[j][i];A[j]=[a-q*b for a,b in zip(A[j],A[i])]
    return im.transform(size,Image.Transform.PERSPECTIVE,[r[-1] for r in A],Image.Resampling.BICUBIC)
def run(project, manifest):
    if not re.fullmatch(r"job-[A-Za-z0-9_-]+",project): raise ValueError("Proyecto invalido")
    p=ROOT/project
    if not p.resolve().is_relative_to(ROOT.resolve()) or not (p/"surface_inventory.json").is_file(): raise ValueError("Proyecto sin inventario")
    inv=json.loads((p/"surface_inventory.json").read_text(encoding="utf-8"));spec=inv["spec"]
    data=json.loads(manifest.read_text(encoding="utf-8-sig"))
    if not isinstance(data,dict) or not data or set(data)-set(IDS): raise ValueError("Superficies invalidas")
    with tempfile.TemporaryDirectory(prefix="ecoblend-painter-") as tmp:
        out=pathlib.Path(tmp);mapping={}
        for side,entry in data.items():
            if entry.get("source") not in ("photo","ai","synthetic"): raise ValueError("Indique procedencia")
            refs=entry["references"]
            if not 1<=len(refs)<=10: raise ValueError("Entre 1 y 10 referencias por superficie")
            mode=entry.get("mode","facade")
            if mode not in ("facade","tile"): raise ValueError("Modo invalido")
            w=spec["width"];d=spec["depth"];h=spec["height"];t=spec["wall"]
            ratio=1 if mode=="tile" else (w/d if side=="P01" else (w if side in ("F01","F02") else d-2*t)/h)
            size=(max(64,round(1536*min(1,ratio))),max(64,round(1536*min(1,1/ratio))))
            acc=None;total=0
            for ref in refs:
                f=(manifest.parent/ref["image"]).resolve()
                if not f.is_relative_to(manifest.parent.resolve()) or f.suffix.lower() not in (".png",".jpg",".jpeg") or f.stat().st_size>32*1024*1024: raise ValueError("Referencia invalida")
                weight=ref.get("weight",1)
                if type(weight) not in (int,float) or not math.isfinite(weight) or not 0<weight<=100: raise ValueError("Peso invalido")
                im=prepare(f,ref.get("corners"),size)
                acc=im if acc is None else Image.blend(acc,im,weight/(total+weight))
                total+=weight
            name=side+".png";acc.save(out/name)
            mapping[side]={"image":name,"mode":mode,"repeat_m":entry.get("repeat_m",1),"source":entry["source"],"roughness":entry.get("roughness",.65)}
        validate(mapping,out)
        m=out/"mapping.json";m.write_text(json.dumps(mapping),encoding="utf-8")
        proc=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name("reality_v08.py")),"--project",project,"--mapping",str(m)],check=True,capture_output=True,text=True,timeout=300)
        report=json.loads(proc.stdout.strip().splitlines()[-1]); dest=pathlib.Path(report["folder"])
        if not dest.resolve().is_relative_to(ROOT.resolve()) or not report["ok"]: raise RuntimeError("Exportacion no validada")
        (dest/"painter_manifest.json").write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
        print(json.dumps(report))
def selftest():
    with tempfile.TemporaryDirectory() as t:
        p=pathlib.Path(t)/"test.png";Image.new("RGB",(200,100),(120,80,40)).save(p)
        im=prepare(p,[[0,0],[1,0],[1,1],[0,1]],(100,50))
        assert im.size==(100,50) and im.getpixel((50,25))==(120,80,40)
        try: prepare(p,[[0,0]]*4,(100,50))
        except ValueError: pass
        else: raise AssertionError("Degenerate corners accepted")
    print("SELFTEST OK: perspective and invalid corners")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--project");p.add_argument("--manifest",type=pathlib.Path);p.add_argument("--selftest",action="store_true");a=p.parse_args()
    if a.selftest:selftest()
    elif a.project and a.manifest:run(a.project,a.manifest.resolve())
    else:p.error("Use --selftest or --project and --manifest")
