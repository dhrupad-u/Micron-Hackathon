import { useEffect } from 'react';
import { Home, RotateCcw } from 'lucide-react';
import { Mascot, ScoreRing, fireConfetti } from '../components/ui.jsx';
import { staticUrl } from '../api.js';
import { topicEmoji } from '../data/topics';

export default function Summary({ session, onHome, onReplay, xpGained }) {
  const ev = session.interaction_state?.latest_evaluation || {};
  const score = ev.score ?? 0;
  const passed = !!ev.passed;
  const hero = staticUrl(session.metadata?.hero_image_url);

  useEffect(() => {
    if (passed) fireConfetti();
  }, [passed]);

  return (
    <div className="fade-in" style={{ maxWidth: 660, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div
        style={{
          borderRadius: 20, overflow: 'hidden', border: '3px solid rgba(0,0,0,0.08)', minHeight: 150, position: 'relative',
          display: 'grid', placeItems: 'center',
          background: hero ? `center/cover url("${hero}")` : 'linear-gradient(120deg,#58cc02,#1cb0f6)',
        }}
      >
        {!hero && <span style={{ fontSize: 62 }}>{topicEmoji(session.active_topic)}</span>}
        <span
          className="pill yellow"
          style={{ position: 'absolute', top: 14, left: 14, background: 'rgba(255,255,255,0.95)' }}
        >
          {passed ? 'quest complete' : 'quest logged'}
        </span>
      </div>

      <div style={{ textAlign: 'center' }}>
        <h2 style={{ margin: 0, fontWeight: 900, fontSize: 28 }}>{passed ? 'Mastery achieved! 🏆' : 'Progress banked 💪'}</h2>
        <p style={{ color: 'var(--ink-mid)', fontWeight: 700, margin: '4px 0 0' }}>{session.active_topic}</p>
      </div>

      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap', justifyContent: 'center', padding: 24 }}>
        <ScoreRing value={score} label="mastery" />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 200 }}>
          <div className="pill yellow" style={{ fontSize: 15 }}>⚡ +{xpGained} XP earned</div>
          <div className="pill blue" style={{ fontSize: 15 }}>🎯 {Math.round(score * 100)}% reasoning score</div>
          <div className="pill green" style={{ fontSize: 15 }}>
            {session.student_answers?.length || 0} answers graded by AI
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: 18, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center' }}>
        <button className="btn3d green big" onClick={onHome}>
          <Home size={17} /> Learn something else
        </button>
        <button className="btn3d ghost big" onClick={onReplay}>
          <RotateCcw size={17} /> Replay this lesson
        </button>
      </div>

      <Mascot
        text={
          passed
            ? 'That animation is yours forever now. Try explaining today\u2019s topic to someone — best XP there is.'
            : 'Every wrong turn today made the next animation smarter. Come back anytime — I remember nothing, but you will.'
        }
      />
    </div>
  );
}
