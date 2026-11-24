"""Optional GitHub mailbox: public metadata only, explicit local approval."""
import json, pathlib, subprocess, sys, urllib.request
URL="https://raw.githubusercontent.com/FUNDACIONECOPIENSAEVOLUTION/creador-3d-online/feature/direct-engine/direct/job.json"
def main():
    req=urllib.request.Request(URL,headers={"Cache-Control":"no-cache","User-Agent":"EcoBlendDirect"})
    with urllib.request.urlopen(req,timeout=15) as r:
        raw=r.read(8193)
    if len(raw)>8192: raise ValueError("Job too large")
    job=json.loads(raw)
    if set(job)!={"id","engine","action","size"}: raise ValueError("Invalid fields")
    if job["engine"] not in ("blender","freecad") or job["action"]!="demo": raise ValueError("Unsupported action")
    if type(job["size"]) not in (int,float) or not 0.01<=job["size"]<=10000: raise ValueError("Invalid size")
    if not isinstance(job["id"],str) or not job["id"].isalnum() or len(job["id"])>64: raise ValueError("Invalid id")
    print(json.dumps(job,ensure_ascii=True))
    print("Blender uses meters by default; FreeCAD uses millimeters.")
    if input("Approve this public job locally? Type YES: ")!="YES": return
    subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name("agent.py")),"demo","--engine",job["engine"],"--size",str(job["size"])],check=True)
if __name__=="__main__": main()
