"""EcoBlend Direct v0.3: local panel and public, bounded job inbox.
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
def validate(j):
    if not isinstance(j,dict) or set(j)!={"id","engine","action","size"}: raise ValueError("Campos invalidos")
    if not isinstance(j["id"],str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",j["id"]): raise ValueError("ID invalido")
    if j["action"]!="demo" or j["engine"] not in ("blender","freecad"): raise ValueError("Operacion no autorizada")
    if type(j["size"]) not in (int,float) or not .01<=j["size"]<=10000: raise ValueError("Tamano invalido")
    return j
def fetch():
    req=urllib.request.Request(URL+"?t="+str(int(time.time())),headers={"Cache-Control":"no-cache","User-Agent":"EcoBlendDirect"})
    with urllib.request.urlopen(req,timeout=15) as r: raw=r.read(8193)
    if len(raw)>8192: raise ValueError("Encargo demasiado grande")
    j=validate(json.loads(raw))
    with LOCK:
        if not seen(j["id"]): STATE["pending"]=j; STATE["inbox"]="Encargo disponible"
        else: STATE["pending"]=None; STATE["inbox"]="Sin encargos nuevos"
def poll():
    while True:
        with LOCK: active=time.monotonic()<STATE["until"]
        if active:
            try: fetch()
            except Exception as e:
                with LOCK: STATE["inbox"]="Error de consulta: "+str(e)
        time.sleep(10)
def run(args,jid=None):
    try:
        p=subprocess.run([sys.executable,str(ROOT/"agent.py"),*args],cwd=ROOT,capture_output=True,text=True,timeout=210)
        status="Completado" if p.returncode==0 else "Error"
        output=(p.stdout+p.stderr)[-8000:]
    except Exception as e: status="Error"; output=str(e)
    with LOCK:
        STATE.update(status=status,output=output)
        if jid: record({"id":jid,"state":status,"output":output})
def start(args,jid=None):
    with LOCK:
        if STATE["status"]=="Ejecutando": raise ValueError("Motor ocupado")
        if jid:
            if seen(jid): raise ValueError("Encargo ya registrado")
            record({"id":jid,"state":"Aceptado"})
            STATE["pending"]=None
        STATE.update(status="Ejecutando",output="")
        threading.Thread(target=run,args=(args,jid),daemon=True).start()
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
        if self.path!="/": return self.reply("No encontrado",404)
        with LOCK: s=dict(STATE)
        e=html.escape
        active=time.monotonic()<s["until"]
        remaining=max(0,int(s["until"]-time.monotonic()))
        hidden=f'<input type="hidden" name="token" value="{TOKEN}">'
        pending=""
        if s["pending"]:
            j=s["pending"]
            pending=f'<pre>{e(json.dumps(j))}</pre><form method="post">{hidden}<input type="hidden" name="id" value="{e(j["id"])}"><button name="action" value="approve">Autorizar y ejecutar</button><button name="action" value="reject">Descartar</button></form>'
        refresh='<meta http-equiv="refresh" content="5">' if active or s["status"]=="Ejecutando" else ""
        self.reply(f"""<!doctype html><html lang="es"><head><meta charset="utf-8">{refresh}<title>EcoBlend Direct v0.3</title><style>body{{font:16px system-ui;background:#101923;color:#edf5f8;max-width:850px;margin:35px auto;padding:20px}}section{{background:#1e2b38;padding:24px;border-radius:14px;margin:16px 0}}button{{background:#36b8a0;border:0;padding:12px 20px;border-radius:8px;margin:8px;cursor:pointer}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;color:#b5e9de}}a{{color:#8cd9ec}}</style></head><body><h1>EcoBlend Direct v0.3</h1><p>Blender · FreeCAD · Sin MCP</p><section><h2>Visualizacion de proyectos</h2><p><a href="http://127.0.0.1:8788/" target="_blank" rel="noopener">Abrir visor 3D de EcoBlend</a></p><p>El lanzador de escritorio inicia ambos servicios.</p></section><section><h2>Buzon de ChatGPT</h2><p>{'Conectado: '+str(remaining)+' segundos' if active else 'Desconectado'} · {e(s['inbox'])}</p><form method="post">{hidden}<button name="action" value="connect">Recibir encargos durante 20 minutos</button><button name="action" value="disconnect">Desconectar</button><button name="action" value="fetch">Consultar ahora</button></form>{pending}<p>La consulta es automatica; cada ejecucion requiere autorizacion local. No incluir datos privados en GitHub.</p></section><section><h2>Motor local</h2><form method="post">{hidden}<select name="engine"><option>blender</option><option>freecad</option></select> <input name="size" type="number" min=".01" max="10000" step="any" value="2"><button name="action" value="demo">Crear modelo</button><button name="action" value="status">Diagnostico</button></form><p>Blender: metros; FreeCAD: milimetros.</p></section><section><h2>{e(s['status'])}</h2><pre>{e(s['output'])}</pre><a href="/">Actualizar estado</a></section><p>Solo localhost. El historial permanece en tu PC. Cerrar PowerShell detiene el panel.</p></body></html>""")
    def do_POST(self):
        if self.headers.get("Host")!=self.host() or self.headers.get("Origin")!="http://"+self.host(): return self.reply("Origen invalido",403)
        try:
            n=int(self.headers.get("Content-Length","0"))
            if not 0<n<=4096: raise ValueError("Solicitud invalida")
            d=parse_qs(self.rfile.read(n).decode()); get=lambda k:d.get(k,[""])[0]
            if not secrets.compare_digest(get("token"),TOKEN): return self.reply("Token invalido",403)
            a=get("action")
            if a=="connect":
                with LOCK: STATE["until"]=time.monotonic()+1200
            elif a=="disconnect":
                with LOCK: STATE.update(until=0,pending=None,inbox="Desconectado")
            elif a=="fetch": fetch()
            elif a in ("approve","reject"):
                with LOCK:
                    j=STATE["pending"]
                    if not j or get("id")!=j["id"]: raise ValueError("Encargo cambiado; vuelve a consultar")
                    if a=="reject": record({"id":j["id"],"state":"Descartado"}); STATE["pending"]=None
                    else: start(["demo","--engine",j["engine"],"--size",str(j["size"])],j["id"])
            elif a=="status": start(["status"])
            elif a=="demo":
                j=validate({"id":"local","engine":get("engine"),"action":"demo","size":float(get("size"))})
                start(["demo","--engine",j["engine"],"--size",str(j["size"])])
            else: raise ValueError("Accion desconocida")
            self.redirect()
        except Exception as e: self.reply(html.escape(str(e))+' <a href="/">Volver</a>',400)
if __name__=="__main__":
    server=ThreadingHTTPServer(("127.0.0.1",8787),Handler)
    threading.Thread(target=poll,daemon=True).start()
    print("EcoBlend Direct v0.3 http://127.0.0.1:8787/",flush=True)
    webbrowser.open("http://127.0.0.1:8787/")
    server.serve_forever()
