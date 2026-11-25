"""Read-only local project gallery; serves only generated GLB files."""
import html, pathlib, re, json, webbrowser, secrets, threading, os
from urllib.parse import parse_qs
TOKEN=secrets.token_urlsafe(32)
LOCK=threading.RLock()
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
ROOT=(pathlib.Path(__file__).resolve().parent.parent/"projects").resolve()
def project(jid):
    if not re.fullmatch(r"job-[A-Za-z0-9_-]+",jid): raise ValueError("ID invalido")
    p=ROOT/jid
    if p.is_symlink() or not p.is_dir() or not p.resolve().is_relative_to(ROOT): raise ValueError("Proyecto no disponible")
    return p
def metadata(p):
    f=p/"studio_project.json"
    if f.is_symlink(): raise ValueError("Metadata invalida")
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"name":p.name,"state":"active"}
def change(jid,action,name=""):
    with LOCK:
        p=project(jid); m=metadata(p)
        if action=="rename":
            name=name.strip()
            if not name or len(name)>100 or any(ord(c)<32 for c in name): raise ValueError("Nombre invalido")
            m["name"]=name
        elif action in ("archive","trash","restore"):
            m["state"]={"archive":"saved","trash":"trash","restore":"active"}[action]
        else: raise ValueError("Accion invalida")
        f=p/"studio_project.json"; tmp=p/(".metadata-"+secrets.token_hex(8))
        tmp.write_text(json.dumps(m,ensure_ascii=False),encoding="utf-8")
        os.replace(tmp,f)
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.headers.get("Host")!="127.0.0.1:8788" or self.headers.get("Origin")!="http://127.0.0.1:8788" or self.path!="/manage":
            self.send_error(403);return
        try:
            n=int(self.headers.get("Content-Length","0"))
            if not 0<n<=4096: raise ValueError("Solicitud invalida")
            d=parse_qs(self.rfile.read(n).decode());g=lambda k:d.get(k,[""])[0]
            if not secrets.compare_digest(g("token"),TOKEN): self.send_error(403);return
            change(g("job"),g("action"),g("name"))
            self.send_response(303);self.send_header("Location","/?state="+("trash" if g("action")=="trash" else "saved" if g("action")=="archive" else "active"));self.end_headers()
        except Exception: self.send_error(400,"Operacion no realizada")

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
        state=parse_qs(urlsplit(self.path).query).get("state",["active"])[0]
        if state not in ("active","saved","trash"):state="active"
        jobs=[p for p in jobs if metadata(p).get("state") == state]
        opts="".join(f'<option value="/model/{p.name}/demo.glb">{html.escape(metadata(p).get("name",p.name))} ({p.name})</option>' for p in jobs)
        rows=[]
        for p in jobs:
            m=metadata(p); name=html.escape(m.get("name",p.name),quote=True)
            actions='<button name="action" value="restore">Restaurar</button>' if state=="trash" else '<button name="action" value="archive">Guardar / archivar</button><button name="action" value="trash">Papelera</button><button name="action" value="restore">Activar</button>'
            rows.append(f'<form action="/manage" method="post"><input type="hidden" name="token" value="{TOKEN}"><input type="hidden" name="job" value="{p.name}"><input name="name" maxlength="100" value="{name}"><button name="action" value="rename">Renombrar</button>{actions}</form>')
        manager='<details><summary>Administrar proyectos</summary><a href="/?state=active">Activos</a> · <a href="/?state=saved">Guardados</a> · <a href="/?state=trash">Papelera</a><p>Estado: '+state+' · Los archivos originales se conservan; la papelera solo cambia su estado.</p>'+''.join(rows)+'</details>'
        body="""<!doctype html><html lang="es"><meta charset="utf-8"><title>EcoBlend Galeria 3D</title><style>body{background:#101923;color:#e8f1f7;font:16px system-ui;margin:24px}main{display:grid;grid-template-columns:3fr 1fr;gap:20px}#view{height:72vh;background:#1e2b38}aside{background:#1e2b38;padding:16px;overflow:auto}button,select{padding:10px;margin:6px}pre{white-space:pre-wrap}canvas{display:block}</style><h1>EcoBlend | Studio 0.9.2</h1><a href="http://127.0.0.1:8787/">Panel de control</a> MANAGER <p>Vista 3D bajo demanda</p><select id="jobs">OPTIONS</select><button id="fit">Encuadrar</button><button id="roof">Cubierta visible</button><button id="top">Superior</button><button id="front">Frontal</button><button id="side">Lateral</button><button id="iso">Isometrica</button><a href="http://127.0.0.1:8789/">Reality Painter</a><button id="grid">Cuadricula</button><button id="wire">Malla</button><a href="/" style="color:#8ee">Actualizar proyectos</a><main><div id="view"></div><aside><h2>Objetos</h2><div id="objects"></div><h2>Inspector</h2><pre id="info">Selecciona una pieza</pre></aside></main><p>Arrastra para rotar; rueda para acercar; clic sobre una pieza para inspeccionarla. Solo lectura.</p><script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script><script type="module">
import * as T from 'three';import {OrbitControls} from 'three/addons/controls/OrbitControls.js';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const el=document.querySelector('#view'),sel=document.querySelector('#jobs'),info=document.querySelector('#info'),list=document.querySelector('#objects');const scene=new T.Scene();scene.background=new T.Color(0x253341);const camera=new T.PerspectiveCamera(45,1,.001,100000);const renderer=new T.WebGLRenderer({antialias:false});el.append(renderer.domElement);const controls=new OrbitControls(camera,renderer.domElement);scene.add(new T.HemisphereLight(0xffffff,0x657080,1.0));const light=new T.DirectionalLight(0xffffff,1.2);light.position.set(4,8,5);scene.add(light);let grid=new T.GridHelper(10,10);scene.add(grid);let model,meshes=[],helper,seq=0,wire=false;
function fit(direction=new T.Vector3(1,.8,1)){if(!model)return;const b=new T.Box3().setFromObject(model),c=b.getCenter(new T.Vector3()),s=Math.max(b.getSize(new T.Vector3()).length(),.01);controls.target.copy(c);camera.position.copy(c).add((direction.isVector3?direction:new T.Vector3(1,.8,1)).normalize().multiplyScalar(s*1.6));camera.near=s/10000;camera.far=s*100;camera.updateProjectionMatrix();controls.update();grid.scale.setScalar(s/8);draw();}
function select(m){if(helper)scene.remove(helper);helper=new T.BoxHelper(m,0xffcc44);scene.add(helper);draw();const b=new T.Box3().setFromObject(m);info.textContent=JSON.stringify({nombre:m.name,dimensiones:b.getSize(new T.Vector3()).toArray(),posicion:m.getWorldPosition(new T.Vector3()).toArray(),vertices:m.geometry.attributes.position.count,materiales:[m.material].flat().map(x=>x.name)},null,2);}
function load(){const n=++seq;if(!sel.value){info.textContent='No hay GLB disponibles';return;}new GLTFLoader().load(sel.value,g=>{if(n!==seq)return;if(model){scene.remove(model);model.traverse(o=>{if(o.isMesh){o.geometry.dispose();[o.material].flat().forEach(m=>{for(const v of Object.values(m))if(v&&v.isTexture)v.dispose();m.dispose();});}});}if(helper)scene.remove(helper);model=g.scene;scene.add(model);document.querySelector('#roof').textContent='Cubierta visible';meshes=[];list.replaceChildren();model.traverse(o=>{if(o.isMesh){meshes.push(o);const btn=document.createElement('button');btn.textContent=o.name||'Pieza '+meshes.length;btn.onclick=()=>select(o);list.append(btn);}});info.textContent=meshes.length+' mallas';fit();},undefined,e=>info.textContent='Error cargando GLB: '+e);}
document.querySelector('#roof').onclick=()=>{if(!model)return;const roof=[];model.traverse(o=>{if(/^C01($|[_.-])/.test(o.name))roof.push(o);});if(!roof.length){info.textContent='Este proyecto no tiene cubierta identificada';return;}const visible=!roof[0].visible;roof.forEach(o=>o.visible=visible);document.querySelector('#roof').textContent=visible?'Cubierta visible':'Cubierta oculta';draw();};
document.querySelector('#top').onclick=()=>fit(new T.Vector3(0,1,.001));document.querySelector('#front').onclick=()=>fit(new T.Vector3(0,0,1));document.querySelector('#side').onclick=()=>fit(new T.Vector3(1,0,0));document.querySelector('#iso').onclick=()=>fit();
sel.onchange=load;document.querySelector('#fit').onclick=fit;document.querySelector('#grid').onclick=()=>{grid.visible=!grid.visible;draw();};document.querySelector('#wire').onclick=()=>{wire=!wire;meshes.forEach(m=>[m.material].flat().forEach(x=>x.wireframe=wire));draw();};renderer.domElement.addEventListener('dblclick',e=>{const r=renderer.domElement.getBoundingClientRect(),p=new T.Vector2((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1),ray=new T.Raycaster();ray.setFromCamera(p,camera);const h=ray.intersectObjects(meshes,false);if(h.length)select(h[0].object);});function draw(){const w=el.clientWidth,h=el.clientHeight;if(renderer.domElement.width!==w||renderer.domElement.height!==h){renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}renderer.render(scene,camera);}controls.addEventListener("change",draw);new ResizeObserver(draw).observe(el);load();draw();
</script></html>""".replace("OPTIONS",opts).replace("MANAGER",manager)
        data=body.encode()
        self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.send_header("X-Frame-Options","DENY"); self.send_header("Content-Security-Policy","default-src 'self'; script-src 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self' https://cdn.jsdelivr.net; frame-ancestors 'none'"); self.end_headers(); self.wfile.write(data)
if __name__=="__main__":
    server=ThreadingHTTPServer(("127.0.0.1",8788),Handler)
    webbrowser.open("http://127.0.0.1:8788/")
    server.serve_forever()
