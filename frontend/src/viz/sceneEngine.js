// Folds a scene script's step effects into a renderable actor state at step k.
// Persistent actions (appear/move/fill/increment/emit/merge) carry forward;
// transient actions (pulse/shake/highlight/dim/connect) apply only at step k.

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

export function computeSceneState(scene, stepIndex) {
  if (!scene || !scene.actors || !scene.steps) {
    return { actors: [], transient: new Map(), connects: [], steps: [] };
  }

  // Actors referenced by an appear/emit/split effect start hidden.
  const bornLater = new Set();
  scene.steps.forEach((s) =>
    (s.effects || []).forEach((e) => {
      if (e.action === 'appear' || e.action === 'emit' || e.action === 'split') {
        bornLater.add(e.target || e.actor);
      }
    })
  );

  const state = new Map();
  scene.actors.forEach((a) => {
    state.set(a.id, {
      id: a.id,
      kind: a.kind || 'node',
      label: a.label ?? '',
      icon: a.icon || defaultIcon(a.kind),
      x: clampNum(a.x, 50),
      y: clampNum(a.y, 50),
      value: a.value ?? null,
      visible: !bornLater.has(a.id),
    });
  });

  const transient = new Map();
  const connects = [];
  const upto = scene.steps.slice(0, clamp(stepIndex, -1, scene.steps.length - 1) + 1);

  upto.forEach((step, i) => {
    const isCurrent = i === upto.length - 1;
    (step.effects || []).forEach((e) => {
      const a = state.get(e.actor);
      const t = e.target ? state.get(e.target) : null;
      switch (e.action) {
        case 'appear':
          if (a) a.visible = true;
          if (t) t.visible = true;
          break;
        case 'disappear':
          if (a) a.visible = false;
          break;
        case 'move':
          if (a) {
            a.x = clampNum(e.to_x, a.x);
            a.y = clampNum(e.to_y, a.y);
          }
          break;
        case 'fill':
          if (a) {
            if (e.label != null) a.label = String(e.label);
            if (e.value != null) a.value = e.value;
          }
          break;
        case 'increment':
          if (a) {
            a.value = typeof e.value === 'number' ? e.value : (typeof a.value === 'number' ? a.value : 0) + 1;
          }
          break;
        case 'emit':
        case 'split':
          if (t) {
            t.visible = true;
            if (a) {
              t.x = clampNum(a.x + 9, t.x);
              t.y = clampNum(a.y, t.y);
            }
          }
          break;
        case 'merge':
          if (a && t) {
            a.x = t.x;
            a.y = t.y;
            a.visible = false;
            if (isCurrent) transient.set(t.id, 'pulse');
          }
          break;
        case 'pulse':
        case 'shake':
        case 'highlight':
        case 'dim':
          if (a && isCurrent) transient.set(a.id, e.action);
          break;
        case 'connect':
          if (a && t && isCurrent) connects.push({ from: a, to: t });
          break;
        default:
          break;
      }
    });
  });

  return {
    actors: [...state.values()].filter((a) => a.visible),
    transient,
    connects,
    steps: scene.steps,
  };
}

function clampNum(v, fallback) {
  const n = typeof v === 'number' ? v : parseFloat(v);
  if (Number.isNaN(n)) return fallback;
  return clamp(n, 0, 100);
}

function defaultIcon(kind) {
  const map = {
    box: '📦', token: '🔴', node: '🔘', sun: '☀️', drop: '💧', bubble: '🫧',
    arrow: '📍', counter: '🔢', chip: '🏷️', meter: '📊', lane: '➖', creature: '🐾', stack: '🗂️',
  };
  return map[kind] || '🔘';
}

export function sceneLength(scene) {
  return scene && scene.steps ? scene.steps.length : 0;
}

export function captionAt(scene, i) {
  return scene && scene.steps && scene.steps[i] ? scene.steps[i].caption || '' : '';
}
