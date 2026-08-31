import { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function mapX(x) {
  return Math.max(5, Math.min(95, x));
}

function mapY(y) {
  return Math.max(5, Math.min(95, y));
}

export default function DiagramRenderer({ scene, stepIndex }) {
  const actors = scene?.actors || [];
  const currentStep = scene?.steps?.[stepIndex];
  const currentEffects = currentStep?.effects || [];

  function isEffectActive(effect) {
    return currentEffects.some((e) => e.actor === effect.actor || e.target === effect.actor);
  }

  function isActorVisible(actorId) {
    const stepIndexes = [];
    scene?.steps?.forEach((step, idx) => {
      (step.effects || []).forEach((e) => {
        if (e.actor === actorId || e.target === actorId) {
          if (e.action === 'appear' || e.action === 'emit' || e.action === 'split') {
            stepIndexes.push(idx);
          }
        }
      });
    });
    if (stepIndexes.length === 0) return true;
    return stepIndex <= stepIndex;
  }

  function getActorColor(actorId) {
    const colors = ['#1cb0f6', '#22c55e', '#ef4444', '#f59e0b', '#8b5cf6', '#ec4899'];
    let hash = 0;
    for (let i = 0; i < actorId.length; i++) hash = actorId.charCodeAt(i) + ((hash << 5) - hash);
    return colors[Math.abs(hash) % colors.length];
  }

  const connections = useMemo(() => {
    const conns = [];
    currentEffects.forEach((e) => {
      if (e.action === 'connect') {
        const fromActor = actors.find((a) => a.id === e.actor);
        const toActor = actors.find((a) => a.id === e.target);
        if (fromActor && toActor) {
          conns.push({ from: fromActor, to: toActor });
        }
      }
    });
    return conns;
  }, [currentEffects, actors]);

  return (
    <div className="stage bg-grid" style={{ position: 'relative', width: '100%', paddingBottom: '65%', minHeight: 360 }}>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      >
        <AnimatePresence>
          {connections.map((conn, i) => (
            <motion.line
              key={`conn-${i}`}
              x1={`${mapX(conn.from.x)}%`}
              y1={`${mapY(conn.from.y)}%`}
              x2={`${mapX(conn.to.x)}%`}
              y2={`${mapY(conn.to.y)}%`}
              stroke="#64748b"
              strokeWidth="0.8"
              strokeDasharray="3 2"
              strokeLinecap="round"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 0.8 }}
              transition={{ duration: 0.6 }}
            />
          ))}
        </AnimatePresence>

        <AnimatePresence>
          {actors.filter((a) => isActorVisible(a.id)).map((actor) => {
            const active = isEffectActive({ actor: actor.id });
            const color = getActorColor(actor.id);
            return (
              <motion.g
                key={actor.id}
                initial={{ scale: 0, opacity: 0 }}
                animate={{
                  scale: active ? 1.15 : 1,
                  opacity: active ? 1 : 0.85,
                }}
                exit={{ scale: 0, opacity: 0 }}
                transition={{ type: 'spring', stiffness: 300, damping: 22 }}
                style={{ transformBox: 'fill-box', transformOrigin: 'center' }}
              >
                <circle
                  cx={`${mapX(actor.x)}%`}
                  cy={`${mapY(actor.y)}%`}
                  r="4.5"
                  fill={active ? color : '#e2e8f0'}
                  stroke={color}
                  strokeWidth="0.8"
                />
                <text
                  x={`${mapX(actor.x)}%`}
                  y={`${mapY(actor.y) - 6}%`}
                  textAnchor="middle"
                  fontSize="3"
                  fill="#1e293b"
                  fontWeight="700"
                >
                  {actor.label}
                </text>
                {actor.icon && (
                  <text
                    x={`${mapX(actor.x)}%`}
                    y={`${mapY(actor.y) + 3.5}%`}
                    textAnchor="middle"
                    fontSize="3.5"
                  >
                    {actor.icon}
                  </text>
                )}
              </motion.g>
            );
          })}
        </AnimatePresence>
      </svg>

      <AnimatePresence mode="wait">
        <motion.div
          key={stepIndex}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.35 }}
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            background: 'linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.95) 60%, rgba(255,255,255,1) 100%)',
            padding: '12px 14px 10px',
            pointerEvents: 'none',
          }}
        >
          <div style={{ fontWeight: 800, fontSize: 14, color: '#0f172a', lineHeight: 1.4 }}>
            {currentStep?.caption || ''}
          </div>
          {currentStep?.narration && (
            <div style={{ fontWeight: 600, fontSize: 12.5, color: '#475569', marginTop: 2, lineHeight: 1.5 }}>
              {currentStep.narration}
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
