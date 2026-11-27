"""Stable portable updater. Only explicit release manifests are installed."""
import argparse,hashlib,json,os,pathlib,re,shutil,socket,subprocess,sys,tempfile,urllib.request
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent.parent
BASE="https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/"
MANIFEST=BASE+"feature/direct-engine/direct/stable_release.json"
STATE=HERE.parent/"update_state.json"
def download(url,limit):
    with urllib.request.urlopen(url,timeout=8) as r:
        data=r.read(limit+1)
    if len(data)>limit:raise ValueError("Download too large")
    return data
def validate(m):
    if type(m["serial"]) is not int or m["serial"]<1:raise ValueError("serial")
    if not re.fullmatch("[0-9a-f]{40}",m["commit"]):raise ValueError("commit")
    files=m["files"]
    if not isinstance(files,dict) or not 1<=len(files)<=50:raise ValueError("files")
    for name,digest in files.items():
        if not re.fullmatch("[A-Za-z][A-Za-z0-9_]*[.]py",name) or name==pathlib.Path(__file__).name or not re.fullmatch("[0-9a-f]{64}",digest):raise ValueError("file")
    if m["launcher"] not in files or not m["launcher"].startswith("studio_launcher_portable_"):raise ValueError("launcher")
    if not isinstance(m["tests"],list) or any(t not in files for t in m["tests"]):raise ValueError("tests")
def occupied():
    for port in (8787,8788,8789):
        with socket.socket() as s:
            s.settimeout(.2)
            if s.connect_ex(("127.0.0.1",port))==0:return True
    return False
def update(state):
    m=json.loads(download(MANIFEST,65536));validate(m)
    if m["serial"]<=state["serial"]:return state
    with tempfile.TemporaryDirectory(prefix="update-",dir=ROOT/"Cache") as t:
        stage=pathlib.Path(t)
        for name,digest in m["files"].items():
            data=download(BASE+m["commit"]+"/direct/"+name,4*1024*1024)
            if hashlib.sha256(data).hexdigest()!=digest:raise ValueError("Checksum "+name)
            compile(data,name,"exec");(stage/name).write_bytes(data)
        backup=pathlib.Path(tempfile.mkdtemp(prefix="update-backup-",dir=ROOT/"Backups"))
        installed=[]
        try:
            for name in m["files"]:
                dest=HERE/name
                if dest.exists():shutil.copy2(dest,backup/name)
                os.replace(stage/name,dest);installed.append(name)
            env=os.environ.copy();env.update(ECOBLEND_PROJECTS=str(ROOT/"Projects"),ECOBLEND_LOGS=str(ROOT/"Logs"))
            for name in m["tests"]:
                subprocess.run([sys.executable,str(HERE/name),"--selftest"],cwd=HERE,env=env,check=True,timeout=90)
            new={"serial":m["serial"],"launcher":m["launcher"],"previous":state["launcher"]}
            tmp=STATE.with_suffix(".tmp");tmp.write_text(json.dumps(new),encoding="utf-8");os.replace(tmp,STATE)
            print("UPDATE OK",m["serial"],flush=True);return new
        except BaseException:
            for name in reversed(installed):
                dest=HERE/name
                if (backup/name).exists():os.replace(backup/name,dest)
                else:dest.unlink(missing_ok=True)
            raise
def main():
    p=argparse.ArgumentParser();p.add_argument("--selftest",action="store_true");p.add_argument("--offline",action="store_true");a=p.parse_args()
    if a.selftest:
        m={"serial":1,"commit":"a"*40,"files":{"studio_launcher_portable_v1.py":"b"*64},"launcher":"studio_launcher_portable_v1.py","tests":[]};validate(m)
        try:validate(dict(m,launcher="../x"))
        except ValueError:pass
        else:raise AssertionError("invalid launcher accepted")
        print("UPDATER SELFTEST OK");return
    state=json.loads(STATE.read_text()) if STATE.exists() else {"serial":0,"launcher":"studio_launcher_portable_v0916.py"}
    if occupied():raise SystemExit("EcoBlend ya esta activo. Cierre el lanzador antes de actualizar.")
    if not a.offline:
        try:state=update(state)
        except Exception as e:print("Actualizacion omitida; se conserva version anterior:",e,flush=True)
    launcher=state["launcher"]
    if not re.fullmatch("studio_launcher_portable_[A-Za-z0-9_]+[.]py",launcher):raise ValueError("launcher state")
    sys.exit(subprocess.call([sys.executable,str(HERE/launcher)],cwd=HERE))
if __name__=="__main__":main()
