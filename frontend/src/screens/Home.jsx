import { useState } from 'react';
import { Sparkles, Search, ArrowRight } from 'lucide-react';
import { TOPICS, EXAMPLE_CHIPS } from '../data/topics';
import { Mascot } from '../components/ui.jsx';

export default function Home({ onStartConcept, onStartCustom, busy, busyLabel }) {
  const [topic, setTopic] = useState('');

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
      <div style={{ textAlign: 'center', paddingTop: 8 }}>
        <h1 style={{ fontSize: 34, margin: '0 0 6px', fontWeight: 900 }}>
          What do you want to <span style={{ color: 'var(--green)' }}>watch</span> today?
        </h1>
        <p style={{ color: 'var(--ink-mid)', fontWeight: 700, margin: 0 }}>
          Any topic becomes an animated, interactive lesson — tuned to what you already know.
        </p>
      </div>

      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14, padding: 26 }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <span
            style={{
              flex: 'none', width: 52, height: 52, borderRadius: 16, display: 'grid', placeItems: 'center',
              fontSize: 26, background: 'linear-gradient(135deg,#1cb0f6,#ce82ff)', boxShadow: '0 3px 0 var(--blue-shadow)',
            }}
          >
            ✨
          </span>
          <div>
            <div style={{ fontWeight: 900, fontSize: 18 }}>Learn Anything</div>
            <div style={{ color: 'var(--ink-mid)', fontWeight: 700, fontSize: 13.5 }}>
              Type any topic — photosynthesis, WiFi, inflation — and watch it animate.
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <input
            className="field"
            style={{ flex: 1, minWidth: 220 }}
            placeholder="e.g. How do black holes form?"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && topic.trim() && onStartCustom(topic.trim())}
          />
          <button className="btn3d green" disabled={!topic.trim() || busy} onClick={() => onStartCustom(topic.trim())}>
            <Sparkles size={17} /> {busy && busyLabel === 'custom' ? 'Synthesizing…' : 'Build my lesson'}
          </button>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {EXAMPLE_CHIPS.map((c) => (
            <button key={c} className="pill blue" style={{ border: 'none' }} onClick={() => onStartCustom(c.replace(/\s*[\u{1F300}-\u{1FAFF}]\s*/gu, ''))}>
              {c}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '4px 0 12px' }}>
          <Search size={18} color="var(--ink-mid)" />
          <span style={{ fontWeight: 900, fontSize: 17 }}>Or pick a classic</span>
          <span className="pill purple">interview favorites</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))', gap: 14 }}>
          {TOPICS.map((t) => (
            <button
              key={t.id}
              className="card choice"
              style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 8, padding: 18 }}
              disabled={busy}
              onClick={() => onStartConcept(t.id)}
            >
              <span
                style={{
                  width: 46, height: 46, borderRadius: 14, display: 'grid', placeItems: 'center',
                  fontSize: 24, background: t.grad, boxShadow: '0 3px 0 rgba(0,0,0,0.15)',
                }}
              >
                {t.emoji}
              </span>
              <span style={{ fontWeight: 900, fontSize: 16.5 }}>{t.title}</span>
              <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--ink-mid)', textAlign: 'left' }}>{t.blurb}</span>
              {busy && busyLabel === t.id && <span style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--blue-d)' }}>Preparing…</span>}
              {!busy && (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12.5, fontWeight: 900, color: 'var(--green)' }}>
                  Start <ArrowRight size={13} />
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <Mascot text="Psst — the warm-up quiz is 3 quick taps, and it's not graded. It just tells me what to skip and what to actually show you." />
    </div>
  );
}
