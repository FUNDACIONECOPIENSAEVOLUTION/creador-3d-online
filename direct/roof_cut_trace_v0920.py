"""Traceable conservative linear cutting plans; no unverified diagonal reuse."""
import argparse,csv,json,math,pathlib,html
from roof_mount_v0914 import prepare
def plan(pieces,stock,kerf=.003):
    bins=[]
    for q in sorted(pieces,key=lambda x:(-x['length'],x['id'])):
        length=math.ceil(q['length']*1000-1e-7)/1000
        need=length+kerf
        if need>stock+1e-9:raise ValueError("Piece too long "+q['id'])
        candidates=[b for b in bins if b['remaining']>=need-1e-9]
        if candidates:b=min(candidates,key=lambda b:b['remaining'])
        else:
            b=dict(id=f"L{len(bins)+1:03}",remaining=stock,cuts=[]);bins.append(b)
        start=stock-b['remaining']
        b['cuts'].append(dict(piece=q['id'],start_m=round(start,6),end_m=round(start+length,6),length_m=length,kerf_m=kerf,width_m=q['width'],overlap_m=q['overlap'],roof_vertices_m=q['vertices']))
        b['remaining']=round(b['remaining']-need,9)
    for b in bins:
        b['offcut_id']=b['id']+'-R';b['offcut_length_m']=b['remaining']
    assert sorted(c['piece'] for b in bins for c in b['cuts'])==sorted(q['id'] for q in pieces)
    return dict(stock_m=stock,count=len(bins),purchased_m=round(stock*len(bins),3),remaining_m=round(sum(b['remaining'] for b in bins),3),bins=bins)
def generate(roofs,out):
    pieces,_=prepare(roofs);options=[plan(pieces,s) for s in (11.8,5.9,5.8)]
    result=dict(options=options,limitations="Best-fit decreasing full-width longitudinal blanks; no diagonal offcut reuse, no profile phase certification, no mixed lengths or exact optimum. 3 mm assumed kerf.")
    (out/'cut_plan.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with (out/'cut_plan.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter=';');w.writerow(['Stock m','Lamina','Pieza','Inicio m','Fin m','Largo m','Ancho m','Traslape m','Sobrante lamina m'])
        for o in options:
            for b in o['bins']:
                for c in b['cuts']:w.writerow([o['stock_m'],b['id'],c['piece'],c['start_m'],c['end_m'],c['length_m'],c['width_m'],c['overlap_m'],b['remaining']])
    lines=['<html lang="es"><meta charset="utf-8"><title>EcoBlend cortes</title><style>body{font:14px system-ui;margin:24px}svg{width:100%;max-width:1100px}section{break-inside:avoid}</style><h1>Plan de corte longitudinal preliminar</h1><p>'+html.escape(result['limitations'])+'</p>']
    for o in options:
        lines.append(f"<h2>{o['stock_m']} m | {o['count']} laminas | sobrante lineal {o['remaining_m']} m</h2>")
        for b in o['bins']:
            scale=900/o['stock_m'];lines.append(f'<section><b>{b["id"]}</b><svg viewBox="0 0 920 48"><rect x="0" y="0" width="900" height="28" fill="#ddd"/>')
            for i,c in enumerate(b['cuts']):
                x=c['start_m']*scale;w=c['length_m']*scale
                lines.append(f'<rect x="{x}" y="0" width="{w}" height="28" fill="{["#e98c43","#95bf76"][i%2]}" stroke="#444"/><text x="{x+2}" y="12" font-size="8">{html.escape(c["piece"])}</text><text x="{x+2}" y="24" font-size="8">{c["length_m"]} m</text>')
            lines.append(f'</svg><p>{b["offcut_id"]}: {b["remaining"]:.3f} m</p></section>')
    (out/'cut_plan.html').write_text(''.join(lines),encoding='utf-8')
    return [{k:v for k,v in o.items() if k!='bins'} for o in options]
def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=pathlib.Path);p.add_argument('--selftest',action='store_true');a=p.parse_args()
    if a.selftest:
        q=[dict(id=str(i),length=2.9,width=1.05,overlap=.09,vertices=[]) for i in range(4)]
        assert plan(q,11.8)['count']==1 and plan(q,5.9)['count']==2 and plan(q,5.8)['count']==4
        print('TRACEABLE CUT SELFTEST OK');return
    if not a.project:p.error('project required')
    import tempfile
    out=pathlib.Path(tempfile.mkdtemp(prefix='cut-plan-',dir=a.project))
    print(json.dumps(dict(folder=str(out),options=generate(json.loads((a.project/'roof_data.json').read_text()),out))))
if __name__=='__main__':main()
