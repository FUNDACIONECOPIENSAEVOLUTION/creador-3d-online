import test from 'node:test';
import assert from 'node:assert/strict';
import { planFreeCommand, runFreeCommand } from '../src/free-command-assistant.js';

test('Entiende una instrucción combinada sin IA ni suscripciones', () => {
  const actions = planFreeCommand('Crea un ángel con movimiento de ataque en modo ligero');
  assert.deepEqual(actions, [
    { type: 'create', figure: 'angel' },
    { type: 'quality', profile: 'low' },
    { type: 'animation', kind: 'attack' }
  ]);
});

test('Reconoce humanoide, defensa y exportar modelo GLB', () => {
  const actions = planFreeCommand('Quiero crear un humanoide, dale defensa y exportar personaje GLB');
  assert.deepEqual(actions, [
    { type: 'create', figure: 'humanoid' },
    { type: 'animation', kind: 'defend' },
    { type: 'export' }
  ]);
});

test('Rechaza instrucciones que no sabe ejecutar y textos excesivos', () => {
  assert.throws(() => planFreeCommand('Haz un humano totalmente fotorrealista a partir de mi foto'), /aún no soportada/);
  assert.throws(() => planFreeCommand('a'.repeat(1001)), /1000 caracteres/);
});

test('Ejecuta acciones permitidas exclusivamente en el estudio', () => {
  const calls = [];
  const studio = {
    selectedObject: { name: 'Angel' },
    createWebCharacter(type) { calls.push(['create', type]); return { name: 'Angel' }; },
    setQualityProfile(type) { calls.push(['quality', type]); },
    animationEditor: { makeRigidPreset(type) { calls.push(['animation', type]); return { name: type }; } },
    exportSelectedGLB() { calls.push(['export']); }
  };
  const result = runFreeCommand(studio, 'crea angel, modo ligero, ataque, exporta personaje glb');
  assert.ok(result.length === 4);
  assert.deepEqual(calls, [
    ['create', 'angel'], ['quality', 'low'], ['animation', 'attack'], ['export']
  ]);
});
