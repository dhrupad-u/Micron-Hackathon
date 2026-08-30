import { motion, AnimatePresence } from 'framer-motion';
import { computeSceneState } from './sceneEngine';

const BIG = new Set(['sun', 'creature']);
const SMALL = new Set(['token', 'chip', 'bubble']);

function ActorView({ actor, fx }) {
  const { kind, label, icon, value } = actor;
  const cls =
    'actor' +
    (BIG.has(kind) ? ' big' : SMALL.has(kind) ? ' small' : '') +
    (fx === 'pulse' ? ' is-pulse' : '') +
    (fx === 'shake' ? ' is-shake' : '') +
    (fx === 'highlight' ? ' is-highlight' : '') +
    (fx === 'dim' ? ' is-dim' : '');

  let body;
  if (kind === 'box') {
    body = <span className="boxcard">{label || icon}</span>;
  } else if (kind === 'counter') {
    body = (
      <span className="counternum">
        {icon} {value != null ? value : 0}
      </span>
    );
  } else if (kind === 'meter') {
    const pct = typeof value === 'number' ? Math.max(0, Math.min(100, value)) : 50;
    body = <span className="meterbar"><i style={{ width: `${pct}%` }} /></span>;
  } else if (kind === 'lane' || kind === 'stack') {
    body = (
      <span
        className="boxcard"
        style={{ padding: '6px 14px', opacity: 0.75, background: kind === 'stack' ? '#f3e8ff' : '#ddf4ff', borderColor: kind === 'stack' ? '#ce82ff' : '#1cb0f6' }}
      >
        {icon} {label}
      </span>
    );
  } else {
    body = <span className="emo">{icon}</span>;
  }

  const showTag = label && kind !== 'box' && kind !== 'lane' && kind !== 'stack' && kind !== 'meter' && kind !== 'counter';

  return (
    <motion.div
      layout
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 320, damping: 22 }}
      className={cls}
      style={{ left: `${actor.x}%`, top: `${actor.y}%`, zIndex: kind === 'lane' ? 1 : 2 }}
      key={actor.id}
    >
      {body}
      {showTag && <span className="tag">{label}</span>}
    </motion.div>
  );
}

/**
 * Controlled scene renderer. Parent owns `stepIndex`; this component just paints
 * the folded actor state for that step.
 */
export default function ScenePlayer({ scene, stepIndex }) {
  const { actors, transient, connects } = computeSceneState(scene, stepIndex);
  const bg = `bg-${scene && scene.background ? scene.background : 'default'}`;

  return (
    <div className={`stage ${bg}`}>
      <div className="ground" />
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', zIndex: 3, pointerEvents: 'none' }}>
        {connects.map((c, i) => (
          <line
            key={i}
            x1={`${c.from.x}%`}
            y1={`${c.from.y}%`}
            x2={`${c.to.x}%`}
            y2={`${c.to.y}%`}
            stroke="#1cb0f6"
            strokeWidth="3"
            strokeDasharray="7 6"
            strokeLinecap="round"
          />
        ))}
      </svg>
      <AnimatePresence>
        {actors.map((a) => (
          <ActorView key={a.id} actor={a} fx={transient.get(a.id)} />
        ))}
      </AnimatePresence>
    </div>
  );
}
