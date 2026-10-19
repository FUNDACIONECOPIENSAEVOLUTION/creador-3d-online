/**
 * EcoBlend CharacterSpec v1.0 — intercambio entre web, IA y futuros adaptadores.
 * Parser descriptivo gratuito, explícitamente limitado: NO es un LLM.
 * Nunca adivina detalles ausentes de una descripción o fotografía.
 */
export const DEFAULT_SPEC = Object.freeze({
  schemaVersion: 'ecoblend.character.v1',
  kind: 'humanoid',
  presentation: 'unspecified',
  heightCm: 172,
  build: 'average',
  eyeColor: 'brown',
  hairColor: 'black',
  hairStyle: 'short',
  skinTone: 'medium',
  faceShape: 'oval',
  outfit: 'casual',
  rig: 'hierarchical-pivots',
  target: 'game-glb'
});
const valid = {
  kind: ['humanoid', 'angel'],
  presentation: ['unspecified', 'feminine', 'masculine'],
  build: ['slim', 'average', 'curvy', 'athletic', 'broad'],
  eyeColor: ['brown', 'green', 'blue', 'hazel', 'gray'],
  hairColor: ['black', 'brown', 'blond', 'red', 'gray', 'white'],
  hairStyle: ['none', 'short', 'medium', 'long'],
  skinTone: ['light', 'medium', 'tan', 'dark'],
  faceShape: ['oval', 'round', 'angular'],
  outfit: ['casual', 'armor'],
  target: ['game-glb', 'webar-glb']
};
export function normalizeCharacterSpec(input = {}, base = DEFAULT_SPEC) {
  if (input === null || typeof input !== 'object' || Array.isArray(input)) throw new Error('La ficha debe ser un objeto JSON.');
  const result = { ...DEFAULT_SPEC, ...base };
  for (const [key, value] of Object.entries(input)) {
    if (key === 'schemaVersion' || key === 'rig') continue; // determinados por el motor
    if (key === 'heightCm') {
      if (typeof value !== 'number' || !Number.isFinite(value) || value < 120 || value > 220)
        throw new Error('heightCm debe estar entre 120 y 220 centímetros.');
      result.heightCm = value;
    } else if (valid[key]) {
      if (!valid[key].includes(value)) throw new Error('Valor inválido de ' + key + ': ' + String(value));
      result[key] = value;
    } else throw new Error('Atributo no permitido: ' + key);
  }
  result.schemaVersion = DEFAULT_SPEC.schemaVersion;
  result.rig = DEFAULT_SPEC.rig;
  return result;
}
const clean = str => str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
export function interpretCharacterDescription(description, base = DEFAULT_SPEC) {
  if (typeof description !== 'string' || !description.trim() || description.length > 1800)
    throw new Error('Escribe una descripción de 1 a 1800 caracteres.');
  const s = clean(description);
  const data = {};
  const has = re => re.test(s);
  if (has(/\b(angel|angelical|alas|guardian alado|pegaso)\b/)) data.kind = 'angel';
  else if (has(/\b(humano|humana|persona|mujer|hombre|avatar|personaje)\b/)) data.kind = 'humanoid';
  if (has(/\b(mujer|femenina|femenino)\b/)) data.presentation = 'feminine';
  else if (has(/\b(hombre|masculino|masculina)\b/)) data.presentation = 'masculine';
  if (has(/\b(acuerpad[ao]|corpulenta|corpulento|curvilinea|curvas)\b/)) data.build = 'curvy';
  else if (has(/\b(musculos[ao]|musculoso|atletic[ao])\b/)) data.build = 'athletic';
  else if (has(/\b(robust[ao]|espald[ao] anch[ao]|ancho de hombros)\b/)) data.build = 'broad';
  else if (has(/\b(delgad[ao]|esbelt[ao]|delgada)\b/)) data.build = 'slim';
  if (has(/\b(ojos?\s+(?:de color\s+)?verdes?|ojos?\s+esmeralda)\b/)) data.eyeColor = 'green';
  else if (has(/\b(ojos?\s+(?:de color\s+)?azules?)\b/)) data.eyeColor = 'blue';
  else if (has(/\b(ojos?\s+(?:de color\s+)?grises?)\b/)) data.eyeColor = 'gray';
  else if (has(/\b(ojos?\s+(?:de color\s+)?miel|ojos?\s+avellana)\b/)) data.eyeColor = 'hazel';
  else if (has(/\b(ojos?\s+(?:de color\s+)?(cafes?|marrones?|castanos?))\b/)) data.eyeColor = 'brown';
  if (has(/\b(cabello|pelo|melena|pelo\s+largo)\b/)) {
    if (has(/\b(cabello|pelo|melena)\s+(negro|azabache)|\bnegro\s+(cabello|pelo)\b/)) data.hairColor = 'black';
    else if (has(/\b(cabello|pelo|melena)\s+(castano|marron)|\bcastano\s+(cabello|pelo)\b/)) data.hairColor = 'brown';
    else if (has(/\b(cabello|pelo|melena)\s+(rubio|rubia)|\brubio\s+(cabello|pelo)\b/)) data.hairColor = 'blond';
    else if (has(/\b(cabello|pelo|melena)\s+(rojo|pelirrojo)|\bpelirrojo\b/)) data.hairColor = 'red';
    else if (has(/\b(cabello|pelo|melena)\s+(gris|canoso|blanco)|\bcanoso\b/)) data.hairColor = 'gray';
    if (has(/\b(sin cabello|sin pelo|calv[ao])\b/)) data.hairStyle = 'none';
    else if (has(/\b(cabello|pelo|melena)\s+(?:(?:negro|castano|rubio|rojo|gris|blanco)\s+)?largo|\bpelo largo\b|\bmelena larga\b/)) data.hairStyle = 'long';
    else if (has(/\b(cabello|pelo)\s+(?:(?:negro|castano|rubio|rojo|gris)\s+)?corto\b/)) data.hairStyle = 'short';
    else if (has(/\bmedia melena|cabello mediano\b/)) data.hairStyle = 'medium';
  }
  if (has(/\b(piel triguena|piel canela|piel bronceada|piel morena clara)\b/)) data.skinTone = 'tan';
  else if (has(/\b(piel oscura|piel morena oscura|piel negra)\b/)) data.skinTone = 'dark';
  else if (has(/\b(piel clara|piel palida|piel blanca)\b/)) data.skinTone = 'light';
  if (has(/\b(rostro redondo|cara redonda)\b/)) data.faceShape = 'round';
  else if (has(/\b(rostro angular|cara angular)\b/)) data.faceShape = 'angular';
  else if (has(/\b(rostro ovalado|cara ovalada)\b/)) data.faceShape = 'oval';
  if (has(/\b(armadura|guerrer[ao]|caballer[ao])\b/)) data.outfit = 'armor';
  const cm = s.match(/\b(?:altura\s*(?:de\s*)?)?(1[.,][2-9]\d?|2[.,][0-1]\d?)\s*(?:m|metros?)\b/);
  if (cm) data.heightCm = Math.round(Number(cm[1].replace(',', '.')) * 100);
  const centimeters = s.match(/\b(1[2-9]\d|20\d|21\d|220)\s*(?:cm|centimetros?)\b/);
  if (centimeters) data.heightCm = Number(centimeters[1]);
  const spec = normalizeCharacterSpec(data, base);
  return { spec, detected: Object.keys(data), limitations: 'Interpretación de rasgos explícitos; sin IA generativa ni modelado hiperrealista automático.' };
}
