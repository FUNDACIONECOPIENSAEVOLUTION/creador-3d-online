"""EcoBlend Reality v0.6. Local photo/material mapping for v0.5 rectangular architecture.
Uses explicit world-space UV projection, never uploads images. Creates a new revision.
"""
import argparse, json, math, pathlib, tempfile, subprocess, sys, shutil, re, struct, zlib
from agent_v04 import locate
from architecture_v05 import build
ROOT=pathlib.Path(__file__).resolve().parent.parent/"projects"
IDS=("F01","F02","F03","F04","P01")
def uv(side,x,y,z,w,d,h,t,repeat=None):
    if side=="P01": return (x/(repeat or w),y/(repeat or d))
    if side=="F01": u,L=x,w
    elif side=="F02": u,L=w-x,w
    elif side=="F03": u,L=d-t-y,d-2*t
    else: u,L=y-t,d-2*t
    return (u/(repeat or L),z/(repeat or h))
def png(path,kind):
    n=256
    def pixel(x,y):
        if kind=="brick":
            mortar=y%32<3 or (x+(32 if (y//32)%2 else 0))%64<3
            base=(174,164,147) if mortar else (155+(x*13+y*7)%18,83+(x+y)%12,55+(x*3+y)%10)
        else:
            seam=x%64<2 or y%64<2
            base=(102,94,85) if seam else (186+(x*7+y*3)%12,176+(x+y)%12,160+(x+y)%9)
        return bytes(base)
    raw=b"".join(b"\0"+b"".join(pixel(x,y) for x in range(n)) for y in range(n))
    def chunk(k,v): return struct.pack(">I",len(v))+k+v+struct.pack(">I",zlib.crc32(k+v)&0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",n,n,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw))+chunk(b"IEND",b""))
def validate(mapping,base):
    if not isinstance(mapping,dict) or any(k not in IDS for k in mapping): raise ValueError("Superficie desconocida")
    result={}
    for k,v in mapping.items():
        if not isinstance(v,dict) or set(v)-{"image","normal","roughness_map","mode","repeat_m","roughness","source"} or "image" not in v: raise ValueError("Material invalido")
        mode=v.get("mode","facade")
        if mode not in ("facade","tile"): raise ValueError("Modo invalido")
        r=v.get("repeat_m",1); rough=v.get("roughness",.65)
        if type(r) not in (int,float) or not .05<=r<=100 or type(rough) not in (int,float) or not 0<=rough<=1: raise ValueError("Escala o rugosidad invalida")
        source=v.get("source","unspecified")
        if source not in ("photo","ai","synthetic","unspecified"): raise ValueError("Procedencia invalida")
        item=dict(mode=mode,repeat_m=r,roughness=rough,source=source)
        for name in ("image","normal","roughness_map"):
            if name not in v: continue
            p=(base/v[name]).resolve()
            if not p.is_relative_to(base.resolve()) or not p.is_file() or p.suffix.lower() not in (".png",".jpg",".jpeg") or p.stat().st_size>32*1024*1024: raise ValueError("Imagen local invalida: "+name)
            item[name]=str(p)
        result[k]=item
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument("--project");p.add_argument("--mapping",type=pathlib.Path);p.add_argument("--demo",action="store_true");p.add_argument("--selftest",action="store_true");a=p.parse_args()
    if a.selftest:
        assert uv("F01",4,0,1.4,8,6,2.8,.2)==(.5,.5)
        assert uv("F02",0,6,2.8,8,6,2.8,.2)==(1,1)
        assert abs(uv("F03",0,.2,0,8,6,2.8,.2)[0]-1)<1e-8
        with tempfile.TemporaryDirectory() as t:
            q=pathlib.Path(t);png(q/"test.png","brick")
            assert (q/"test.png").read_bytes().startswith(b"\x89PNG")
            assert validate({"F01":{"image":"test.png"}},q)["F01"]["mode"]=="facade"
            try: validate({"X":{"image":"test.png"}},q)
            except ValueError: pass
            else: raise AssertionError("ID invalido aceptado")
        print("SELFTEST OK: UV, PNG, materiales e IDs");return
    if a.demo==bool(a.mapping): p.error("Seleccione --demo o --mapping")
    if a.project:
        if not re.fullmatch(r"job-[A-Za-z0-9_-]+",a.project): p.error("ID invalido")
        src=ROOT/a.project
    else:
        candidates=[x for x in ROOT.glob("job-*") if (x/"surface_inventory.json").is_file() and (x/"demo.blend").is_file() and not (x/"reality_report.json").exists()]
        if not candidates: p.error("No hay proyecto arquitectonico v0.5")
        src=max(candidates,key=lambda x:(x/"surface_inventory.json").stat().st_mtime)
    if not src.resolve().is_relative_to(ROOT.resolve()): p.error("Proyecto invalido")
    inv=json.loads((src/"surface_inventory.json").read_text(encoding="utf-8")); spec=inv["spec"];pieces,_=build(spec)
    out=pathlib.Path(tempfile.mkdtemp(prefix="job-",dir=ROOT)); tex=out/"textures";tex.mkdir()
    if a.demo:
        png(tex/"brick.png","brick");png(tex/"floor.png","floor")
        mapping={k:{"image":"floor.png" if k=="P01" else "brick.png","mode":"tile","repeat_m":1,"source":"synthetic"} for k in IDS}
        materials=validate(mapping,tex)
    else:
        materials=validate(json.loads(a.mapping.read_text(encoding="utf-8-sig")),a.mapping.resolve().parent)
        for side,m in materials.items():
            for key in ("image","normal","roughness_map"):
                if key in m:
                    f=pathlib.Path(m[key]); target=tex/(side+"_"+key+f.suffix.lower());shutil.copy2(f,target);m[key]=str(target)
    for name in ("surface_inventory.json","surface_map.svg","demo.FCStd","demo.step"):
        if (src/name).is_file(): shutil.copy2(src/name,out/name)
    script=f"""import bpy, pathlib
from mathutils import Vector
out=pathlib.Path({str(out)!r})
bpy.ops.wm.open_mainfile(filepath={str(src/"demo.blend")!r},use_scripts=False)
materials={materials!r}
spec={spec!r}
w,d,h,t=[spec[k] for k in ('width','depth','height','wall')]
{uv_source}
mats={{}}
for side,m in materials.items():
    mat=bpy.data.materials.new('Reality_'+side);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF')
    bs.inputs['Roughness'].default_value=m['roughness']
    for key in ('image','normal','roughness_map'):
        if key not in m: continue
        img=bpy.data.images.load(m[key],check_existing=False)
        if max(img.size)>2048:
            scale=2048/max(img.size);img.scale(max(1,int(img.size[0]*scale)),max(1,int(img.size[1]*scale)))
        if key!='image': img.colorspace_settings.name='Non-Color'
        img.pack();node=nodes.new('ShaderNodeTexImage');node.image=img
        node.extension='REPEAT' if m['mode']=='tile' else 'EXTEND'
        uvnode=nodes.new('ShaderNodeUVMap');uvnode.uv_map='RealityUV';links.new(uvnode.outputs['UV'],node.inputs['Vector'])
        if key=='image': links.new(node.outputs['Color'],bs.inputs['Base Color'])
        elif key=='roughness_map': links.new(node.outputs['Color'],bs.inputs['Roughness'])
        else:
            norm=nodes.new('ShaderNodeNormalMap');links.new(node.outputs['Color'],norm.inputs['Color']);links.new(norm.outputs['Normal'],bs.inputs['Normal'])
    mats[side]=mat
counts={{k:0 for k in materials}}
for o in bpy.context.scene.objects:
    side=o.name.split('_')[0]
    if o.type!='MESH' or side not in mats: continue
    m=materials[side];mesh=o.data
    layer=mesh.uv_layers.active or mesh.uv_layers.new(name='RealityUV')
    layer.name='RealityUV'
    mesh.uv_layers.active=layer
    layer.active_render=True
    mesh.name=o.name
    o['surface_id']=side
    mesh.materials.append(mats[side]);idx=len(mesh.materials)-1
    for poly in mesh.polygons:
        n=poly.normal
        exterior={{'F01':n.y<-.9,'F02':n.y>.9,'F03':n.x<-.9,'F04':n.x>.9,'P01':n.z>.9}}[side]
        center=o.matrix_world @ poly.center
        plane={{'F01':abs(center.y)<.001,'F02':abs(center.y-d)<.001,'F03':abs(center.x)<.001,'F04':abs(center.x-w)<.001,'P01':abs(center.z)<.001}}[side]
        if not (exterior and plane): continue
        poly.material_index=idx;counts[side]+=1
        for li in poly.loop_indices:
            v=o.matrix_world @ mesh.vertices[mesh.loops[li].vertex_index].co
            layer.data[li].uv=uv(side,*v,w,d,h,t,m['repeat_m'] if m['mode']=='tile' else None)
assert all(counts.values()),counts
bpy.ops.wm.save_as_mainfile(filepath=str(out/'demo.blend'))
bpy.ops.export_scene.gltf(filepath=str(out/'demo.glb'),export_format='GLB',export_materials='EXPORT',export_texcoords=True,export_extras=True)
(out/'applied.json').write_text(__import__('json').dumps(counts))
"""
    (out/"reality_build.py").write_text(script,encoding="utf-8")
    exe=locate("blender")
    if not exe: raise SystemExit("Blender no encontrado")
    with (out/"reality.log").open("w",encoding="utf-8") as log:
        proc=subprocess.run([exe,"--background","--factory-startup","--disable-autoexec","--python-exit-code","1","--python",str(out/"reality_build.py")],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=240)
    ok=proc.returncode==0 and all((out/f).is_file() and (out/f).stat().st_size>0 for f in ("demo.blend","demo.glb","applied.json"))
    glb=out/"demo.glb"
    audit={}
    if ok:
        with glb.open("rb") as f:
            magic,version,total=struct.unpack("<4sII",f.read(12)); length,kind=struct.unpack("<I4s",f.read(8)); doc=json.loads(f.read(length))
        used={p.get('material') for mesh in doc.get('meshes',[]) for p in mesh.get('primitives',[]) if 'TEXCOORD_0' in p.get('attributes',{})}
        textured=[m for i,m in enumerate(doc.get('materials',[])) if i in used and m.get('name','').startswith('Reality_') and 'baseColorTexture' in m.get('pbrMetallicRoughness',{})]
        embedded=all("bufferView" in i for i in doc.get("images",[]))
        audit={"textured_materials":[m["name"] for m in textured],"images":len(doc.get("images",[])),"embedded":embedded}
        ok=magic==b"glTF" and version==2 and total==glb.stat().st_size and kind==b"JSON" and {m['name'] for m in textured}=={'Reality_'+k for k in materials} and bool(doc.get("images")) and embedded
    report={"audit":audit,"ok":ok,"parent":src.name,"demo":a.demo,"surfaces":list(materials),"folder":str(out),"limitations":["Fotos deben estar rectificadas previamente","Solo caras exteriores y piso","Sin cubierta ni render hiperrealista"]}
    (out/"reality_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8");print(json.dumps(report))
    if not ok: sys.exit(1)
import inspect
uv_source=inspect.getsource(uv)
if __name__=="__main__":main()
