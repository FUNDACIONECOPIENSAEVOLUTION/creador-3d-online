/**
 * Accessible free starter interpreter: deterministic commands, no paid AI, no eval.
 * This is NOT a language model. Unknown language is explicitly refused.
 * Translates a small set of Spanish verbs to existing studio actions.
 */
export function planFreeCommand(raw) {
  if (typeof raw !== 'string' || raw.length > 1000) throw new Error('La instrucción debe tener hasta 1000 caracteres.');
  const input = raw.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  if (!input.trim()) throw new Error('Escribe una instrucción.');
  const commands = [];
  if (/\b(angel|guardian alado|guardian con alas)\b/.test(input) &&
      /\b(crea|crear|genera|generar|haz|hacer|quiero|necesito)\b/.test(input))
    commands.push({ type: 'create', figure: 'angel' });
  else if (/\b(humano|humanoide|persona|maniqui)\b/.test(input) &&
           /\b(crea|crear|genera|generar|haz|hacer|quiero|necesito)\b/.test(input))
    commands.push({ type: 'create', figure: 'humanoid' });

  if (/\b(modo ligero|calidad baja|bajo consumo|pc lento|equipo modesto)\b/.test(input))
    commands.push({ type: 'quality', profile: 'low' });
  else if (/\b(modo visual|calidad alta)\b/.test(input))
    commands.push({ type: 'quality', profile: 'high' });
  else if (/\b(modo equilibrado|calidad media)\b/.test(input))
    commands.push({ type: 'quality', profile: 'balanced' });

  let animation = null;
  if (/\b(ataque|atacar|ataca|peleando)\b/.test(input)) animation = 'attack';
  else if (/\b(defensa|defender|defiende|escudo)\b/.test(input)) animation = 'defend';
  else if (/\b(reposo|quieto|respirando|idle)\b/.test(input)) animation = 'idle';
  else if (/\b(derrota|derrotado|caerse)\b/.test(input)) animation = 'defeat';
  else if (/\b(golpe|golpeado|recibir golpe)\b/.test(input)) animation = 'hit';
  if (animation) commands.push({ type: 'animation', kind: animation });

  if (/\b(exporta|exportar|descarga|descargar)\b/.test(input) &&
      /\b(personaje|modelo|glb|figura)\b/.test(input))
    commands.push({ type: 'export' });

  if (!commands.length) throw new Error(
    'Instrucción aún no soportada. Prueba: "crea un ángel con ataque", "crea humanoide", "modo ligero" o "descarga personaje GLB".'
  );
  return commands;
}

export function runFreeCommand(studio, prompt) {
  const commands = planFreeCommand(prompt);
  const result = [];
  for (const command of commands) {
    switch (command.type) {
      case 'create': {
        const created = studio.createWebCharacter(command.figure);
        if (created?.error) throw new Error(created.error);
        result.push('Creado: ' + created.name);
        break;
      }
      case 'quality':
        studio.setQualityProfile(command.profile);
        result.push('Perfil: ' + command.profile);
        break;
      case 'animation': {
        const clip = studio.animationEditor.makeRigidPreset(command.kind, studio.selectedObject);
        result.push('Animación: ' + clip.name + ' (pieza completa)');
        break;
      }
      case 'export':
        studio.exportSelectedGLB();
        result.push('Exportando GLB del personaje seleccionado');
        break;
      default:
        throw new Error('Acción no reconocida.');
    }
  }
  return result;
}
