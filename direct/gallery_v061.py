"""Read-only local project gallery; serves only generated GLB files."""
import html, pathlib, re, json, webbrowser, secrets, threading, os
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
ROOT=(pathlib.Path(__file__).resolve().parent.parent/"projects").resolve()
TOKEN=secrets.token_urlsafe(32)
LOCK=threading.Lock()
META=ROOT/"gallery_index.json"
def index():
    return json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.headers.get("Host")!="127.0.0.1:8788" or self.headers.get("Origin")!="http://127.0.0.1:8788": self.send_error(403);return
        try:
            n=int(self.headers.get("Content-Length","0"))
            if not 0<n<=4096: raise ValueError()
            d=parse_qs(self.rfile.read(n).decode());get=lambda k:d.get(k,[""])[0]
            if not secrets.compare_digest(get("token"),TOKEN): self.send_error(403);return
            jid=get("project");action=get("action");name=get("name").strip()
            if not re.fullmatch(r"job-[A-Za-z0-9_-]+",jid) or not (ROOT/jid/"demo.glb").is_file() or not (ROOT/jid).resolve().is_relative_to(ROOT): raise ValueError()
            with LOCK:
                data=index(); entry=data.setdefault(jid,{"name":jid,"state":"active"})
                if action=="save":
                    if not 1<=len(name)<=100: raise ValueError()
                    entry["name"]=name
                elif action in ("active","archive","trash"): entry["state"]=action
                else: raise ValueError()
                tmp=META.with_suffix(".tmp");tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8");os.replace(tmp,META)
            self.send_response(303);self.send_header("Location","/?state="+("archive" if action=="archive" else "trash" if action=="trash" else "active"));self.end_headers()
        except (ValueError,OSError): self.send_error(400)

    def do_GET(self):
        if self.headers.get("Host")!="127.0.0.1:8788":
            self.send_error(403); return
        path=urlsplit(self.path).path
        match=re.fullmatch(r"/model/(job-[A-Za-z0-9_-]+)/demo.glb",path)
        if match:
            f=(ROOT/match[1]/"demo.glb").resolve()
            if not f.is_relative_to(ROOT) or not f.is_file(): self.send_error(404); return
            self.send_response(200); self.send_header("Content-Type","model/gltf-binary"); self.send_header("Content-Length",str(f.stat().st_size)); self.end_headers()
            with f.open("rb") as src:
                import shutil
                shutil.copyfileobj(src,self.wfile)
            return
        if path!="/": self.send_error(404); return
        jobs=sorted((p for p in ROOT.glob("job-*") if p.is_dir() and (p/"demo.glb").is_file() and p.resolve().is_relative_to(ROOT) and re.fullmatch(r"job-[A-Za-z0-9_-]+",p.name)),key=lambda p:(p/"demo.glb").stat().st_mtime,reverse=True)
        with LOCK: metadata=index()
        state=parse_qs(urlsplit(self.path).query).get("state",["active"])[0]
        if state not in ("active","archive","trash"): state="active"
        jobs=[p for p in jobs if metadata.get(p.name,{}).get("state","active")==state]
        opts="".join(f'<option value="/model/{p.name}/demo.glb">{html.escape(metadata.get(p.name,{}).get("name",p.name))}</option>' for p in jobs)
        management=f'<nav><a href="/?state=active">Activos</a> · <a href="/?state=archive">Archivados</a> · <a href="/?state=trash">Papelera</a> · <a href="http://127.0.0.1:8787/">Control</a></nav><form method="post"><input type="hidden" name="token" value="{TOKEN}"><input type="hidden" id="project" name="project"><input name="name" maxlength="100" placeholder="Nombre del proyecto"><button name="action" value="save">Guardar nombre</button><button name="action" value="archive">Archivar</button><button name="action" value="trash">Enviar a papelera</button><button name="action" value="active">Restaurar</button></form><p>Los archivos se conservan en disco. Papelera reversible.</p>'
        body="""<!doctype html><html lang="es"><meta charset="utf-8"><title>EcoBlend Galeria 3D</title><style>body{background:#101923;color:#e8f1f7;font:16px system-ui;margin:24px}main{display:grid;grid-template-columns:3fr 1fr;gap:20px}#view{height:72vh;background:#1e2b38}aside{background:#1e2b38;padding:16px;overflow:auto}button,select{padding:10px;margin:6px}pre{white-space:pre-wrap}canvas{display:block}</style><h1>EcoBlend | Galeria 3D local</h1>MANAGEMENT<select id="jobs">OPTIONS</select><button id="fit">Encuadrar</button><button id="grid">Cuadricula</button><button id="wire">Malla</button><a href="/" style="color:#8ee">Actualizar proyectos</a><main><div id="view"></div><aside><h2>Objetos</h2><div id="objects"></div><h2>Inspector</h2><pre id="info">Selecciona una pieza</pre></aside></main><p>Arrastra para rotar; rueda para acercar; clic sobre una pieza para inspeccionarla. Gestion local de proyectos.</p><script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script><script type="module">
import * as T from 'three';import {OrbitControls} from 'three/addons/controls/OrbitControls.js';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const el=document.querySelector('#view'),sel=document.querySelector('#jobs'),info=document.querySelector('#info'),list=document.querySelector('#objects');const scene=new T.Scene();scene.background=new T.Color(0x253341);const camera=new T.PerspectiveCamera(45,1,.001,100000);const renderer=new T.WebGLRenderer({antialias:false});el.append(renderer.domElement);const controls=new OrbitControls(camera,renderer.domElement);scene.add(new T.HemisphereLight(0xffffff,0x657080,1.1));const light=new T.DirectionalLight(0xffffff,1.5);light.position.set(4,8,5);scene.add(light);let grid=new T.GridHelper(10,10);scene.add(grid);let model,meshes=[],helper,seq=0,wire=false;
function fit(){if(!model)return;const b=new T.Box3().setFromObject(model),c=b.getCenter(new T.Vector3()),s=Math.max(b.getSize(new T.Vector3()).length(),.01);controls.target.copy(c);camera.position.copy(c).add(new T.Vector3(1,.8,1).normalize().multiplyScalar(s*1.6));camera.near=s/10000;camera.far=s*100;camera.updateProjectionMatrix();controls.update();grid.scale.setScalar(s/8);}
function select(m){if(helper)scene.remove(helper);helper=new T.BoxHelper(m,0xffcc44);scene.add(helper);const b=new T.Box3().setFromObject(m);info.textContent=JSON.stringify({nombre:m.parent?.userData?.surface_id||m.userData.surface_id||m.name,dimensiones:b.getSize(new T.Vector3()).toArray(),posicion:m.getWorldPosition(new T.Vector3()).toArray(),vertices:m.geometry.attributes.position.count,materiales:[m.material].flat().map(x=>x.name)},null,2);}
function load(){document.querySelector("#project").value=sel.value.split("/")[2]||"";const n=++seq;if(!sel.value){info.textContent='No hay GLB disponibles';return;}new GLTFLoader().load(sel.value,g=>{if(n!==seq)return;if(model)scene.remove(model);if(helper)scene.remove(helper);model=g.scene;scene.add(model);meshes=[];list.replaceChildren();model.traverse(o=>{if(o.isMesh){meshes.push(o);const btn=document.createElement('button');btn.textContent=o.name||'Pieza '+meshes.length;btn.onclick=()=>select(o);list.append(btn);}});info.textContent=meshes.length+" mallas; "+meshes.filter(m=>[m.material].flat().some(x=>x.map)).length+" con textura";fit();draw();},undefined,e=>info.textContent='Error cargando GLB: '+e);}
sel.onchange=load;document.querySelector('#fit').onclick=fit;document.querySelector('#grid').onclick=()=>grid.visible=!grid.visible;document.querySelector('#wire').onclick=()=>{wire=!wire;meshes.forEach(m=>[m.material].flat().forEach(x=>x.wireframe=wire));};renderer.domElement.addEventListener('dblclick',e=>{const r=renderer.domElement.getBoundingClientRect(),p=new T.Vector2((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1),ray=new T.Raycaster();ray.setFromCamera(p,camera);const h=ray.intersectObjects(meshes,false);if(h.length)select(h[0].object);});function draw(){const w=el.clientWidth,h=el.clientHeight;if(renderer.domElement.width!==w||renderer.domElement.height!==h){renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}renderer.render(scene,camera);}controls.addEventListener("change",draw);new ResizeObserver(draw).observe(el);for(const id of ["grid","wire","fit"])document.querySelector("#"+id).addEventListener("click",draw);list.addEventListener("click",draw);renderer.domElement.addEventListener("dblclick",draw);load();draw();
</script></html>""".replace("OPTIONS",opts).replace("MANAGEMENT",management)
        data=body.encode()
        self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.send_header("X-Frame-Options","DENY"); self.send_header("Content-Security-Policy","default-src 'self'; script-src 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self' https://cdn.jsdelivr.net; form-action 'self'; frame-ancestors 'none'"); self.end_headers(); self.wfile.write(data)
if __name__=="__main__":
    server=ThreadingHTTPServer(("127.0.0.1",8788),Handler)
    webbrowser.open("http://127.0.0.1:8788/")
    server.serve_forever()
