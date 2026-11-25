"""Integrated synthetic material smoke test. No real photos or network."""
import subprocess,sys,pathlib,json
from reality_v092 import surface_ids,ROOT,png
from architecture_plus_v092 import DEMO
HERE=pathlib.Path(__file__).resolve().parent
def call(*args):
    p=subprocess.run([sys.executable,str(HERE/args[0]),*args[1:]],capture_output=True,text=True,timeout=560)
    print(p.stdout,flush=True)
    if p.returncode:raise RuntimeError(p.stderr or p.stdout)
    return json.loads(p.stdout.strip().splitlines()[-1])
def main():
    result=call("architecture_plus_v092.py","--demo","--engine","both")
    src=pathlib.Path(result["folder"]);assert result["ok"] and src.resolve().is_relative_to(ROOT.resolve())
    refs=src/"photo_references";refs.mkdir(exist_ok=True)
    png(refs/"brick.png","brick");png(refs/"floor.png","floor")
    ids=surface_ids(DEMO)
    mapping={k:{"image":"floor.png" if k=="P01" or k.endswith("-P") else "brick.png","source":"synthetic","mode":"tile","repeat_m":1} for k in ids}
    m=refs/"demo_mapping.json";m.write_text(json.dumps(mapping),encoding="utf-8")
    result=call("reality_v092.py","--project",src.name,"--mapping",str(m))
    assert result["ok"] and set(result["audit"]["textured_materials"])=={"Reality_"+k for k in ids}
    first=pathlib.Path(result["folder"])
    m=refs/"revision_mapping.json";m.write_text(json.dumps({"M01-A":{"image":"floor.png","source":"synthetic","mode":"tile","repeat_m":1}}),encoding="utf-8")
    result=call("reality_v092.py","--project",first.name,"--mapping",str(m))
    assert result["ok"] and set(result["audit"]["textured_materials"])=={"Reality_"+k for k in ids}
    print("INTEGRATED TEST OK: geometry, all materials and one-face revision",flush=True)
if __name__=="__main__":main()
