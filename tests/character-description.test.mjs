import test from 'node:test';
import assert from 'node:assert/strict';
import { interpretCharacterDescription, normalizeCharacterSpec } from '../src/character-spec.js';
import { createFreeCharacter } from '../src/procedural-character.js';
import { applyCharacterAppearance } from '../src/character-appearance.js';

test('Una descripción humana produce atributos explícitos, no inferidos',()=>{
  const parsed=interpretCharacterDescription(
    'Haz una mujer de ojos verdes, acuerpada, cabello negro largo, piel canela y altura 1.68 metros'
  );
  assert.equal(parsed.spec.kind,'humanoid');
  assert.equal(parsed.spec.presentation,'feminine');
  assert.equal(parsed.spec.eyeColor,'green');
  assert.equal(parsed.spec.hairColor,'black');
  assert.equal(parsed.spec.hairStyle,'long');
  assert.equal(parsed.spec.build,'curvy');
  assert.equal(parsed.spec.skinTone,'tan');
  assert.equal(parsed.spec.heightCm,168);
  assert.equal(parsed.detected.includes('eyeColor'),true);
  assert.equal(parsed.detected.includes('hairStyle'),true);
});

test('La descripción humana cambia geometría y materiales visibles de una base libre',()=>{
  const {object}=createFreeCharacter({type:'humanoid',detail:'low'});
  const spec=interpretCharacterDescription('Mujer de ojos verdes, cabello negro largo, acuerpada').spec;
  const result=applyCharacterAppearance(object,spec);
  assert.equal(result.updated,true);
  assert.equal(object.getObjectByName('Ojo_Izquierdo').material.color.getHexString(),'44864b');
  assert.equal(object.getObjectByName('Ojo_Derecho').material.color.getHexString(),'44864b');
  assert.ok(object.getObjectByName('EcoBlend_Cabello'));
  assert.ok(object.getObjectByName('Melena_Izquierda'));
  assert.ok(object.getObjectByName('Torso_Armadura').scale.x > .29);
  assert.equal(object.userData.ecoblendCharacterSpec.build,'curvy');
});

test('Solo permite ajustes sobre cuerpos generados y validaciones seguras',()=>{
  assert.throws(()=>normalizeCharacterSpec({eyeColor:'ultraviolet'}),/Valor inválido/);
  assert.throws(()=>normalizeCharacterSpec({heightCm:500}),/120 y 220/);
  assert.throws(()=>applyCharacterAppearance({name:'Externo'},{}),/base humana o ángel/);
});
