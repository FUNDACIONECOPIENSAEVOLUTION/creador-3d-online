"""Local browser UI for Reality Painter. Private reference files stay in project folders."""
import html,json,pathlib,re,secrets,threading,subprocess,sys,webbrowser,os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import parse_qs,urlsplit
from reality_v091 import ROOT,surface_ids
def ids(p):
    return surface_ids(json.loads((p/'surface_inventory.json').read_text(encoding='utf-8'))['spec'])
TOKEN=secrets.token_urlsafe(32)
LOCK=threading.Lock()
STATE={"status":"Listo","log":""}
def project(j):
    if not re.fullmatch(r"job-[A-Za-z0-9_-]+",j):raise ValueError("Proyecto invalido")
    p=(ROOT/j).resolve()
    if not p.is_relative_to(ROOT.resolve()) or not (p/"surface_inventory.json").is_file() or not (p/"demo.blend").is_file():raise ValueError("Proyecto no compatible")
    return p
def references(p):
    d=p/"photo_references";d.mkdir(exist_ok=True)
    if not d.resolve().is_relative_to(p.resolve()):raise ValueError("Carpeta invalida")
    return d
def worker(j,m):
    try:
        r=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name("reality_painter_v091.py")),"--project",j,"--manifest",str(m)],capture_output=True,text=True,timeout=360)
        STATE.update(status="Completado" if r.returncode==0 else "Error",log=(r.stdout+r.stderr)[-12000:])
    except Exception as e:STATE.update(status="Error",log=str(e))
    finally:LOCK.release()
class Handler(BaseHTTPRequestHandler):
    def reply(self,body,status=200):
        b=body.encode();self.send_response(status);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("X-Frame-Options","DENY");self.send_header("Content-Security-Policy","default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        if self.headers.get("Host")!="127.0.0.1:8789":return self.reply("Host invalido",403)
        u=urlsplit(self.path)
        if u.path!="/":return self.reply("No encontrado",404)
        jobs=[]
        for p in ROOT.glob("job-*"):
            try:
                q=project(p.name)
                if not (q/"reality_report.json").exists() or json.loads((q/"reality_report.json").read_text(encoding="utf-8")).get("ok"):jobs.append(q)
            except ValueError:pass
        jobs.sort(key=lambda p:(p/"demo.blend").stat().st_mtime,reverse=True)
        j=parse_qs(u.query).get("project",[jobs[0].name if jobs else ""])[0]
        e=html.escape
        opts="".join(f'<option value="{p.name}" {"selected" if p.name==j else ""}>{p.name}</option>' for p in jobs)
        fields=""
        if j:
            try:
                p=project(j);d=references(p)
                files=[f.name for f in d.iterdir() if f.is_file() and f.suffix.lower() in (".png",".jpg",".jpeg") and f.resolve().is_relative_to(d.resolve())]
                labels={"F01":"Frente","F02":"Posterior","F03":"Izquierda","F04":"Derecha","P01":"Piso"}
                for side in ids(p):
                    choices="".join(f'<option value="{e(n,quote=True)}">{e(n)}</option>' for n in sorted(files))
                    fields+=f'<fieldset><legend>{side} · {labels.get(side,'Piso de ambiente' if side.endswith('-P') else 'Cara interior')}</legend><label>Imagenes alineadas (Ctrl para varias)<select name="{side}" multiple size="4">{choices}</select></label><label>Procedencia<select name="{side}_source"><option value="photo">Foto</option><option value="ai">IA</option><option value="synthetic">Sintetica</option></select></label><label>Modo<select name="{side}_mode"><option value="facade">Imagen completa</option><option value="tile">Repetible</option></select></label><label>Repeticion (m)<input name="{side}_repeat" type="number" value="1" min=".05" max="100" step=".05"></label><label>Esquinas opcionales TL TR BR BL (JSON 0-1; una imagen)<input name="{side}_corners" placeholder="[[0,0],[1,0],[1,1],[0,1]]"></label></fieldset>'
                fields=f'<p>Guarde fotos JPG/PNG en esta carpeta local y actualice:</p><pre>{e(str(d))}</pre><form method="post"><input type="hidden" name="token" value="{TOKEN}"><input type="hidden" name="project" value="{e(j)}">{fields}<button>Aplicar y generar nueva version</button></form>'
            except ValueError:fields="<p>Seleccione un proyecto valido</p>"
        self.reply(f"""<!doctype html><html lang="es"><meta charset="utf-8"><title>Reality Painter</title><style>body{{font:16px system-ui;background:#101923;color:#edf5f8;max-width:1100px;margin:30px auto;padding:20px}}fieldset{{border:1px solid #405565;margin:12px 0;padding:14px;border-radius:8px;display:flex;gap:12px;flex-wrap:wrap}}label{{display:flex;flex-direction:column;gap:5px}}select,input,button{{padding:8px}}button{{background:#36b8a0;border:0;border-radius:6px;margin:10px 0}}a{{color:#8ee}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style><h1>EcoBlend Reality Painter v0.9.1</h1><p>Fotografias locales · Proyeccion UV · Nueva version editable</p><a href="http://127.0.0.1:8788/">Visor 3D</a> · <a href="http://127.0.0.1:8787/">Control</a><form method="get"><select name="project">{opts}</select><button>Seleccionar / actualizar</button></form>{fields}<h2>{e(STATE['status'])}</h2><pre>{e(STATE['log'])}</pre><p>Recargue para consultar resultados. No se generan imagenes IA automaticamente. Las referencias multiples deben estar alineadas.</p></html>""")
    def do_POST(self):
        if self.path!="/" or self.headers.get("Host")!="127.0.0.1:8789" or self.headers.get("Origin")!="http://127.0.0.1:8789":return self.reply("Origen invalido",403)
        try:
            n=int(self.headers.get("Content-Length","0"))
            if not 0<n<=32768:raise ValueError("Solicitud invalida")
            d=parse_qs(self.rfile.read(n).decode());g=lambda k,v="":d.get(k,[v])[0]
            if not secrets.compare_digest(g("token"),TOKEN):return self.reply("Token invalido",403)
            j=g("project");p=project(j);folder=references(p);manifest={}
            for side in ids(p):
                selected=d.get(side,[])
                if not selected:continue
                if len(selected)>10:raise ValueError("Maximo diez imagenes")
                refs=[]
                for name in selected:
                    f=folder/name
                    if pathlib.Path(name).name!=name or not f.resolve().is_relative_to(folder.resolve()) or not f.is_file():raise ValueError("Referencia invalida")
                    refs.append({"image":name})
                corners=g(side+"_corners")
                if corners:
                    if len(refs)!=1:raise ValueError("Esquinas solo para una referencia")
                    refs[0]["corners"]=json.loads(corners)
                manifest[side]={"source":g(side+"_source"),"mode":g(side+"_mode"),"repeat_m":float(g(side+"_repeat","1")),"references":refs}
            if not manifest:raise ValueError("Seleccione al menos una imagen")
            if not LOCK.acquire(False):raise ValueError("Motor ocupado")
            try:
                m=folder/("manifest-"+secrets.token_hex(8)+".json");m.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
                STATE.update(status="Ejecutando",log="")
                threading.Thread(target=worker,args=(j,m),daemon=True).start()
            except Exception:LOCK.release();raise
            self.send_response(303);self.send_header("Location","/?project="+j);self.end_headers()
        except Exception as e:return self.reply(html.escape(str(e))+' <a href="/">Volver</a>',400)
if __name__=="__main__":
    server=ThreadingHTTPServer(("127.0.0.1",8789),Handler);webbrowser.open("http://127.0.0.1:8789/");server.serve_forever()
