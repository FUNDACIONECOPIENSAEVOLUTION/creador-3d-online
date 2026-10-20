import { ASSET_VERSION } from './asset-blueprint.js';

/**
 * Lightweight, editable EXAMPLES of the universal blueprint vocabulary.
 * They are geometric starting points, not reconstructions of reference images.
 */
export const PRESET_OPTIONS = [
  {id:'anthro-cat',label:'Gato antropomorfo'},
  {id:'guardian-pawn',label:'♟ Peón guardián humanoide'},
  {id:'dragon',label:'Dragón fantástico'},
  {id:'robot',label:'Robot articulado'},
  {id:'tree',label:'Árbol'},
  {id:'chair',label:'Silla'},
  {id:'vehicle',label:'Vehículo sencillo'},
  {id:'castle',label:'Torre de castillo'}
];
export function makePresetBlueprint(id){
  if (!PRESET_OPTIONS.some(option=>option.id===id)) throw new Error('Plantilla no disponible.');
  const category = {
    'anthro-cat':'anthropomorphic','guardian-pawn':'human',dragon:'creature',robot:'robot',
    tree:'prop',chair:'prop',vehicle:'vehicle',castle:'building'
  }[id];
  const parts=[];
  const add=(name,shape,pos,scale,color,parent='root',rotationDeg=[0,0,0])=>{
    const part={id:name,name,parent,kind:'mesh',shape,position:pos,scale,color,rotationDeg};
    parts.push(part);
  };
  const joint=(name,pos,parent='root')=>parts.push({id:name,name,parent,kind:'joint',position:pos});
  const eyes=(parent,y,z,span=0.26,c='#64b58e')=>{
    add('Ojo_Izq','sphere',[-span,y,z],[.12,.13,.08],c,parent);
    add('Ojo_Der','sphere',[span,y,z],[.12,.13,.08],c,parent);
  };

  if(id==='guardian-pawn'){
    // Parametric videogame starter; separate movable joints, realistic proportions
    // but not a photogrammetric or cinematic human reconstruction.
    const ivory='#e9e2d2',silver='#a9bac8',steel='#495e71',gold='#e6b954';
    const skin='#c9a081',leather='#403328',dark='#182436',eyesColor='#6fd7b0';
    add('Peana_Inferior','cylinder',[0,.12,0],[1.28,.24,1.28],dark);
    add('Peana_Anillo','torus',[0,.25,0],[1.26,.22,1.26],gold,'root',[-90,0,0]);
    add('Peana_Superior','cylinder',[0,.31,0],[1.14,.12,1.14],steel);
    joint('Raiz_Cadera',[0,1.13,0]);
    add('Pelvis_Armadura','sphere',[0,.04,0],[.88,.48,.54],steel,'Raiz_Cadera');
    add('Cinturon','cylinder',[0,.25,0],[.84,.20,.58],leather,'Raiz_Cadera');
    add('Hebilla','box',[0,.25,-.34],[.26,.19,.12],gold,'Raiz_Cadera');
    joint('Torso_Pivote',[0,.35,0],'Raiz_Cadera');
    add('Peto_Principal','capsule',[0,.54,0],[1.11,.83,.64],silver,'Torso_Pivote');
    add('Pecho_Placa','box',[0,.67,-.35],[.66,.56,.13],ivory,'Torso_Pivote');
    add('Pecho_Escudo','sphere',[0,.76,-.435],[.22,.28,.07],gold,'Torso_Pivote');
    add('Espalda_Capa','box',[0,.17,.39],[1.04,1.38,.13],dark,'Torso_Pivote');
    add('Cuello_Gargantilla','cylinder',[0,1.17,0],[.52,.19,.48],gold,'Torso_Pivote');
    joint('Cuello_Pivote',[0,1.21,0],'Torso_Pivote');
    add('Rostro','sphere',[0,.30,-.06],[.65,.76,.57],skin,'Cuello_Pivote');
    add('Mandibula','sphere',[0,.01,-.23],[.45,.32,.34],skin,'Cuello_Pivote');
    add('Nariz','cone',[0,.28,-.60],[.17,.30,.16],skin,'Cuello_Pivote',[90,0,0]);
    add('Visera_Casco','sphere',[0,.61,.04],[.75,.47,.67],steel,'Cuello_Pivote');
    add('Ribete_Casco','torus',[0,.50,0],[.66,.34,.63],gold,'Cuello_Pivote',[90,0,0]);
    add('Penacho_Casco','capsule',[0,.95,.04],[.18,.48,.16],ivory,'Cuello_Pivote');
    add('Crema_Casco','cone',[0,1.19,.04],[.32,.35,.25],gold,'Cuello_Pivote');
    for(const side of [-1,1]){
      const label=side<0?'Izq':'Der';
      add('Ojo_'+label,'sphere',[side*.23,.29,-.565],[.11,.09,.075],eyesColor,'Cuello_Pivote');
      add('Pupila_'+label,'sphere',[side*.23,.29,-.625],[.045,.055,.04],dark,'Cuello_Pivote');
      add('Ceja_'+label,'box',[side*.23,.40,-.57],[.24,.055,.065],leather,'Cuello_Pivote');
      add('Guarda_Casco_'+label,'box',[side*.62,.35,-.12],[.20,.60,.34],steel,'Cuello_Pivote');
      joint('Hombro_'+label,[side*.68,1.02,0],'Torso_Pivote');
      add('Hombrera_'+label,'sphere',[side*.09,-.04,0],[.62,.48,.63],steel,'Hombro_'+label);
      add('Brazalete_'+label,'torus',[side*.11,-.23,0],[.36,.16,.30],gold,'Hombro_'+label',[90,0,0]);
      add('Brazo_'+label,'capsule',[side*.08,-.42,0],[.38,.53,.39],silver,'Hombro_'+label);
      joint('Codo_'+label,[side*.13,-.75,0],'Hombro_'+label);
      add('Antebrazo_'+label,'capsule',[0,-.31,0],[.34,.48,.32],steel,'Codo_'+label);
      add('Guante_'+label,'sphere',[0,-.67,0],[.33,.26,.25],leather,'Codo_'+label);
      joint('Cadera_'+label,[side*.33,-.13,0],'Raiz_Cadera');
      add('Muslo_'+label,'capsule',[0,-.37,0],[.44,.55,.48],silver,'Cadera_'+label);
      add('Rodillera_'+label,'sphere',[0,-.73,-.17],[.46,.34,.29],gold,'Cadera_'+label);
      joint('Rodilla_'+label,[0,-.77,0],'Cadera_'+label);
      add('Espinillera_'+label,'capsule',[0,-.37,0],[.37,.53,.39],steel,'Rodilla_'+label);
      add('Bota_'+label,'box',[0,-.81,-.17],[.47,.27,.77],leather,'Rodilla_'+label);
      for(let i=0;i<3;i++){
        add('Faldon_'+label+'_'+i,'box',[side*(.23+.15*i),-.16,.15+i*.04],[.14,.62,.09],ivory,'Raiz_Cadera',[side*8,0,side*5]);
      }
    }
    joint('Lanza_Agarre',[0,-.71,0],'Codo_Der');
    add('Lanza_Mango','cylinder',[0,.02,-.22],[.085,2.5,.085],leather,'Lanza_Agarre');
    add('Lanza_Anillos','torus',[0,.74,-.22],[.22,.12,.22],gold,'Lanza_Agarre',[90,0,0]);
    add('Lanza_Punta','cone',[0,1.52,-.22],[.31,.83,.27],silver,'Lanza_Agarre');
    joint('Escudo_Agarre',[-.15,-.58,-.26],'Codo_Izq');
    add('Escudo_Plateria','sphere',[-.12,-.11,-.31],[.88,1.08,.24],steel,'Escudo_Agarre');
    add('Escudo_Frontal','sphere',[-.12,-.10,-.47],[.70,.90,.09],ivory,'Escudo_Agarre');
    add('Escudo_Blason','sphere',[-.12,-.09,-.56],[.33,.42,.09],gold,'Escudo_Agarre');
    return {version:ASSET_VERSION,name:'Peon_Guardian_Ecoajedrez',category,parts};
  }
  if (id === 'anthro-cat' || id === 'robot') {
    const fur = id==='robot'?'#7b9baa':'#b88756';
    const secondary=id==='robot'?'#4b606a':'#eee0bb';
    add('Torso','capsule',[0,1.5,0],[.95,.8,.66],fur);
    joint('Cuello',[0,2.2,0]);
    add('Cabeza','sphere',[0,.24,0],[.85,.75,.7],fur,'Cuello');
    if(id==='anthro-cat'){
      for(const side of [-1,1]){
        const tag=side===-1?'Izq':'Der';
        add('Oreja_'+tag,'cone',[side*.32,.69,0],[.33,.55,.28],fur,'Cuello');
        add('Bigote_'+tag,'cylinder',[side*.47,.08,-.35],[.018,.45,.018],secondary,'Cuello',[0,0,side*78]);
      }
      add('Hocico','sphere',[0,.08,-.42],[.38,.25,.28],secondary,'Cuello');
      joint('Cola_Base',[0,1.15,.26]);
      add('Cola','capsule',[.48,.04,.3],[.22,.9,.22],fur,'Cola_Base',[0,0,-48]);
    } else {
      add('Casco','box',[0,.75,0],[.91,.2,.73],secondary,'Cuello');
      add('Pecho_Panel','box',[0,1.7,-.35],[.65,.45,.08],'#3fd7d1');
    }
    eyes('Cuello',.31,-.36,.23,id==='robot'?'#28ebe5':'#69b88f');
    for(const side of [-1,1]){
      const tag=side===-1?'Izq':'Der';
      joint('Hombro_'+tag,[side*.63,1.95,0]);
      add('Brazo_'+tag,'capsule',[side*.12,-.35,0],[.30,.49,.30],fur,'Hombro_'+tag);
      joint('Codo_'+tag,[side*.13,-.78,0],'Hombro_'+tag);
      add('Antebrazo_'+tag,'capsule',[0,-.31,0],[.27,.43,.26],secondary,'Codo_'+tag);
      add('Mano_'+tag,'sphere',[0,-.7,0],[.3,.25,.18],fur,'Codo_'+tag);
      joint('Cadera_'+tag,[side*.32,1.1,0]);
      add('Muslo_'+tag,'capsule',[0,-.37,0],[.36,.54,.38],fur,'Cadera_'+tag);
      joint('Rodilla_'+tag,[0,-.81,0],'Cadera_'+tag);
      add('Pantorrilla_'+tag,'capsule',[0,-.33,0],[.29,.42,.3],secondary,'Rodilla_'+tag);
      add('Pie_'+tag,'box',[0,-.74,-.17],[.35,.23,.64],secondary,'Rodilla_'+tag);
    }
  } else if(id==='dragon'){
    const primary='#477f68',wing='#8fbd98',horn='#dbc690';
    add('Cuerpo','sphere',[0,1.35,0],[1.25,.65,.82],primary);
    joint('Cuello',[0,1.68,-.65]);
    add('Cuello_Malla','capsule',[0,.39,-.1],[.5,.72,.52],primary,'Cuello',[28,0,0]);
    add('Cabeza','sphere',[0,.94,-.25],[.75,.47,.63],primary,'Cuello');
    add('Hocico','sphere',[0,.79,-.69],[.48,.27,.58],primary,'Cuello');
    eyes('Cuello',1.04,-.65,.3,'#e7c04a');
    for(const side of [-1,1]){
      const tag=side<0?'Izq':'Der';
      add('Cuerno_'+tag,'cone',[side*.38,1.27,-.18],[.22,.65,.24],horn,'Cuello',[0,0,-side*15]);
      for(const z of [-.48,.55]){
        const key=z<0?'Del':'Tra';
        joint('Pata_'+key+'_'+tag,[side*.76,1.04,z]);
        add('Pata_Mesh_'+key+'_'+tag,'capsule',[0,-.45,0],[.35,.65,.36],primary,'Pata_'+key+'_'+tag);
        add('Garra_'+key+'_'+tag,'cone',[0,-.96,-.22],[.21,.36,.22],horn,'Pata_'+key+'_'+tag,[90,0,0]);
      }
      joint('Ala_'+tag,[side*.42,1.75,.12]);
      add('Ala_Membrana_'+tag,'box',[side*.81,.36,.01],[1.6,.11,.92],wing,'Ala_'+tag,[0,side*14,side*27]);
    }
    joint('Cola_Dragon',[0,1.24,.69]);
    for(let i=0;i<4;i++) add('Cola_Segmento_'+i,'cone',[0,-.12-i*.09,.42+i*.35],[.37-i*.07,.67-i*.09,.37-i*.07],primary,'Cola_Dragon',[90,0,0]);
  } else if(id==='tree'){
    add('Tronco','cylinder',[0,1,0],[.54,2,.54],'#6a4731');
    for(let i=0;i<3;i++)add('Copa_'+i,'sphere',[0,2.2+i*.42,0],[2-i*.3,1.3-i*.1,1.7-i*.23],'#2d7553');
  } else if(id==='chair'){
    const wood='#7b4f35';
    add('Asiento','box',[0,.95,0],[1.2,.15,1.1],wood);
    add('Respaldo','box',[0,1.55,.48],[1.18,1.13,.15],wood);
    for(const x of [-.48,.48])for(const z of [-.44,.44])
      add('Pata_'+(x<0?'I':'D')+(z<0?'F':'T'),'cylinder',[x,.47,z],[.13,.95,.13],wood);
  } else if(id==='vehicle'){
    add('Carroceria','box',[0,.7,0],[2.4,.6,1.2],'#317fbb');
    add('Cabina','box',[.1,1.18,0],[1.2,.55,1.1],'#9ec4d9');
    for(const x of [-.75,.8])for(const z of [-.63,.63]){
      const tag=(x<0?'T':'D')+(z<0?'I':'D');
      joint('Rueda_Pivote_'+tag,[x,.42,z]);
      add('Rueda_'+tag,'cylinder',[0,0,0],[.42,.24,.42],'#2a3038','Rueda_Pivote_'+tag,[90,0,0]);
    }
  }else if(id==='castle'){
    const stone='#92929c';
    add('Torre','cylinder',[0,1.35,0],[1.4,2.7,1.4],stone);
    add('Techo','cone',[0,3.02,0],[1.8,1.1,1.8],'#536790');
    add('Puerta','box',[0,.56,-.71],[.55,1.1,.12],'#543c30');
    for(let i=0;i<6;i++){
      const a=i*Math.PI/3;
      add('Almena_'+i,'box',[.63*Math.sin(a),2.71,.63*Math.cos(a)],[.43,.38,.43],stone);
    }
  }
  return {version:ASSET_VERSION,name:'EcoBlend_'+id.replace(/-/g,'_'),category,parts};
}
/** Only explicit, limited examples; unlike a vision-capable AI this doesn't interpret arbitrary pictures. */
export function matchPreset(description){
  if(typeof description!=='string'||description.length>1800)throw new Error('Descripción inválida.');
  const text=description.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  if(/\b(gato|felino|gata|cat)\b/.test(text)&&/\b(antropomorfo|humanoide|guerrero|bipedo)\b/.test(text))return 'anthro-cat';
  if(/\b(dragon|draconico)\b/.test(text))return 'dragon';
  if(/\b(robot|androide|mecanico)\b/.test(text))return 'robot';
  if(/\b(arbol|planta grande)\b/.test(text))return 'tree';
  if(/\b(silla|asiento)\b/.test(text))return 'chair';
  if(/\b(carro|coche|automovil|vehiculo)\b/.test(text))return 'vehicle';
  if(/\b(castillo|torre medieval|torre de piedra)\b/.test(text))return 'castle';
  return null;
}
