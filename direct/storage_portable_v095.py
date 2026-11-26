"""EcoBlend external storage and lightweight profile. Standard library only."""
import pathlib, os, json, shutil, uuid, argparse
HOME=pathlib.Path(__file__).resolve().parent.parent
CONFIG=HOME/"storage_v094.json"
def initialize(root):
    root=pathlib.Path(root).resolve()
    root.mkdir(parents=True,exist_ok=True)
    marker=root/".ecoblend-volume"
    if not marker.exists():marker.write_text(uuid.uuid4().hex,encoding="ascii")
    for name in ("Projects","Textures","AI-Images","Renders","Exports","Cache","Backups","Logs"):
        (root/name).mkdir(exist_ok=True)
    cfg={"root":str(root),"id":marker.read_text(encoding="ascii").strip(),"profile":"lite","threads":2,"texture_px":1024}
    tmp=CONFIG.with_suffix(".tmp");tmp.write_text(json.dumps(cfg,indent=2),encoding="utf-8");os.replace(tmp,CONFIG)
    return cfg
def storage(min_free=0):
    cfg=json.loads(CONFIG.read_text(encoding="utf-8"))
    root=HOME.parent.resolve() if HOME.name=="Engine" else pathlib.Path(cfg["root"])
    if not root.is_dir() or (root/".ecoblend-volume").read_text(encoding="ascii").strip()!=cfg["id"]:raise RuntimeError("Disco EcoBlend no disponible o incorrecto")
    if shutil.disk_usage(root).free<min_free:raise RuntimeError("Espacio insuficiente en disco EcoBlend")
    return root
def configure():
    root=storage(2*1024**3)
    os.environ.update(ECOBLEND_PROJECTS=str(root/"Projects"),ECOBLEND_LOGS=str(root/"Logs"),ECOBLEND_THREADS="2",ECOBLEND_TEXTURE_PX="1024",TEMP=str(root/"Cache"),TMP=str(root/"Cache"),TMPDIR=str(root/"Cache"))
    return root
def main():
    p=argparse.ArgumentParser();p.add_argument("--init");p.add_argument("--status",action="store_true");a=p.parse_args()
    if a.init:initialize(a.init)
    root=storage()
    print(json.dumps({"root":str(root),"free_gib":round(shutil.disk_usage(root).free/1024**3,2),"profile":"lite","threads":2,"texture_px":1024}))
if __name__=="__main__":main()
