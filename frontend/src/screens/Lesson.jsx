import { useState } from 'react';
import { ArrowRight, BookOpen, Cpu, Globe, Key, AlertTriangle } from 'lucide-react';
import { Mascot } from '../components/ui.jsx';
import { staticUrl } from '../api.js';
import { topicEmoji } from '../data/topics';

export default function Lesson({ token, session, onContinue }) {
  const concept = session.concept_history?.[0];
  const brief = session.metadata?.topic_brief;
  const hero = staticUrl(session.metadata?.hero_image_url);
  const [flipped, setFlipped] = useState({});

  if (!concept) return null;

  // Extract rich narrative sections
  const intuition =
    concept.narrative_intuition ||
    brief?.narrative_intuition ||
    concept.canonical_definition ||
    '';

  const mechanism =
    concept.deep_mechanism ||
    brief?.deep_mechanism ||
    brief?.example_walkthrough ||
    concept.explanation_summary ||
    '';

  const scenario =
    concept.real_world_scenario ||
    brief?.real_world_scenario ||
    (brief?.explanation_depths && brief.explanation_depths[2]) ||
    '';

  const facts = (concept.key_facts || []).filter((f) => f && f.length > 5).slice(0, 4);
  const pitfalls = (concept.common_pitfalls || brief?.common_pitfalls || concept.misconceptions || []).slice(0, 3);

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 22, maxWidth: 900, margin: '0 auto' }}>
      {/* Hero Banner */}
      <div
        style={{
          borderRadius: 24, overflow: 'hidden', border: '3px solid rgba(0,0,0,0.08)', minHeight: 180,
          display: 'flex', alignItems: 'flex-end', position: 'relative',
          background: hero
            ? `center/cover url("${hero}")`
            : 'linear-gradient(120deg,#1cb0f6,#ce82ff)',
        }}
      >
        {!hero && (
          <span style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', fontSize: 72, opacity: 0.9 }}>
            {topicEmoji(session.active_topic)}
          </span>
        )}
        <div
          style={{
            background: 'linear-gradient(180deg, transparent 0%, rgba(0,0,0,0.75) 100%)', padding: '32px 28px 20px',
            width: '100%', color: '#fff',
          }}
        >
          <span className="pill yellow" style={{ marginBottom: 8, fontWeight: 900, textTransform: 'uppercase', tracking: '0.05em' }}>
            Comprehensive Conceptual Deep Dive
          </span>
          <h1 style={{ margin: 0, fontWeight: 900, fontSize: 30, textShadow: '0 2px 10px rgba(0,0,0,0.5)' }}>
            {concept.title}
          </h1>
        </div>
      </div>

      {/* 1. Core Intuition & Big Picture */}
      <div className="card" style={{ padding: 26, borderLeft: '6px solid var(--blue)', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 36, height: 36, borderRadius: 12, display: 'grid', placeItems: 'center', background: 'var(--blue-soft)' }}>
            <BookOpen size={20} color="var(--blue)" />
          </span>
          <h3 style={{ margin: 0, fontWeight: 900, fontSize: 20 }}>1. The Big Picture & Intuition</h3>
        </div>
        <div style={{ fontWeight: 600, fontSize: 15.5, lineHeight: 1.7, color: 'var(--ink)', whiteSpace: 'pre-line' }}>
          {intuition}
        </div>
      </div>

      {/* 2. How it Works — Deep Mechanism */}
      {mechanism && (
        <div className="card" style={{ padding: 26, borderLeft: '6px solid var(--yellow)', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ width: 36, height: 36, borderRadius: 12, display: 'grid', placeItems: 'center', background: 'var(--yellow-soft)' }}>
              <Cpu size={20} color="var(--yellow)" />
            </span>
            <h3 style={{ margin: 0, fontWeight: 900, fontSize: 20 }}>2. How it Works (The Step-by-Step Mechanism)</h3>
          </div>
          <div style={{ fontWeight: 600, fontSize: 15.5, lineHeight: 1.7, color: 'var(--ink)', whiteSpace: 'pre-line' }}>
            {mechanism}
          </div>
        </div>
      )}

      {/* 3. Real-World Scenario */}
      {scenario && (
        <div className="card" style={{ padding: 26, borderLeft: '6px solid var(--green)', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ width: 36, height: 36, borderRadius: 12, display: 'grid', placeItems: 'center', background: 'var(--green-soft)' }}>
              <Globe size={20} color="var(--green)" />
            </span>
            <h3 style={{ margin: 0, fontWeight: 900, fontSize: 20 }}>3. Real-World Scenario & Impact</h3>
          </div>
          <div style={{ fontWeight: 600, fontSize: 15.5, lineHeight: 1.7, color: 'var(--ink)', whiteSpace: 'pre-line' }}>
            {scenario}
          </div>
        </div>
      )}

      {/* 4. Core Principles & Key Facts (Interactive reveal) */}
      {facts.length > 0 && (
        <div className="card" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Key size={20} color="var(--purple)" />
            <h3 style={{ margin: 0, fontWeight: 900, fontSize: 19 }}>Key Core Principles (Tap to reveal details)</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {facts.map((f, i) => (
              <button
                key={i}
                className={`choice ${flipped[i] ? 'right' : ''}`}
                style={{ textAlign: 'left', padding: '14px 18px', fontSize: 15, fontWeight: 700 }}
                onClick={() => setFlipped((p) => ({ ...p, [i]: !p[i] }))}
              >
                <span className="key" style={{ marginRight: 10 }}>{flipped[i] ? '✓' : `Fact ${i + 1}`}</span>
                <span>{flipped[i] ? f : `Tap to view Core Principle #${i + 1}`}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 5. Common Traps & Pitfalls */}
      {pitfalls.length > 0 && (
        <div className="card" style={{ padding: 22, background: '#fff5f5', border: '2px solid var(--red-soft)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <AlertTriangle size={20} color="var(--red)" />
            <h4 style={{ margin: 0, fontWeight: 900, fontSize: 17, color: 'var(--red)' }}>Common Pitfalls & Misconceptions</h4>
          </div>
          <ul style={{ margin: 0, paddingLeft: 22, color: 'var(--ink)', fontWeight: 700, fontSize: 14.5, lineHeight: 1.6 }}>
            {pitfalls.map((p, i) => (
              <li key={i} style={{ marginBottom: 6 }}>{p}</li>
            ))}
          </ul>
        </div>
      )}

      {/* DeepBot Assistant Component */}
      <Mascot
        token={token}
        session={session}
        screen="lesson"
        text="Read through these sections carefully. If anything feels unclear, tap 'Ask a doubt' on my bubble and I'll explain it in 1 sentence!"
      />

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
        <button className="btn3d green big" onClick={onContinue} style={{ fontSize: 18, padding: '14px 32px' }}>
          Watch the Interactive Animation <ArrowRight size={22} />
        </button>
      </div>
    </div>
  );
}
