"""EcoBlend Studio local launcher: one process supervising three HTTP services."""
import subprocess,sys,pathlib,os,time,webbrowser,urllib.request,socket
from storage_portable_v095 import configure,storage
HERE=pathlib.Path(__file__).resolve().parent
def listening(port):
    with socket.socket() as s:
        s.settimeout(.2)
        return s.connect_ex(("127.0.0.1",port))==0
def main():
    root=configure()
    os.environ["ECOBLEND_BLENDER"]=str(next((root/"Software"/"Blender").rglob("blender.exe")))
    os.environ["ECOBLEND_FREECAD"]=str(next(p for p in (root/"Software"/"FreeCAD").rglob("freecadcmd.exe") if p.parent.name.lower()=="bin"))
    if "--test" in sys.argv:
        subprocess.run([sys.executable,str(HERE/"test_studio_v092.py")],check=True,cwd=HERE)
        return
    modules=[(8787,"panel_v0910"),(8788,"gallery_v096"),(8789,"painter_panel_v092")]
    if any(listening(port) for port,_ in modules):
        raise SystemExit("Cierre primero los servidores EcoBlend anteriores (8787-8789).")
    children=[]
    logs=root/"Logs";logs.mkdir(exist_ok=True)
    try:
        for port,module in modules:
            code="import runpy,webbrowser;webbrowser.open=lambda *a,**k:False;runpy.run_module("+repr(module)+",run_name='__main__')"
            with (logs/(module+".log")).open("a",encoding="utf-8") as log:
                children.append(subprocess.Popen([sys.executable,"-u","-c",code],cwd=HERE,stdout=log,stderr=subprocess.STDOUT))
        deadline=time.monotonic()+15
        while not all(listening(port) for port,_ in modules):
            if any(p.poll() is not None for p in children) or time.monotonic()>deadline:raise RuntimeError("Error de arranque; consulte logs")
            time.sleep(.2)
        webbrowser.open("http://127.0.0.1:8787/")
        print("EcoBlend activo. Ctrl+C cierra los tres servicios.",flush=True)
        while all(p.poll() is None for p in children):
            storage();time.sleep(1)
        raise RuntimeError("Un servicio termino; consulte logs")
    finally:
        for p in children:
            if p.poll() is None:p.terminate()
        for p in children:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
if __name__=="__main__":main()
