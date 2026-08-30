import { useState } from 'react';
import { Lightbulb, Send } from 'lucide-react';
import { Mascot } from '../components/ui.jsx';

export default function Challenge({ token, session, onSubmit, busy }) {
  const [answer, setAnswer] = useState('');
  const [hintLevel, setHintLevel] = useState(0);

  const exercise = session.practice_history?.[0]?.exercises?.[0];
  const question = session.interaction_state?.current_question || exercise?.prompt || '';
  const hints = exercise?.hints || [];
  const frozenScene = session.interaction_state?.current_visualization?.scene;
  const frozenCaption =
    frozenScene && frozenScene.steps?.length
      ? frozenScene.steps[frozenScene.steps.length - 1].caption
      : '';

  return (
    <div className="fade-in" style={{ maxWidth: 680, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ textAlign: 'center' }}>
        <span className="pill purple">Final challenge</span>
        <h2 style={{ margin: '10px 0 4px', fontWeight: 900, fontSize: 26 }}>🧠 Prove the mechanism</h2>
        <p style={{ color: 'var(--ink-mid)', fontWeight: 700, margin: 0 }}>
          This one <i>is</i> graded — by an AI that reads your reasoning, not just keywords.
        </p>
      </div>

      {frozenCaption && (
        <div className="caption-bar" style={{ opacity: 0.85 }}>
          <span className="stepchip">recap</span>
          <span>{frozenCaption}</span>
        </div>
      )}

      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: 24 }}>
        <div style={{ fontWeight: 900, fontSize: 18, lineHeight: 1.45 }}>{question}</div>
        <textarea
          className="field"
          rows={5}
          placeholder="Explain the mechanism in your own words — the 'why' matters more than the words…"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
        />
        {hintLevel > 0 && (
          <div className="fade-in" style={{ background: 'var(--yellow-soft)', borderRadius: 14, padding: '12px 16px', fontWeight: 700, fontSize: 14 }}>
            💡 {hints[hintLevel - 1]}
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          {hintLevel < hints.length ? (
            <button className="btn3d yellow" onClick={() => setHintLevel((h) => h + 1)}>
              <Lightbulb size={16} /> Give me a hint
            </button>
          ) : (
            <span />
          )}
          <button className="btn3d green big" disabled={!answer.trim() || busy} onClick={() => onSubmit(answer.trim())}>
            {busy ? 'Grading…' : 'Submit answer'} <Send size={16} />
          </button>
        </div>
      </div>

      <Mascot
        token={token}
        session={session}
        screen="challenge"
        text="Talk like you're explaining it to a friend. Need a quick hint or doubt check? Ask DeepBot!"
      />
    </div>
  );
}
