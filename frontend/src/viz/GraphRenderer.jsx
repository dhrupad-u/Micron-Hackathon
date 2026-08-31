import { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function mapX(dataX, xRange) {
  return ((dataX - xRange[0]) / (xRange[1] - xRange[0])) * 100;
}

function mapY(dataY, yRange) {
  return 100 - ((dataY - yRange[0]) / (yRange[1] - yRange[0])) * 100;
}

function pointsToPath(points, xRange, yRange) {
  if (!points || points.length === 0) return '';
  return points
    .map((p, i) => {
      const x = mapX(p[0], xRange);
      const y = mapY(p[1], yRange);
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');
}

export default function GraphRenderer({ scene, stepIndex }) {
  const graph = scene?.graph_data || {};
  const xRange = graph.x_range || [0, 100];
  const yRange = graph.y_range || [0, 100];

  const curves = useMemo(() => {
    if (!graph.curves) return [];
    return graph.curves.map((c) => ({
      ...c,
      path: pointsToPath(c.points, xRange, yRange),
    }));
  }, [graph.curves, xRange, yRange]);

  const equilibria = useMemo(() => {
    if (!graph.equilibria) return [];
    return graph.equilibria.map((eq) => ({
      ...eq,
      cx: mapX(eq.x, xRange),
      cy: mapY(eq.y, yRange),
    }));
  }, [graph.equilibria, xRange, yRange]);

  const annotations = useMemo(() => {
    if (!graph.annotations) return [];
    return graph.annotations.map((a) => ({
      ...a,
      x: mapX(a.x, xRange),
      y: mapY(a.y, yRange),
    }));
  }, [graph.annotations, xRange, yRange]);

  const currentStep = scene?.steps?.[stepIndex];
  const currentEffects = currentStep?.effects || [];

  function isEffectActive(effect) {
    return currentEffects.some((e) => e.actor === effect.actor || e.target === effect.actor);
  }

  function curveVisible(curve) {
    const from = curve.visible_from_step ?? 0;
    const to = curve.visible_to_step ?? Infinity;
    return stepIndex >= from && stepIndex < to;
  }

  function eqVisible(eq) {
    const from = eq.visible_from_step ?? 0;
    const to = eq.visible_to_step ?? Infinity;
    return stepIndex >= from && stepIndex < to;
  }

  function annotationVisible(a) {
    return stepIndex >= a.step;
  }

  return (
    <div className="stage bg-grid" style={{ position: 'relative', width: '100%', paddingBottom: '65%', minHeight: 360 }}>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      >
        <defs>
          <marker id="arrowhead" markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto">
            <path d="M 0 0 L 6 2 L 0 4 z" fill="#64748b" />
          </marker>
        </defs>

        <line x1="6" y1="90" x2="96" y2="90" stroke="#64748b" strokeWidth="0.6" markerEnd="url(#arrowhead)" />
        <line x1="6" y1="90" x2="6" y2="4" stroke="#64748b" strokeWidth="0.6" markerEnd="url(#arrowhead)" />

        <text x="50" y="96" textAnchor="middle" fontSize="3.2" fill="#475569" fontWeight="700">
          {graph.x_axis || 'X'}
        </text>
        <text x="3" y="8" textAnchor="start" fontSize="3.2" fill="#475569" fontWeight="700">
          {graph.y_axis || 'Y'}
        </text>

        {[0, 25, 50, 75, 100].map((pct) => (
          <g key={`grid-${pct}`}>
            <line x1={pct} y1="90" x2={pct} y2="4" stroke="#cbd5e1" strokeWidth="0.15" strokeDasharray="1 1" opacity="0.6" />
            <line x1="6" y1={pct} x2="96" y2={pct} stroke="#cbd5e1" strokeWidth="0.15" strokeDasharray="1 1" opacity="0.6" />
          </g>
        ))}

        <AnimatePresence>
          {curves.filter(curveVisible).map((curve) => (
            <motion.path
              key={curve.id}
              d={curve.path}
              fill="none"
              stroke={curve.color || '#334155'}
              strokeWidth="1.2"
              strokeLinecap="round"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 0.8, ease: 'easeInOut' }}
            />
          ))}
        </AnimatePresence>

        <AnimatePresence>
          {equilibria.filter(eqVisible).map((eq) => (
            <motion.g
              key={eq.id}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            >
              <circle cx={eq.cx} cy={eq.cy} r="2.2" fill={eq.color || '#ef4444'} opacity="0.2" />
              <circle cx={eq.cx} cy={eq.cy} r="1.4" fill={eq.color || '#ef4444'} />
              <text x={eq.cx + 2.5} y={eq.cy - 1.5} fontSize="2.8" fill={eq.color || '#ef4444'} fontWeight="800">
                {eq.label}
              </text>
            </motion.g>
          ))}
        </AnimatePresence>

        <AnimatePresence>
          {annotations.filter(annotationVisible).map((a, i) => (
            <motion.text
              key={`ann-${i}`}
              x={a.x}
              y={a.y}
              fontSize="2.6"
              fill={a.color || '#334155'}
              fontWeight="800"
              initial={{ opacity: 0, y: a.y + 1 }}
              animate={{ opacity: 1, y: a.y }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              {a.text}
            </motion.text>
          ))}
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
