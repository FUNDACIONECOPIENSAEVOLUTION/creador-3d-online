"""Document local roof cutting study as SVG and native FreeCAD spreadsheet.
Does not overwrite prior revisions or claim structural verification."""
import argparse, pathlib, json, math, html, tempfile, subprocess, sys, os
from agent_v04 import locate
def make_svg(rows,stock,path):
    W=1150; H=110+len(rows)*66; x0=100; span=1000
    colors={"T2":"#c07854","T3":"#397c87","T4":"#9374ae","T5":"#b59a46","T6":"#748b50"}
    a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/><g font-family="Arial" fill="#243039"><text x="25" y="30" font-size="22">EcoBlend | Plan de corte longitudinal {stock:.2f} m</text><text x="25" y="55" font-size="14">Bloques = longitud reservada (incluye corte). No representa fase de ondas ni retales diagonales.</text><text x="25" y="78" font-size="13">IDs coinciden con el modelo CAD. No es una orden de corte definitiva.</text>']
    for i,b in enumerate(rows):
        y=100+i*66;x=x0
        a.append(f'<text x="20" y="{y+22}" font-size="14">L{i+1:02}</text><rect x="{x0}" y="{y}" width="{span}" height="35" fill="#e5e7e8" stroke="#808080"/>')
        for ident,l in b["pieces"]:
            width=l/stock*span
            a.append(f'<rect x="{x:.3f}" y="{y}" width="{width:.3f}" height="35" fill="{colors.get(ident.split("_")[0],"#627d8d")}" stroke="white"/>')
            # Labels below minimum width are in the separate spreadsheet.
            if width>=62:
                a.append(f'<text x="{x+width/2:.3f}" y="{y+15}" text-anchor="middle" fill="white" font-size="10">{html.escape(ident)}</text><text x="{x+width/2:.3f}" y="{y+28}" text-anchor="middle" fill="white" font-size="10">{l:.3f}m</text>')
            x+=width
        a.append(f'<text x="{x0}" y="{y+51}" font-size="11">Usado {b["used"]:.3f} m | Sobrante {stock-b["used"]:.3f} m</text>')
    a.append("</g></svg>");path.write_text("".join(a),encoding="utf-8")
def audit(data,roofs,stock):
    row=next(r for r in data["options"] if r["roof"]=="GLOBAL" and abs(r["stock_m"]-stock)<1e-8)
    if "error" in row:raise ValueError(row["error"])
    ids={q["id"]:q["length"] for r in roofs for q in r["sheets"]}
    seen=set()
    for b in row["bins"]:
        if not math.isclose(sum(v for _,v in b["pieces"]),b["used"],abs_tol=1e-7) or b["used"]>stock+1e-7:raise ValueError("Stock balance")
        for ident,l in b["pieces"]:
            if ident not in ids or ident in seen or l<ids[ident]-1e-7:raise ValueError("Piece assignment")
            seen.add(ident)
    if seen!=set(ids):raise ValueError("Incomplete study")
    return row
def main():
    p=argparse.ArgumentParser();p.add_argument("--project",type=pathlib.Path);p.add_argument("--study",type=pathlib.Path);p.add_argument("--stock",type=float,default=11.8);p.add_argument("--selftest",action="store_true");a=p.parse_args()
    if a.selftest:
        roofs=[{"sheets":[{"id":"T2_S_P01","length":2.0}]}];d={"options":[{"roof":"GLOBAL","stock_m":5.9,"bins":[{"used":2.003,"pieces":[["T2_S_P01",2.003]]}]}]}
        r=audit(d,roofs,5.9)
        with tempfile.TemporaryDirectory() as t:
            path=pathlib.Path(t)/"cut.svg";make_svg(r["bins"],5.9,path);assert "T2_S_P01" in path.read_text()
        print("ROOF DOCUMENT SELFTEST OK");return
    if not a.project or not a.study:p.error("project and study required")
    project=a.project.resolve();study=a.study.resolve()
    if not study.is_relative_to(project):p.error("Study must be inside project")
    roofs=json.loads((project/"roof_data.json").read_text(encoding="utf-8"))
    data=json.loads((study/"stock_comparison.json").read_text(encoding="utf-8"));row=audit(data,roofs,a.stock)
    out=pathlib.Path(tempfile.mkdtemp(prefix="engineering-doc-",dir=project))
    make_svg(row["bins"],a.stock,out/"plan_cortes.svg")
    payload={"source":str(project/"demo.FCStd"),"stock":a.stock,"row":row,"roofs":roofs}
    (out/"document_data.json").write_text(json.dumps(payload),encoding="utf-8")
    script="""import FreeCAD as App, pathlib, json
out=pathlib.Path(__file__).parent
d=json.loads((out/'document_data.json').read_text())
doc=App.openDocument(d['source'])
sheet=doc.addObject('Spreadsheet::Sheet','CutSchedule')
sheet.Label='Despiece longitudinal provisional'
for i,h in enumerate(['Lamina','Pieza CAD','Reserva mm','Inicio mm','Fin mm']):
    sheet.set(chr(65+i)+'1',h)
row=2
for n,b in enumerate(d['row']['bins'],1):
    offset=0
    for ident,l in b['pieces']:
        for i,v in enumerate([n,ident,round(l*1000,2),round(offset*1000,2),round((offset+l)*1000,2)]):
            sheet.set(chr(65+i)+str(row),str(v))
        offset+=l;row+=1
sheet.set('G1','PRELIMINAR - no incluye fase de onda ni remates')
sheet.set('G2','Longitud comercial mm');sheet.set('H2',str(d['stock']*1000))
sheet.set('G3','Laminas comerciales');sheet.set('H3',str(len(d['row']['bins'])))
for col,width in [('A',100),('B',160),('C',120),('D',120),('E',120),('G',360)]:
    sheet.setColumnWidth(col,width)
doc.recompute()
doc.saveAs(str(out/'cubiertas_documentadas.FCStd'))
assert (out/'cubiertas_documentadas.FCStd').stat().st_size>0
"""
    macro=out/"freecad_document.py";macro.write_text(script,encoding="utf-8")
    exe=locate("freecad")
    if not exe:raise SystemExit("FreeCAD no encontrado")
    with (out/"freecad.log").open("w",encoding="utf-8") as log:
        result=subprocess.run([exe,str(macro)],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=240)
    ok=result.returncode==0 and (out/"cubiertas_documentadas.FCStd").is_file()
    print(json.dumps({"ok":ok,"folder":str(out),"stock":a.stock,"sheets":len(row["bins"]),"pieces":sum(len(b["pieces"]) for b in row["bins"])}))
    if not ok:sys.exit(1)
if __name__=="__main__":main()
