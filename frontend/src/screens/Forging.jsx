import { useEffect, useRef, useState } from 'react';
import { Check } from 'lucide-react';
import { api } from '../api.js';

const STAGES = [
  { status: 'new', emoji: '🕵️', name: 'Detector', blurb: 'Reading your warm-up answers' },
  { status: 'diagnose', emoji: '🗺️', name: 'Architect', blurb: 'Mapping what you know and skip what you don’t' },
  { status: 'plan', emoji: '🧙', name: 'Professor', blurb: 'Writing the lesson for your level' },
  { status: 'explain', emoji: '🎬', name: 'Animator', blurb: 'Choreographing your custom animation' },
];

/**
 * The "invisible pipeline" screen: chains /advance calls from `new` (or wherever
 * the session is) all the way to `visualize` while the user watches a friendly
 * progress animation. No agent output is ever dumped as text.
 */
export default function Forging({ token, session, initialAnswer, onSession, onDone, onError }) {
  const [current, setCurrent] = useState(() =>
    Math.max(0, STAGES.findIndex((s) => s.status === session.session_status))
  );
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      let s = session;
      let answer = initialAnswer ?? null;
      let guard = 0;
      while (s.session_status !== 'visualize' && guard++ < 6) {
        const idx = Math.max(0, STAGES.findIndex((st) => st.status === s.session_status));
        setCurrent(idx);
        // Let the animation breathe a beat before revealing the next stage.
        await new Promise((r) => setTimeout(r, 700));
        s = await api.advance(token, s.session_id, answer);
        answer = null;
        setCurrent(idx + 1);
        onSession(s);
      }
      if (s.session_status === 'visualize') {
        onDone(s);
      } else {
        onError('The pipeline took a wrong turn — please try again.');
      }
    })().catch((e) => onError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fade-in" style={{ maxWidth: 560, margin: '40px auto', textAlign: 'center' }}>
      <div style={{ fontSize: 54, marginBottom: 4 }}>🏗️</div>
      <h2 style={{ fontWeight: 900, fontSize: 26, margin: '0 0 6px' }}>Building your lesson…</h2>
      <p style={{ color: 'var(--ink-mid)', fontWeight: 700, margin: '0 0 26px' }}>
        Four agents are working on <b>{session.active_topic}</b> just for you.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {STAGES.map((st, i) => {
          const done = i < current;
          const active = i === current;
          return (
            <div
              key={st.status}
              className="card"
              style={{
                display: 'flex', alignItems: 'center', gap: 14, padding: '14px 18px', textAlign: 'left',
                opacity: done || active ? 1 : 0.45,
                border: active ? '2px solid var(--blue)' : '2px solid transparent',
                transition: 'all 0.3s',
              }}
            >
              <span
                style={{
                  flex: 'none', width: 44, height: 44, borderRadius: 14, display: 'grid', placeItems: 'center',
                  fontSize: 23, background: done ? 'var(--green-soft)' : active ? 'var(--blue-soft)' : '#f0f0f0',
                }}
              >
                {done ? <Check size={22} color="var(--green)" /> : st.emoji}
              </span>
              <span style={{ flex: 1 }}>
                <span style={{ display: 'block', fontWeight: 900, fontSize: 15.5 }}>{st.name}</span>
                <span style={{ display: 'block', fontWeight: 700, fontSize: 13, color: 'var(--ink-mid)' }}>{st.blurb}</span>
              </span>
              {active && <span className="spinner" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
