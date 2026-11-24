"""Local EcoBlend control panel. Standard library only; no public listener."""
import html, json, pathlib, secrets, subprocess, sys, threading, webbrowser, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
ROOT=pathlib.Path(__file__).resolve().parent
TOKEN=secrets.token_urlsafe(32)
LOCK=threading.Lock()
STATE={"status":"Listo","output":""}
URL="https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/feature/direct-engine/direct/job.json"
def run(args):
    try:
        p=subprocess.run([sys.executable,str(ROOT/"agent.py"),*args],cwd=ROOT,capture_output=True,text=True,timeout=210)
        STATE.update(status="Completado" if p.returncode==0 else "Error",output=(p.stdout+p.stderr)[-8000:])
    except Exception as e: STATE.update(status="Error",output=str(e))
    finally: LOCK.release()
class Handler(BaseHTTPRequestHandler):
    def valid_host(self):
        return self.headers.get("Host")==f"127.0.0.1:{self.server.server_port}"
    def reply(self,body,status=200):
        data=body.encode("utf-8")
        self.send_response(status); self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Cache-Control","no-store"); self.send_header("X-Frame-Options","DENY")
        self.send_header("Content-Security-Policy","default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
        self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if not self.valid_host(): return self.reply("Host invalido",403)
        if self.path!="/": return self.reply("No encontrado",404)
        self.panel()
    def panel(self,job=None):
        e=html.escape
        jobform=""
        if job:
            jobform=f"<h2>Encargo remoto (revisar antes de ejecutar)</h2><pre>{e(json.dumps(job,ensure_ascii=False))}</pre><form method='post'><input type='hidden' name='token' value='{TOKEN}'><input type='hidden' name='action' value='remote'><input type='hidden' name='engine' value='{e(job['engine'])}'><input type='hidden' name='size' value='{job['size']}'><button>Autorizar y ejecutar</button></form>"
        self.reply(f"""<!doctype html><html lang='es'><meta charset='utf-8'><title>EcoBlend Direct</title><style>body{{font:16px system-ui;background:#101923;color:#edf5f8;max-width:850px;margin:40px auto;padding:20px}}section{{background:#1e2b38;padding:24px;border-radius:14px;margin:16px 0}}button{{background:#36b8a0;border:0;padding:12px 20px;border-radius:8px;margin:8px;cursor:pointer}}input,select{{padding:9px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;color:#b5e9de}}a{{color:#8cd9ec}}</style><h1>EcoBlend Direct</h1><p>Motor local · Blender y FreeCAD · sin MCP</p><section><h2>Motor 3D</h2><form method='post'><input type='hidden' name='token' value='{TOKEN}'><label>Motor <select name='engine'><option>blender</option><option>freecad</option></select></label> <label>Tamaño <input name='size' type='number' min='.01' max='10000' step='any' value='2'></label><br><button name='action' value='demo'>Crear modelo de prueba</button><button name='action' value='status'>Diagnóstico</button></form><p>Blender: metros; FreeCAD: milímetros.</p></section><section><h2>Encargos de ChatGPT</h2><form method='post'><input type='hidden' name='token' value='{TOKEN}'><button name='action' value='fetch'>Consultar encargo de GitHub</button></form>{jobform}</section><section><h2>{e(STATE['status'])}</h2><pre>{e(STATE['output'])}</pre><a href='/'>Actualizar estado</a></section><p>Solo accesible desde este computador. Cierra PowerShell para detener el panel.</p></html>""")
    def do_POST(self):
        if not self.valid_host() or self.headers.get("Origin")!=f"http://127.0.0.1:{self.server.server_port}": return self.reply("Origen invalido",403)
        try:
            n=int(self.headers.get("Content-Length","0"))
            if not 0<n<=4096: raise ValueError("Solicitud invalida")
            data=parse_qs(self.rfile.read(n).decode())
            get=lambda k:data.get(k,[""])[0]
            if not secrets.compare_digest(get("token"),TOKEN): return self.reply("Token invalido",403)
            action=get("action")
            if action=="fetch":
                with urllib.request.urlopen(URL,timeout=15) as r: raw=r.read(8193)
                if len(raw)>8192: raise ValueError("Encargo demasiado grande")
                j=json.loads(raw)
                if set(j)!={"id","engine","action","size"} or j["action"]!="demo" or j["engine"] not in ("blender","freecad") or type(j["size"]) not in (int,float) or not .01<=j["size"]<=10000: raise ValueError("Encargo no permitido")
                return self.panel(j)
            if action=="status": args=["status"]
            elif action in ("demo","remote"):
                engine=get("engine"); size=float(get("size"))
                if engine not in ("blender","freecad") or not .01<=size<=10000: raise ValueError("Parametros invalidos")
                args=["demo","--engine",engine,"--size",str(size)]
            else: raise ValueError("Accion desconocida")
            if LOCK.acquire(False):
                STATE.update(status="Ejecutando",output="")
                threading.Thread(target=run,args=(args,),daemon=True).start()
            return self.panel()
        except Exception as ex: return self.reply(html.escape(str(ex)),400)
if __name__=="__main__":
    server=ThreadingHTTPServer(("127.0.0.1",8787),Handler)
    url="http://127.0.0.1:8787/"
    print("EcoBlend Direct:",url,flush=True)
    webbrowser.open(url)
    server.serve_forever()
