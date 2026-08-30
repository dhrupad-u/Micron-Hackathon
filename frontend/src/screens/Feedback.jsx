import { ArrowRight } from 'lucide-react';
import { Mascot, ScoreRing } from '../components/ui.jsx';

export default function Feedback({ session, onContinue, busy }) {
  const ev = session.interaction_state?.latest_evaluation || {};
  const score = Math.round((ev.score ?? 0) * 100);
  const passed = !!ev.passed;
  const myths = ev.misconception_detected || [];

  const headline = passed ? 'You cracked it! 🎉' : 'Almost there — and now we know exactly where to dig.';
  const quality = ev.reasoning_quality || '';

  return (
    <div className="fade-in" style={{ maxWidth: 640, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ textAlign: 'center' }}>
        <h2 style={{ margin: 0, fontWeight: 900, fontSize: 26 }}>Your reasoning report</h2>
        <p style={{ color: 'var(--ink-mid)', fontWeight: 700, margin: '4px 0 0' }}>
          Graded against the topic's ground truth — not keywords.
        </p>
      </div>

      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap', justifyContent: 'center', padding: 26 }}>
        <ScoreRing value={(ev.score ?? 0)} label="reasoning" />
        <div style={{ flex: 1, minWidth: 220 }}>
          <span className={`pill ${passed ? 'green' : 'yellow'}`}>{passed ? '✅ PASSED' : '🔁 needs another lap'}</span>
          <div style={{ fontWeight: 900, fontSize: 19, margin: '8px 0 6px' }}>{headline}</div>
          {quality && (
            <div style={{ fontWeight: 700, fontSize: 13.5, color: 'var(--ink-mid)' }}>Reasoning quality: {quality}</div>
          )}
        </div>
      </div>

      {myths.length > 0 && (
        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontWeight: 900, fontSize: 16, marginBottom: 10 }}>🚫 Myths we just busted</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {myths.map((m, i) => (
              <div key={i} style={{ background: 'var(--red-soft)', borderRadius: 12, padding: '10px 14px', fontWeight: 700, fontSize: 14 }}>
                {m}
              </div>
            ))}
          </div>
        </div>
      )}

      {ev.feedback && (
        <div className="card" style={{ padding: 18, borderLeft: '5px solid var(--blue)' }}>
          <div style={{ fontWeight: 900, marginBottom: 4 }}>📝 Coach's notes</div>
          <p style={{ margin: 0, fontWeight: 700, fontSize: 14.5, lineHeight: 1.55, color: 'var(--ink)' }}>{ev.feedback}</p>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button className="btn3d green big" onClick={onContinue} disabled={busy}>
          {busy ? 'Deciding next step…' : 'What\'s next?'} <ArrowRight size={17} />
        </button>
      </div>
    </div>
  );
}
