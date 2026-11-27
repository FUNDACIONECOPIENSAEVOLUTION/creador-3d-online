"""Build timber solids in FreeCAD, then tessellate the same solids for Blender."""
import argparse,json,math,pathlib,subprocess,sys,tempfile,os,csv
from agent_v04 import locate
def frame(roofs):
    out=[]
    for r in roofs:
        name=r["id"]; edges={}
        for f in r["faces"]:
            vs=f["vertices"]
            for a,b in zip(vs,vs[1:]+vs[:1]):
                if math.dist(a,b)<1e-7:continue
                key=tuple(sorted(tuple(round(v,7) for v in p) for p in (a,b)))
                edges[key]=(a,b)
        for i,(a,b) in enumerate(edges.values(),1):
            kind="alero" if abs(a[2])+abs(b[2])<1e-7 else "cumbrera" if abs(a[2]-b[2])<1e-7 else "limatesa"
            out.append(dict(id=f"{name}_WMAIN_{i:02}",kind=kind,a=a,b=b,width=100,depth=100,length=math.dist(a,b)*1000))
        for q in r["wood"]:
            a,b=q["vertices"]
            out.append(dict(id=q["id"],kind="secundaria",a=a,b=b,width=50,depth=100,length=math.dist(a,b)*1000))
    return out
CAD="""import FreeCAD as App,Part,json,pathlib,math
out=pathlib.Path(__file__).parent
doc=App.newDocument('RoofFrame')
groups={}; meshes=[]; objs=[]
for q in json.loads((out/'frame.json').read_text()):
    roof=q['id'].split('_')[0]
    key=roof+('_Secundaria' if q['kind']=='secundaria' else '_Principal')
    if key not in groups:groups[key]=doc.addObject('App::DocumentObjectGroup',key)
    a,b=[App.Vector(*[1000*c for c in q[k]]) for k in ('a','b')]
    axis=b-a; L=axis.Length; axis.normalize()
    cross=App.Vector(-axis.y,axis.x,0);cross.normalize()
    down=cross.cross(axis);down.normalize()
    if down.z>0:down=-down
    w=q['width'];h=q['depth']
    corners=[a-cross*w/2,a+cross*w/2,a+cross*w/2+down*h,a-cross*w/2+down*h]
    shape=Part.Face(Part.makePolygon(corners+[corners[0]])).extrude(b-a)
    assert shape.isValid() and len(shape.Solids)==1
    assert abs(shape.Volume-L*w*h)<max(1,L*w*h*1e-7)
    ob=doc.addObject('Part::Feature',q['id']);ob.Shape=shape;groups[key].addObject(ob);objs.append(ob)
    for prop,val in [('WidthMM',w),('DepthMM',h),('LengthMM',L)]:
        ob.addProperty('App::PropertyLength',prop,'EcoBlend');setattr(ob,prop,val)
    ob.addProperty('App::PropertyString','MemberType','EcoBlend');ob.MemberType=q['kind']
    v,f=shape.tessellate(.5)
    meshes.append(dict(id=q['id'],kind=q['kind'],vertices=[[p.x/1000,p.y/1000,p.z/1000] for p in v],faces=f,volume_mm3=shape.Volume))
doc.recompute();doc.saveAs(str(out/'demo.FCStd'));Part.export(objs,str(out/'demo.step'))
(out/'cad_mesh.json').write_text(json.dumps(meshes),encoding='utf-8')
"""
BLENDER="""import bpy,json,pathlib
out=pathlib.Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(name,col):
    m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*col,1);b.inputs['Roughness'].default_value=.65
    return m
main=mat('Madera principal 100x100',(.24,.09,.025))
sec=mat('Madera secundaria 50x100',(.58,.29,.10))
for q in json.loads((out/'cad_mesh.json').read_text()):
    m=bpy.data.meshes.new(q['id']);m.from_pydata(q['vertices'],[],q['faces']);m.update()
    ob=bpy.data.objects.new(q['id'],m);bpy.context.collection.objects.link(ob);m.materials.append(sec if q['kind']=='secundaria' else main)
    ob['source']='FreeCAD solid';ob['volume_mm3']=q['volume_mm3']
bpy.ops.wm.save_as_mainfile(filepath=str(out/'demo.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'demo.glb'),export_format='GLB',export_extras=True)
"""
def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=pathlib.Path);p.add_argument('--selftest',action='store_true');a=p.parse_args()
    if a.selftest:
        from roof_engine_v099 import build
        r=build({"pitch":.35,"useful_width":.96,"spacing":.8,"stock":11.8,"roofs":[{"id":"T9","width":8,"depth":6,"x":0,"y":0}]})
        q=frame(r);assert len([v for v in q if v['kind']!='secundaria'])==9
        assert len([v for v in q if v['kind']=='secundaria'])==34
        assert all(v['length']>0 for v in q)
        compile(CAD,'cad','exec');compile(BLENDER,'blender','exec')
        print('FRAME SELFTEST OK');return
    if not a.project:p.error('project required')
    src=a.project.resolve();r=json.loads((src/'roof_data.json').read_text(encoding='utf-8'));q=frame(r)
    out=pathlib.Path(tempfile.mkdtemp(prefix='job-',dir=src.parent))
    (out/'frame.json').write_text(json.dumps(q),encoding='utf-8')
    (out/'roof_data.json').write_text(json.dumps(r),encoding='utf-8')
    (out/'studio_project.json').write_text(json.dumps({'name':'Cubiertas | esqueleto CAD maestro','state':'active'}),encoding='utf-8')
    with (out/'madera.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter=';');w.writerow(['ID','Tipo','Ancho mm','Altura mm','Longitud eje mm'])
        for v in q:w.writerow([v['id'],v['kind'],v['width'],v['depth'],round(v['length'],2)])
    for engine,code,files in [('freecad',CAD,['demo.FCStd','demo.step','cad_mesh.json']),('blender',BLENDER,['demo.blend','demo.glb'])]:
        exe=locate(engine)
        if not exe:raise RuntimeError(engine+' no disponible')
        macro=out/(engine+'_frame.py');macro.write_text(code,encoding='utf-8')
        cmd=[exe] if engine=='freecad' else [exe,'--background','--threads','2','--factory-startup','--disable-autoexec','--python-exit-code','1','--python']
        with (out/(engine+'.log')).open('w',encoding='utf-8') as log:
            p=subprocess.run(cmd+[str(macro)],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=240)
        if p.returncode or not all((out/f).is_file() and (out/f).stat().st_size for f in files):raise RuntimeError('Error '+engine+'; consulte '+str(out))
    summary={k:dict(count=sum(v['kind']==k for v in q),meters=round(sum(v['length'] for v in q if v['kind']==k)/1000,3)) for k in ('alero','cumbrera','limatesa','secundaria')}
    print(json.dumps(dict(ok=True,folder=str(out),summary=summary,limitations='Nominal axis lengths; no joint trimming or structural assessment')))
if __name__=='__main__':main()
