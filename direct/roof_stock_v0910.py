"""Compare stock sizes for an existing local roof revision. No motor execution."""
import argparse, csv, json, math, pathlib
def pack(pieces,stock,module=0,kerf=.003):
    bins=[]
    for q in sorted(pieces,key=lambda q:-q["length"]):
        l=q["length"]
        # module is optional and must be measured along the sheet, not across crests.
        l=math.ceil((l+kerf)/module-1e-9)*module if module else l+kerf
        if l>stock+1e-9:raise ValueError("Piece exceeds commercial length: "+q["id"])
        for b in bins:
            if b["used"]+l<=stock+1e-9:
                b["used"]+=l;b["pieces"].append([q["id"],l]);break
        else:bins.append({"used":l,"pieces":[[q["id"],l]]})
    return bins
def main():
    p=argparse.ArgumentParser();p.add_argument("project",type=pathlib.Path,nargs="?");p.add_argument("--module",type=float,default=0);p.add_argument("--selftest",action="store_true");a=p.parse_args()
    if a.selftest:
        q=[{"id":str(i),"length":2.9} for i in range(4)]
        assert len(pack(q,11.8))==1 and len(pack(q,5.9))==2
        assert len(pack(q,5.8))==4
        assert all(b["used"]<=5.9 for b in pack(q,5.9,.1))
        print("STOCK SELFTEST OK");return
    if not a.project or not math.isfinite(a.module) or not 0<=a.module<=1:p.error("Project/module invalid")
    roofs=json.loads((a.project/"roof_data.json").read_text(encoding="utf-8"))
    pieces=[q for r in roofs for q in r["sheets"]]
    rows=[]
    for stock in (11.8,5.9,5.8):
        for name,items in [(r["id"],r["sheets"]) for r in roofs]+[("GLOBAL",pieces)]:
            try:
                bins=pack(items,stock,a.module)
                used=sum(b["used"] for b in bins);bought=len(bins)*stock
                rows.append(dict(roof=name,stock_m=stock,count=len(bins),purchased_m=round(bought,3),unused_m=round(bought-used,3),bins=bins))
            except ValueError as e:rows.append(dict(roof=name,stock_m=stock,error=str(e)))
    import tempfile
    out=pathlib.Path(tempfile.mkdtemp(prefix="cut-study-",dir=a.project))
    (out/"stock_comparison.json").write_text(json.dumps({"module_m":a.module,"limitations":"No diagonal scrap reuse; no guarantee of lap or profile phase; first fit decreasing, not exact optimum","options":rows},indent=2),encoding="utf-8")
    with (out/"stock_comparison.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f,delimiter=";");w.writerow(["cubierta","largo comercial m","cantidad","metros comprados","sobrante lineal","error"])
        for r in rows:w.writerow([r["roof"],r["stock_m"],r.get("count"),r.get("purchased_m"),r.get("unused_m"),r.get("error")])
    print(json.dumps({"folder":str(out),"global":[{k:v for k,v in r.items() if k!="bins"} for r in rows if r["roof"]=="GLOBAL"]}))
if __name__=="__main__":main()
