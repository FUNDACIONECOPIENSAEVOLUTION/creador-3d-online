"""Generic polygonal roof facet framing in local metres; explicit slope vector and elevation.
No inference of surveyed dimensions. Supports concave facets by line interval clipping."""
import argparse,json,math,pathlib,subprocess,tempfile
from agent_v04 import locate
from roof_frame_v0913 import CAD,BLENDER
def build(spec):
    result=[];edges={};names=set()
    for f in spec['facets']:
        name=f['id']
        import re
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,39}',name) or name in names:raise ValueError('Facet ID')
        names.add(name)
        poly=f['polygon'];gx,gy=f['gradient'];z0=f['z0'];spacing=f.get('spacing',.8)
        if not 3<=len(poly)<=300 or not all(len(v)==2 and all(math.isfinite(c) for c in v) for v in poly):raise ValueError('Polygon')
        slope=math.hypot(gx,gy)
        if not .05<=slope<=1 or not .3<=spacing<=1.5:raise ValueError('Slope/spacing')
        u=(gx/slope,gy/slope);v=(-u[1],u[0])
        def dot(a,b):return sum(x*y for x,y in zip(a,b))
        def xyz(p):return [*p,z0+dot(p,(gx,gy))]
        def point(a,b):return xyz([u[0]*a+v[0]*b,u[1]*a+v[1]*b])
        def member(id,kind,a,b,w):
            length=math.dist(a,b)*1000
            if length>1e-4:result.append(dict(id=id,kind=kind,a=a,b=b,width=w,depth=100,length=length))
        for a,b in zip(poly,poly[1:]+poly[:1]):
            a,b=xyz(a),xyz(b);key=tuple(sorted(tuple(round(c,6) for c in p) for p in (a,b)))
            if key not in edges:
                edges[key]=name;member(name+'_WMAIN_'+str(len(edges)),'borde',a,b,100)
        ab=[(dot(p,u),dot(p,v)) for p in poly];lo=min(b for a,b in ab);hi=max(b for a,b in ab)
        n=0;t=lo+spacing/2
        while t<hi-1e-8:
            hits=[]
            for (a,b),(c,d) in zip(ab,ab[1:]+ab[:1]):
                if min(b,d)<=t<max(b,d):hits.append(a+(c-a)*(t-b)/(d-b))
            hits.sort()
            if len(hits)%2:raise ValueError('Invalid polygon intersections '+name)
            for a,b in zip(hits[::2],hits[1::2]):
                n+=1;member(name+'_W'+str(n).zfill(3),'secundaria',point(a,t),point(b,t),50)
            t+=spacing
    if not result or len(result)>3000:raise ValueError('Member count')
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=pathlib.Path);p.add_argument('--selftest',action='store_true');a=p.parse_args()
    if a.selftest:
        q=build(dict(facets=[dict(id='F1',polygon=[[0,0],[4,0],[4,2],[2,2],[2,4],[0,4]],gradient=[.35,0],z0=0)]))
        assert len(q)>6 and all(x['length']>0 for x in q)
        compile(CAD,'cad','exec');compile(BLENDER,'blender','exec')
        print('POLYGON FRAME SELFTEST OK');return
    if not a.spec:p.error('spec required')
    spec=json.loads(a.spec.read_text(encoding='utf-8-sig'))
    import os
    root=pathlib.Path(os.environ['ECOBLEND_PROJECTS']);out=pathlib.Path(tempfile.mkdtemp(prefix='job-',dir=root))
    q=build(spec);(out/'frame.json').write_text(json.dumps(q),encoding='utf-8')
    (out/'facet_spec.json').write_text(json.dumps(spec),encoding='utf-8')
    for engine,code,files in [('freecad',CAD,['demo.FCStd','demo.step','cad_mesh.json']),('blender',BLENDER,['demo.blend','demo.glb'])]:
        exe=locate(engine)
        if not exe:raise RuntimeError(engine+' unavailable')
        macro=out/(engine+'_polygon.py');macro.write_text(code,encoding='utf-8')
        cmd=[exe] if engine=='freecad' else [exe,'--background','--threads','2','--factory-startup','--disable-autoexec','--python-exit-code','1','--python']
        with (out/(engine+'.log')).open('w',encoding='utf-8') as log:
            r=subprocess.run(cmd+[str(macro)],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=480)
        if r.returncode or not all((out/f).is_file() and (out/f).stat().st_size for f in files):raise RuntimeError(engine+' failed '+str(out))
    (out/'studio_project.json').write_text(json.dumps(dict(name='Cubierta irregular | estructura preliminar',state='active')),encoding='utf-8')
    print(json.dumps(dict(ok=True,folder=str(out),members=len(q),status='preliminary')))
if __name__=='__main__':main()
