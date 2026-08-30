import { useEffect, useState } from 'react';
import { LogOut } from 'lucide-react';

export function TopBar({ user, xp, onHome, onSignOut }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <button className="brand" onClick={onHome}>
          <span className="logo">🤿</span>
          <span>
            Deep<em>Dive</em>
          </span>
        </button>
        <span className="spacer" />
        <span className="xp-pill">⚡ {xp} XP</span>
        {user && <span className="user-chip">Hi, {user}!</span>}
        <button className="btn3d ghost" style={{ padding: '9px 14px', fontSize: 14 }} onClick={onSignOut}>
          <LogOut size={16} /> Log out
        </button>
      </div>
    </header>
  );
}

import { MessageSquare, Send, Sparkles } from 'lucide-react';
import { api } from '../api.js';

export function Mascot({ text, children, token, session, screen = 'lesson' }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [aiResponse, setAiResponse] = useState(null);
  const [chips, setChips] = useState(['💡 Explain simpler', '❓ Why does this work?', '🔍 Everyday example']);

  async function handleAsk(query) {
    const q = (query || input).trim();
    if (!q || loading) return;
    if (!token || !session?.session_id) {
      setAiResponse(`DeepBot: ${text || children || "I'm here to help!"}`);
      return;
    }
    setLoading(true);
    try {
      const res = await api.askChatbot(token, session.session_id, q, screen);
      if (res?.reply) {
        setAiResponse(res.reply);
        if (res.suggested_followups && res.suggested_followups.length > 0) {
          setChips(res.suggested_followups);
        }
      }
    } catch {
      setAiResponse('DeepBot is thinking — focus on the core mechanism for this step!');
    } finally {
      setLoading(false);
      setInput('');
    }
  }

  const currentSpeech = aiResponse || text || children;

  return (
    <div className="mascot-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
      <div className="mascot" style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        <button
          onClick={() => setOpen((o) => !o)}
          title="Click to ask DeepBot a question!"
          style={{
            background: 'none', border: 'none', padding: 0, cursor: 'pointer',
            transform: open ? 'scale(1.1) rotate(-4deg)' : 'none', transition: 'transform 0.2s',
          }}
        >
          <div className="face" style={{ fontSize: 38 }}>🦉</div>
        </button>
        <div className="bubble" style={{ flex: 1, position: 'relative' }}>
          <div style={{ fontWeight: 800, fontSize: 14, color: 'var(--ink)', lineHeight: 1.5 }}>
            {currentSpeech}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8, paddingTop: 6, borderTop: '1px solid rgba(0,0,0,0.06)' }}>
            <span style={{ fontSize: 11.5, fontWeight: 800, color: 'var(--ink-mid)' }}>
              🦉 DeepBot AI Companion
            </span>
            <button
              className="pill blue"
              style={{ fontSize: 11.5, padding: '3px 10px', border: 'none', cursor: 'pointer' }}
              onClick={() => setOpen((o) => !o)}
            >
              {open ? 'Close Chat' : '💬 Ask a doubt'}
            </button>
          </div>
        </div>
      </div>

      {open && (
        <div
          className="card fade-in"
          style={{
            marginLeft: 52, padding: 14, background: 'var(--blue-soft)', border: '2px solid var(--blue)',
            borderRadius: 16, display: 'flex', flexDirection: 'column', gap: 10,
          }}
        >
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {chips.map((chip, i) => (
              <button
                key={i}
                className="pill yellow"
                style={{ cursor: 'pointer', border: 'none', fontSize: 12, padding: '5px 10px' }}
                onClick={() => handleAsk(chip.replace(/^[^\w]+/, ''))}
                disabled={loading}
              >
                {chip}
              </button>
            ))}
          </div>

          <form
            onSubmit={(e) => { e.preventDefault(); handleAsk(); }}
            style={{ display: 'flex', gap: 8, alignItems: 'center' }}
          >
            <input
              type="text"
              className="field"
              placeholder="Ask DeepBot any doubt..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              style={{ flex: 1, padding: '8px 12px', fontSize: 13.5, borderRadius: 12 }}
            />
            <button
              className="btn3d blue"
              type="submit"
              disabled={loading || !input.trim()}
              style={{ padding: '8px 14px', fontSize: 13 }}
            >
              {loading ? '...' : <Send size={15} />}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

export function ScoreRing({ value, size = 130, label = 'Score' }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setShown(value), 120);
    return () => clearTimeout(t);
  }, [value]);
  const r = (size - 16) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, shown));
  const color = pct >= 0.8 ? 'var(--green)' : pct >= 0.5 ? 'var(--yellow)' : 'var(--red)';
  return (
    <div style={{ position: 'relative', width: size, height: size, flex: 'none' }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e9e9e9" strokeWidth="12" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          style={{ transition: 'stroke-dashoffset 1.1s cubic-bezier(.22,1,.36,1), stroke 0.4s', transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
        />
      </svg>
      <div
        style={{
          position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', fontWeight: 900,
        }}
      >
        <span style={{ fontSize: size * 0.26 }}>{Math.round(value * 100)}</span>
        <span style={{ fontSize: 12, color: 'var(--ink-mid)', fontWeight: 800 }}>{label}</span>
      </div>
    </div>
  );
}

export function ProgressTrack({ value }) {
  return (
    <div className="track">
      <div style={{ width: `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%` }} />
    </div>
  );
}

export function Spinner() {
  return <span className="spinner" />;
}

export function shuffleWithAnswer(options, correctIndex) {
  const idx = options.map((_, i) => i);
  for (let i = idx.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [idx[i], idx[j]] = [idx[j], idx[i]];
  }
  return { order: idx, newCorrect: idx.indexOf(correctIndex) };
}

export function awardXP(amount) {
  const cur = parseInt(localStorage.getItem('dd_xp') || '0', 10);
  const next = cur + amount;
  localStorage.setItem('dd_xp', String(next));
  return next;
}

export function fireConfetti() {
  import('canvas-confetti').then(({ default: confetti }) => {
    const shoot = (x, angle) =>
      confetti({ particleCount: 90, spread: 70, origin: { x, y: 0.7 }, angle, colors: ['#58cc02', '#1cb0f6', '#ffc800', '#ce82ff', '#ff9600'] });
    shoot(0.2, 60);
    shoot(0.8, 120);
    setTimeout(() => shoot(0.5, 90), 250);
  });
}
