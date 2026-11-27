"""EcoBlend Studio v0.9.22: local panel and public, bounded job inbox.
Remote jobs always require explicit local approval. No remote code execution.
"""
import os, html, json, pathlib, re, secrets, subprocess, sys, threading, time, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
ROOT=pathlib.Path(__file__).resolve().parent
TOKEN=secrets.token_urlsafe(32)
LOCK=threading.RLock()
STATE={"status":"Listo","output":"","pending":None,"until":0,"inbox":"Desconectado"}
HISTORY=pathlib.Path(os.environ.get("ECOBLEND_LOGS",str(ROOT.parent/"logs")))/"direct-history.jsonl"
HISTORY.parent.mkdir(exist_ok=True)
URL="https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/feature/direct-engine/direct/job.json"
def seen(jid):
    if not HISTORY.exists(): return False
    return any(json.loads(line).get("id")==jid for line in HISTORY.read_text(encoding="utf-8").splitlines() if line.strip())
def record(data):
    with HISTORY.open("a",encoding="utf-8") as f: f.write(json.dumps(data)+"\n")
from architecture_plus_v092 import build, DEMO
from roof_engine_v099 import build as build_roofs
from roof_polygon_frame_v0921 import build as build_facets
POLICY=HISTORY.parent/"direct-session.json"
def session_enabled():
    try:return json.loads(POLICY.read_text()).get("receive") is True
    except (OSError,ValueError):return False
def set_receive(value):
    tmp=POLICY.with_suffix(".tmp");tmp.write_text(json.dumps({"receive":value}),encoding="utf-8");os.replace(tmp,POLICY)
def validate(j):
    if isinstance(j,dict) and j.get("action")=="polygon_frame":
        if set(j)!={"id","action","engine","spec"} or not isinstance(j["id"],str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",j["id"]) or j["engine"]!="both":raise ValueError("Invalid frame job")
        spec=j["spec"]
        if not isinstance(spec,dict) or set(spec)!={"facets"} or len(json.dumps(spec,allow_nan=False))>16000 or not isinstance(spec["facets"],list) or not 1<=len(spec["facets"])<=40:raise ValueError("Invalid facets")
        for f in spec["facets"]:
            if not isinstance(f,dict) or set(f)-{"id","polygon","gradient","z0","spacing"} or not {"id","polygon","gradient","z0"}<=set(f):raise ValueError("Invalid facet fields")
            if not isinstance(f["polygon"],list) or not 3<=len(f["polygon"])<=80 or any(not isinstance(v,list) or len(v)!=2 or any(type(c) not in (int,float) or abs(c)>100 for c in v) for v in f["polygon"]):raise ValueError("Invalid coordinates")
            if not isinstance(f["gradient"],list) or len(f["gradient"])!=2 or any(type(c) not in (int,float) or abs(c)>1 for c in f["gradient"]) or type(f["z0"]) not in (int,float) or abs(f["z0"])>100:raise ValueError("Invalid elevation")
        if len(build_facets(spec))>1200:raise ValueError("Too many members")
        return j
    if isinstance(j,dict) and j.get("action")=="roof":
        if set(j)!={"id","action","engine","spec"} or not isinstance(j["id"],str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",j["id"]) or j["engine"] not in ("both","freecad","blender"):raise ValueError("Encargo de cubierta invalido")
        if not isinstance(j["spec"],dict) or len(json.dumps(j["spec"],allow_nan=False))>16000:raise ValueError("Especificacion invalida")
        data=build_roofs(j["spec"])
        if sum(len(r["sheets"])+len(r["wood"])+len(r["bars"]) for r in data)>1200:raise ValueError("Limite de objetos")
        return j

    if isinstance(j,dict) and j.get("action")=="architecture":
        if set(j)!={"id","action","engine","spec"} or not isinstance(j["id"],str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",j["id"]) or j["engine"] not in ("both","blender","freecad"): raise ValueError("Encargo arquitectonico invalido")
        spec=j["spec"]
        if not isinstance(spec,dict) or len(json.dumps(spec,allow_nan=False).encode())>16000: raise ValueError("Especificacion invalida")
        for key,limit in (("partitions",40),("rooms",40),("openings",30)):
            items=spec.get(key,[])
            if not isinstance(items,list) or len(items)>limit: raise ValueError("Limite de elementos")
            for item in items:
                if not isinstance(item,dict): raise ValueError("Elemento invalido")
                if key=="partitions" and (not isinstance(item.get("doors",[]),list) or len(item.get("doors",[]))>12): raise ValueError("Limite de puertas")
        pieces,surfaces=build(spec)
        if len(pieces)>600: raise ValueError("Modelo demasiado complejo para perfil lite")
        return j

    if not isinstance(j,dict) or set(j)!={"id","engine","action","size"}: raise ValueError("Campos invalidos")
    if not isinstance(j["id"],str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",j["id"]): raise ValueError("ID invalido")
    if j["action"]!="demo" or j["engine"] not in ("blender","freecad"): raise ValueError("Operacion no autorizada")
    if type(j["size"]) not in (int,float) or not .01<=j["size"]<=10000: raise ValueError("Tamano invalido")
    return j
def fetch():
    req=urllib.request.Request(URL+"?t="+str(int(time.time())),headers={"Cache-Control":"no-cache","User-Agent":"EcoBlendDirect"})
    with urllib.request.urlopen(req,timeout=15) as r: raw=r.read(32769)
    if len(raw)>32768: raise ValueError("Encargo demasiado grande")
    j=validate(json.loads(raw))
    with LOCK:
        if STATE["inbox"]=="Encargo local validado" and STATE["pending"]: return
        if not seen(j["id"]): STATE["pending"]=j; STATE["inbox"]="Encargo disponible"
        else: STATE["pending"]=None; STATE["inbox"]="Sin encargos nuevos"
def poll():
    while True:
        with LOCK: active=session_enabled() or time.monotonic()<STATE["until"]
        if active:
            try: fetch()
            except Exception as e:
                with LOCK: STATE["inbox"]="Error de consulta: "+str(e)
        time.sleep(10)
def run(args,jid=None):
    try:
        p=subprocess.run([sys.executable,str(ROOT/(args[0] if args[0] in ("architecture_plus_v092.py","roof_engine_v099.py","roof_colonial_v0920.py","roof_polygon_frame_v0921.py") else "agent.py")),* (args[1:] if args[0] in ("architecture_plus_v092.py","roof_engine_v099.py","roof_colonial_v0920.py","roof_polygon_frame_v0921.py") else args)],cwd=ROOT,capture_output=True,text=True,timeout=1100)
        status="Completado" if p.returncode==0 else "Error"
        output=(p.stdout+p.stderr)[-8000:]
    except Exception as e: status="Error"; output=str(e)
    with LOCK:
        STATE.update(status=status,output=output)
        if jid: record({"id":jid,"state":status,"output":output})
def job_digest(j):
    import hashlib
    return hashlib.sha256(json.dumps(j,sort_keys=True,allow_nan=False).encode()).hexdigest()
def job_args(j):
    if j["action"]=="demo": return ["demo","--engine",j["engine"],"--size",str(j["size"])]
    import tempfile
    folder=pathlib.Path(os.environ["ECOBLEND_LOGS"])/"approved-specs"
    folder.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",suffix=".json",dir=folder,delete=False) as f:
        json.dump(j["spec"],f,ensure_ascii=False,allow_nan=False)
        path=f.name
    if j["action"]=="polygon_frame":return ["roof_polygon_frame_v0921.py","--spec",path]
    return ["roof_engine_v099.py" if j["action"]=="roof" else "architecture_plus_v092.py","--spec",path,"--engine",j["engine"]]
def start(args,jid=None):
    with LOCK:
        if STATE["status"]=="Ejecutando": raise ValueError("Motor ocupado")
        if jid:
            if seen(jid): raise ValueError("Encargo ya registrado")
            record({"id":jid,"state":"Aceptado"})
            STATE["pending"]=None
        STATE.update(status="Ejecutando",output="")
        threading.Thread(target=run,args=(args,jid),daemon=True).start()
def frame_projects():
    root=pathlib.Path(os.environ["ECOBLEND_PROJECTS"]).resolve()
    return [p for p in sorted(root.glob("job-*")) if p.is_dir() and p.resolve().parent==root and all((p/n).is_file() for n in ("frame.json","roof_data.json","demo.FCStd")) and not (p/"profile_report.json").exists()]
def frame_project(name):
    if not re.fullmatch(r"job-[A-Za-z0-9_-]+",name):raise ValueError("ID invalido")
    for p in frame_projects():
        if p.name==name:return p
    raise ValueError("Esqueleto no disponible")
class Handler(BaseHTTPRequestHandler):
    def host(self): return f"127.0.0.1:{self.server.server_port}"
    def reply(self,body,status=200):
        b=body.encode("utf-8")
        self.send_response(status); self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Cache-Control","no-store"); self.send_header("X-Frame-Options","DENY")
        self.send_header("Content-Security-Policy","default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
        self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def redirect(self):
        self.send_response(303); self.send_header("Location","/"); self.end_headers()
    def do_GET(self):
        if self.headers.get("Host")!=self.host(): return self.reply("Host invalido",403)
        if self.path=="/health":
            with LOCK: status=STATE["status"];inbox=STATE["inbox"]
            return self.reply(html.escape(json.dumps({"version":"0.9.22","receiver":session_enabled(),"status":status,"inbox":inbox,"actions":["demo","architecture","roof","polygon_frame"]})))
        if self.path!="/": return self.reply("No encontrado",404)
        with LOCK: s=dict(STATE)
        e=html.escape
        active=session_enabled() or time.monotonic()<s["until"]
        remaining=max(0,int(s["until"]-time.monotonic()))
        hidden=f'<input type="hidden" name="token" value="{TOKEN}">'
        pending=""
        if s["pending"]:
            j=s["pending"]
            pending=f'<pre>{e(json.dumps(j))}</pre><form method="post">{hidden}<input type="hidden" name="id" value="{e(j["id"])}"><input type="hidden" name="digest" value="{job_digest(j)}"><button name="action" value="approve">Autorizar y ejecutar</button><button name="action" value="reject">Descartar</button></form>'
        options="".join('<option value="'+e(p.name)+'">'+e(p.name)+'</option>' for p in frame_projects())
        refresh='<meta http-equiv="refresh" content="5">' if s["status"]=="Ejecutando" or (active and not s["pending"]) else ""
        self.reply(f"""<!doctype html><html lang="es"><head><meta charset="utf-8">{refresh}<title>EcoBlend Studio v0.9.22</title><style>body{{font:16px system-ui;background:#101923;color:#edf5f8;max-width:850px;margin:35px auto;padding:20px}}section{{background:#1e2b38;padding:24px;border-radius:14px;margin:16px 0}}button{{background:#36b8a0;border:0;padding:12px 20px;border-radius:8px;margin:8px;cursor:pointer}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;color:#b5e9de}}a{{color:#8cd9ec}}</style></head><body><h1>EcoBlend Studio v0.9.22</h1><p>Blender · FreeCAD · Sin MCP</p><section><h2>Visualizacion de proyectos</h2><p><a href="http://127.0.0.1:8788/" target="_blank" rel="noopener">Abrir visor 3D de EcoBlend</a></p><p>El lanzador de escritorio inicia ambos servicios.</p></section><section><h2>Buzon de ChatGPT</h2><p>{'Recepcion persistente' if session_enabled() else 'Conectado: '+str(remaining)+' segundos' if active else 'Desconectado'} · {e(s['inbox'])}</p><form method="post">{hidden}<button name="action" value="persist">Mantener receptor conectado</button><button name="action" value="connect">Recibir encargos durante 20 minutos</button><button name="action" value="disconnect">Desconectar</button><button name="action" value="fetch">Consultar ahora</button></form>{pending}<p>La consulta es automatica; cada ejecucion requiere autorizacion local. No incluir datos privados en GitHub.</p></section><section><h2>Architecture / Engineering · Encargo privado</h2><p>Pega un JSON de ChatGPT. Se valida antes de autorizar. No se envia a GitHub.</p><form method="post">{hidden}<textarea name="job" rows="12" style="width:100%" maxlength="20000">{e(json.dumps(dict(id="architecture-local-001",action="architecture",engine="both",spec=DEMO),ensure_ascii=False,indent=2))}</textarea><button name="action" value="preview">Validar encargo local</button></form><p><a href="http://127.0.0.1:8789/">Reality Painter</a> · <a href="http://127.0.0.1:8788/">Explorer</a></p></section><section><h2>Engineering · Cubiertas</h2><p>Ejemplo generico de cubierta a cuatro aguas. Madera existente, metal desactivado. Edite las medidas antes de validar.</p><form method="post">{hidden}<textarea name="job" rows="12" style="width:100%" maxlength="20000">{e(json.dumps(dict(id="roof-"+secrets.token_hex(6),action="roof",engine="both",spec={"pitch":.35,"useful_width":.96,"spacing":.8,"stock":11.8,"wood_spacing":.8,"wood_contact":.05,"simulate_metal":False,"roofs":[{"id":"T9","width":8,"depth":6,"x":0,"y":0}]}),indent=2))}</textarea><button name="action" value="preview">Validar cubiertas</button></form></section><section><h2>Editar proyecto · Cubiertas</h2><p>Operacion especializada sobre un proyecto CAD. Se conserva el original y se crea una revision nueva.</p><form method="post">{hidden}<select name="project">{options}</select><button name="action" value="colonial">Generar montaje y despiece</button></form></section><section><h2>Motor local</h2><form method="post">{hidden}<select name="engine"><option>blender</option><option>freecad</option></select> <input name="size" type="number" min=".01" max="10000" step="any" value="2"><button name="action" value="demo">Crear modelo</button><button name="action" value="status">Diagnostico</button></form><p>Blender: metros; FreeCAD: milimetros.</p></section><section><h2>{e(s['status'])}</h2><pre>{e(s['output'])}</pre><a href="/">Actualizar estado</a></section><p>Solo localhost. El historial permanece en tu PC. Cerrar PowerShell detiene el panel.</p></body></html>""")
    def do_POST(self):
        if self.headers.get("Host")!=self.host() or self.headers.get("Origin")!="http://"+self.host(): return self.reply("Origen invalido",403)
        try:
            n=int(self.headers.get("Content-Length","0"))
            if not 0<n<=120000: raise ValueError("Solicitud invalida")
            d=parse_qs(self.rfile.read(n).decode()); get=lambda k:d.get(k,[""])[0]
            if not secrets.compare_digest(get("token"),TOKEN): return self.reply("Token invalido",403)
            a=get("action")
            if a=="persist":
                set_receive(True)
                fetch()
            elif a=="connect":
                with LOCK: STATE["until"]=time.monotonic()+1200
            elif a=="disconnect":
                set_receive(False)
                with LOCK: STATE.update(until=0,pending=None,inbox="Desconectado")
            elif a=="fetch": fetch()
            elif a=="preview":
                j=validate(json.loads(get("job")))
                with LOCK:
                    if seen(j["id"]): raise ValueError("ID ya utilizado")
                    STATE.update(pending=j,until=0,inbox="Encargo local validado")
            elif a in ("approve","reject"):
                with LOCK:
                    j=STATE["pending"]
                    if not j or get("id")!=j["id"] or get("digest")!=job_digest(j): raise ValueError("Encargo cambiado; vuelve a consultar")
                    if a=="reject": record({"id":j["id"],"state":"Descartado"}); STATE["pending"]=None
                    else: start(job_args(j),j["id"])
            elif a=="colonial": start(["roof_colonial_v0920.py","--project",str(frame_project(get("project")))])
            elif a=="status": start(["status"])
            elif a=="demo":
                j=validate({"id":"local","engine":get("engine"),"action":"demo","size":float(get("size"))})
                start(["demo","--engine",j["engine"],"--size",str(j["size"])])
            else: raise ValueError("Accion desconocida")
            self.redirect()
        except Exception as e: self.reply(html.escape(str(e))+' <a href="/">Volver</a>',400)
if __name__=="__main__":
    if "--selftest" in sys.argv:
        good={"id":"test","action":"architecture","engine":"both","spec":DEMO}
        assert validate(good)==good
        assert validate({"id":"old","action":"demo","engine":"blender","size":2})["size"]==2
        for bad in (dict(good,engine="shell"),dict(good,spec=dict(DEMO,wall=-1)),dict(good,command="cmd"),dict(good,id="../test")):
            try: validate(bad)
            except (ValueError,KeyError,TypeError): pass
            else: raise AssertionError("Encargo invalido aceptado")
        assert job_digest(good)!=job_digest(dict(good,id="other"))
        roof={"id":"roof-test","action":"roof","engine":"both","spec":{"pitch":.35,"useful_width":.96,"spacing":.8,"stock":11.8,"roofs":[{"id":"T9","width":8,"depth":6,"x":0,"y":0}]}}
        assert validate(roof)==roof
        try:validate(dict(roof,spec=dict(roof["spec"],wood_spacing=0)))
        except ValueError:pass
        else:raise AssertionError("Invalid roof accepted")
        facet={"id":"facet-test","engine":"both","action":"polygon_frame","spec":{"facets":[{"id":"F1","polygon":[[0,0],[3,0],[3,2],[0,2]],"gradient":[.35,0],"z0":0}]}}
        assert validate(facet)==facet
        try:validate(dict(facet,spec={"facets":[dict(facet["spec"]["facets"][0],polygon=[[0,0],[99999,0],[0,2]])]}))
        except ValueError:pass
        else:raise AssertionError("Unbounded geometry")
        print("DIRECT BRIDGE SELFTEST OK")
        sys.exit(0)
    server=ThreadingHTTPServer(("127.0.0.1",8787),Handler)
    threading.Thread(target=poll,daemon=True).start()
    print("EcoBlend Studio v0.9.22 http://127.0.0.1:8787/",flush=True)
    webbrowser.open("http://127.0.0.1:8787/")
    server.serve_forever()
