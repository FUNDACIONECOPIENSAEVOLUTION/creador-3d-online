"""Mount individually identified tiles onto the validated native FreeCAD frame."""
import argparse,json,math,pathlib,subprocess,sys,tempfile
from agent_v04 import locate
from roof_assembly_v0912 import assembly
from roof_stock_v0910 import pack
def prepare(roofs):
    tiles=[q for q in assembly(roofs) if q["kind"]=="tile"]
    report=[]
    for r in roofs:
        h=min(r["width"],r["depth"])/2
        rise=max(v[2] for f in r["faces"] for v in f["vertices"])
        report.append(dict(id=r["id"],rise_mm=round(rise*1000,3),pitch_pct=round(100*rise/h,4),angle_deg=round(math.degrees(math.atan(rise/h)),5)))
    return tiles,report
CAD="""import FreeCAD as App,Part,json,pathlib
out=pathlib.Path(__file__).parent
data=json.loads((out/'mount_input.json').read_text())
doc=App.openDocument(data['source'])
groups={}; meshes=[]; objs=[]
for ob in doc.Objects:
    if not hasattr(ob,'Shape') or ob.Shape.isNull():continue
    assert ob.Shape.isValid() and len(ob.Shape.Solids)==1
    v,f=ob.Shape.tessellate(.5)
    meshes.append(dict(id=ob.Name,kind=str(ob.MemberType),vertices=[[p.x/1000,p.y/1000,p.z/1000] for p in v],faces=f))
    objs.append(ob)
assert len(objs)==data['wood_count']
for q in data['tiles']:
    roof=q['id'].split('_')[0]
    if roof not in groups:groups[roof]=doc.addObject('App::DocumentObjectGroup',roof+'_Tejas')
    v=[App.Vector(*[1000*c for c in p]) for p in q['vertices']]
    shape=Part.Face(Part.makePolygon(v+[v[0]])).extrude(App.Vector(0,0,2.5))
    assert shape.isValid() and len(shape.Solids)==1
    ob=doc.addObject('Part::Feature',q['id']);ob.Shape=shape;groups[roof].addObject(ob);objs.append(ob)
    for name,val in [('CutLength',q['length']),('PanelWidth',q['width']),('SideOverlap',q['overlap'])]:
        ob.addProperty('App::PropertyLength',name,'EcoBlend');setattr(ob,name,val*1000)
    v,f=shape.tessellate(.5)
    meshes.append(dict(id=ob.Name,kind='tile',color=q['color'],vertices=[[p.x/1000,p.y/1000,p.z/1000] for p in v],faces=f))
sheet=doc.addObject('Spreadsheet::Sheet','RoofElevations')
for i,h in enumerate(['Cubierta','Elevacion mm','Pendiente %','Angulo grados']):
    sheet.set(chr(65+i)+'1',h)
for n,r in enumerate(data['elevations'],2):
    for i,k in enumerate(['id','rise_mm','pitch_pct','angle_deg']):sheet.set(chr(65+i)+str(n),str(r[k]))
doc.recompute();doc.saveAs(str(out/'demo.FCStd'));Part.export(objs,str(out/'demo.step'))
(out/'cad_mesh.json').write_text(json.dumps(meshes),encoding='utf-8')
"""
BLENDER="""import bpy,json,pathlib
out=pathlib.Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(name,col,alpha=1):
    m=bpy.data.materials.new(name);m.diffuse_color=(*col,alpha);m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*col,1);b.inputs['Alpha'].default_value=alpha;b.inputs['Roughness'].default_value=.55
    if alpha<1:m.surface_render_method='DITHERED'
    return m
main=mat('Madera principal',(.24,.09,.025));sec=mat('Madera secundaria',(.58,.29,.10))
tiles=[mat('UPVC naranja',(.82,.23,.07),.52),mat('UPVC verde',(.48,.82,.30),.52)]
groups={}
for q in json.loads((out/'cad_mesh.json').read_text()):
    key=q['id'].split('_')[0]+('_Tejas' if q['kind']=='tile' else '_Madera')
    if key not in groups:
        groups[key]=bpy.data.collections.new(key);bpy.context.scene.collection.children.link(groups[key])
    m=bpy.data.meshes.new(q['id']);m.from_pydata(q['vertices'],[],q['faces']);m.update()
    ob=bpy.data.objects.new(q['id'],m);groups[key].objects.link(ob)
    m.materials.append(tiles[q['color']] if q['kind']=='tile' else sec if q['kind']=='secundaria' else main)
    ob['source']='FreeCAD solid'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'demo.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'demo.glb'),export_format='GLB',export_extras=True)
"""
def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=pathlib.Path);p.add_argument('--selftest',action='store_true');a=p.parse_args()
    if a.selftest:
        from roof_engine_v099 import build
        r=build({"pitch":.35,"useful_width":.96,"spacing":.8,"stock":11.8,"roofs":[{"id":"T9","width":8,"depth":6,"x":0,"y":0}]})
        t,e=prepare(r);assert e[0]['rise_mm']==1050 and len(t)==32
        assert all(q['width']<=1.05+1e-8 for q in t)
        compile(CAD,'cad','exec');compile(BLENDER,'blender','exec')
        print('CAD MOUNT SELFTEST OK');return
    if not a.project:p.error('project required')
    src=a.project.resolve();roofs=json.loads((src/'roof_data.json').read_text());wood=json.loads((src/'frame.json').read_text())
    tiles,elevations=prepare(roofs)
    out=pathlib.Path(tempfile.mkdtemp(prefix='job-',dir=src.parent))
    options=[]
    for size in (11.8,5.9,5.8):
        try:
            b=pack(tiles,size);options.append(dict(stock=size,count=len(b),unused_m=round(size*len(b)-sum(v['used'] for v in b),3)))
        except ValueError as e:options.append(dict(stock=size,error=str(e)))
    (out/'mount_input.json').write_text(json.dumps(dict(source=str(src/'demo.FCStd'),tiles=tiles,wood_count=len(wood),elevations=elevations)),encoding='utf-8')
    (out/'roof_data.json').write_text(json.dumps(roofs),encoding='utf-8')
    (out/'frame.json').write_text(json.dumps(wood),encoding='utf-8')
    for engine,code,files in [('freecad',CAD,['demo.FCStd','demo.step','cad_mesh.json']),('blender',BLENDER,['demo.blend','demo.glb'])]:
        exe=locate(engine)
        if not exe:raise RuntimeError(engine+' unavailable')
        macro=out/(engine+'_mount.py');macro.write_text(code,encoding='utf-8')
        cmd=[exe] if engine=='freecad' else [exe,'--background','--threads','2','--factory-startup','--disable-autoexec','--python-exit-code','1','--python']
        with (out/(engine+'.log')).open('w',encoding='utf-8') as log:
            r=subprocess.run(cmd+[str(macro)],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=240)
        if r.returncode or not all((out/f).is_file() and (out/f).stat().st_size for f in files):raise RuntimeError(engine+' failed: '+str(out))
    report=dict(ok=True,folder=str(out),wood=len(wood),tiles=len(tiles),elevations=elevations,stock=options,limitations='Flat panel approximation, lateral overlap assumed; no structural or joint verification')
    (out/'mount_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (out/'studio_project.json').write_text(json.dumps(dict(name='Cubiertas | CAD madera y tejas',state='active')),encoding='utf-8')
    print(json.dumps(report))
if __name__=='__main__':main()
