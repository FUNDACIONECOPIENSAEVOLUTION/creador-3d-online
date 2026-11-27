"""Reusable provisional colonial profile, clipped in CAD coordinates.
Profile dimensions are illustrative until a manufacturer's section is measured."""
import argparse,json,math,pathlib,sqlite3,subprocess,tempfile,sys
from agent_v04 import locate
from roof_mount_v0914 import prepare,BLENDER
from roof_stock_v0910 import pack
def clip(poly,axis,bound,sign):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=sign*(a[axis]-bound);db=sign*(b[axis]-bound)
        if da>=-1e-9:out.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);out.append(tuple(a[i]+t*(b[i]-a[i]) for i in range(2)))
    clean=[]
    for p in out:
        if not clean or math.dist(p,clean[-1])>1e-8:clean.append(p)
    if len(clean)>1 and math.dist(clean[0],clean[-1])<1e-8:clean.pop()
    return clean
def profile(roofs,wave=.192,height=.035,step=.35,step_height=.008):
    if not (.06<=wave<=.5 and .005<=height<=.08 and .1<=step<=.6 and 0<=step_height<=.03):raise ValueError("profile bounds")
    tiles,elevations=prepare(roofs);by={r['id']:r for r in roofs}
    for q in tiles:
        rid,side,_=q['id'].split('_');r=by[rid];w,d,x,y=[r[k] for k in ('width','depth','x','y')]
        p=max(v[2] for f in r['faces'] for v in f['vertices'])/(min(w,d)/2);k=math.hypot(1,p)
        def ab(v):
            X,Y=v[0]-x,v[1]-y
            return {'S':(X,Y),'N':(w-X,d-Y),'W':(d-Y,X),'E':(Y,w-X)}[side]
        def xyz(a,b,z):
            X,Y={'S':(a,b),'N':(w-a,d-b),'W':(b,d-a),'E':(w-b,a)}[side]
            return [x+X,y+Y,b*p+z]
        poly=[ab(v) for v in q['vertices']];lo=min(a for a,b in poly);hi=max(a for a,b in poly);top=max(b for a,b in poly)
        # Global phase keeps overlapping profiles aligned when useful width is a multiple of wave pitch.
        dx=wave/6;dy=step/(k*3)
        def z(a,b):return .004+height*(.5-.5*math.cos(2*math.pi*a/wave)) + step_height*((b*k/step)%1) + q['color']*.003
        vs=[];fs=[];index={}
        for i in range(math.floor(lo/dx),math.ceil(hi/dx)):
            strip=clip(clip(poly,0,i*dx,1),0,(i+1)*dx,-1)
            if len(strip)<3:continue
            for j in range(math.ceil(top/dy)):
                cell=clip(clip(strip,1,j*dy,1),1,(j+1)*dy,-1)
                if len(cell)<3:continue
                ids=[]
                for a,b in cell:
                    key=(round(a,9),round(b,9))
                    if key not in index:
                        index[key]=len(vs);vs.append(xyz(*key,z(*key)))
                    ids.append(index[key])
                for n in range(1,len(cell)-1):
                    a,b,c=cell[0],cell[n],cell[n+1]
                    if abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))>1e-10:fs.append([ids[0],ids[n],ids[n+1]])
        q['profile_vertices']=vs;q['profile_faces']=fs
        if not fs:raise ValueError("empty profile "+q['id'])
    return tiles,elevations
CAD="""import FreeCAD as App,Part,json,pathlib,Mesh
out=pathlib.Path(__file__).parent
data=json.loads((out/'input.json').read_text())
doc=App.openDocument(data['source']);meshes=[];groups={}
print('CAD opened',flush=True)
for ob in doc.Objects:
    if not hasattr(ob,'Shape') or ob.Shape.isNull():continue
    assert ob.Shape.isValid() and len(ob.Shape.Solids)==1
    v,f=ob.Shape.tessellate(.5)
    meshes.append(dict(id=ob.Name,kind=str(ob.MemberType),vertices=[[p.x/1000,p.y/1000,p.z/1000] for p in v],faces=f))
assert len(meshes)==data['wood_count']
for q in data['tiles']:
    print('CAD tile '+q['id'],flush=True)
    roof=q['id'].split('_')[0]
    if roof not in groups:groups[roof]=doc.addObject('App::DocumentObjectGroup',roof+'_Tejas')
    v=[App.Vector(*[1000*c for c in p]) for p in q['vertices']]
    shape=Part.Face(Part.makePolygon(v+[v[0]])).extrude(App.Vector(0,0,2.0))
    assert shape.isValid()
    ob=doc.addObject('Part::Feature',q['id']+'_Cut');ob.Shape=shape;groups[roof].addObject(ob)
    for key,val in [('CutLength',q['length']),('PanelWidth',q['width']),('SideOverlap',q['overlap'])]:
        ob.addProperty('App::PropertyLength',key,'EcoBlend');setattr(ob,key,val*1000)
    pv=[App.Vector(*[1000*c for c in p]) for p in q['profile_vertices']]
    m=doc.addObject('Mesh::Feature',q['id']);m.Mesh=Mesh.Mesh([[tuple(pv[i]) for i in f] for f in q['profile_faces']]);groups[roof].addObject(m)
    # Use the same CAD mesh vertices/facets in Blender, not a second roof construction.
    meshes.append(dict(id=q['id'],kind='tile',color=q['color'],vertices=q['profile_vertices'],faces=q['profile_faces']))
    if App.GuiUp:
        ob.ViewObject.Visibility=False;m.ViewObject.ShapeColor=(.8,.25,.08) if q['color']==0 else (.5,.8,.3)
doc.recompute();doc.saveAs(str(out/'demo.FCStd'))
(out/'cad_mesh.json').write_text(json.dumps(meshes),encoding='utf-8')
"""
def register(root,out,src,report):
    db=root/'ecoblend_catalog.sqlite3'
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE IF NOT EXISTS revisions(id TEXT PRIMARY KEY,parent TEXT,module TEXT,status TEXT,report TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)')
        c.execute('INSERT INTO revisions(id,parent,module,status,report) VALUES(?,?,?,?,?)',(out.name,src.name,'colonial-profile','generated',json.dumps(report)))
def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=pathlib.Path);p.add_argument('--selftest',action='store_true');a=p.parse_args()
    if a.selftest:
        from roof_engine_v099 import build
        r=build({'pitch':.35,'useful_width':.96,'spacing':.8,'stock':11.8,'roofs':[{'id':'T9','width':3,'depth':2,'x':0,'y':0}]})
        t,e=profile(r);assert t and all(q['profile_faces'] for q in t);assert e[0]['rise_mm']==350
        assert all(q['width']<=1.05+1e-8 for q in t)
        compile(CAD,'cad','exec');compile(BLENDER,'blender','exec')
        print('COLONIAL PROFILE SELFTEST OK');return
    if not a.project:p.error('project required')
    src=a.project.resolve();roofs=json.loads((src/'roof_data.json').read_text());wood=json.loads((src/'frame.json').read_text())
    tiles,elevations=profile(roofs);out=pathlib.Path(tempfile.mkdtemp(prefix='job-',dir=src.parent))
    (out/'input.json').write_text(json.dumps(dict(source=str(src/'demo.FCStd'),tiles=tiles,wood_count=len(wood))),encoding='utf-8')
    for name in ('roof_data.json','frame.json'):(out/name).write_bytes((src/name).read_bytes())
    for engine,code,files in [('freecad',CAD,['demo.FCStd','cad_mesh.json']),('blender',BLENDER,['demo.blend','demo.glb'])]:
        exe=locate(engine)
        if not exe:raise RuntimeError(engine+' unavailable')
        macro=out/(engine+'_profile.py')
        if engine=='freecad':
            code='import traceback\ntry:\n'+''.join('    '+line+'\n' for line in code.splitlines())+'except BaseException:\n    traceback.print_exc()\n    raise\n'
        macro.write_text(code,encoding='utf-8')
        cmd=[exe] if engine=='freecad' else [exe,'--background','--threads','2','--factory-startup','--disable-autoexec','--python-exit-code','1','--python']
        with (out/(engine+'.log')).open('w',encoding='utf-8') as log:
            r=subprocess.run(cmd+[str(macro)],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=480)
        if r.returncode or not all((out/f).is_file() and (out/f).stat().st_size for f in files):raise RuntimeError(engine+' failed: '+str(out)+'; returncode='+str(r.returncode)+'; missing='+str([f for f in files if not (out/f).is_file()]))
    options=[]
    for size in (11.8,5.9,5.8):
        b=pack(tiles,size);options.append(dict(stock=size,count=len(b),unused_m=round(size*len(b)-sum(v['used'] for v in b),3)))
    report=dict(ok=True,folder=str(out),wood=len(wood),tiles=len(tiles),elevations=elevations,stock=options,profile=dict(wave_m=.192,height_m=.035,step_m=.35,step_height_m=.008,thickness_m=.002,status='illustrative'),limitations='CAD cut solids plus separate profiled meshes; not manufacturer geometry or verified structural contact')
    (out/'profile_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (out/'studio_project.json').write_text(json.dumps(dict(name='Cubiertas | perfil colonial 2 mm provisional',state='active')),encoding='utf-8')
    register(src.parent,out,src,report);print(json.dumps(report))
if __name__=='__main__':main()
