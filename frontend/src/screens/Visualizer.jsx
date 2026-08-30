import { useEffect, useMemo, useRef, useState } from 'react';
import { Play, Pause, SkipBack, SkipForward, RotateCcw, ArrowRight, Target, Info, Eye } from 'lucide-react';
import ScenePlayer from '../viz/ScenePlayer.jsx';
import { captionAt, sceneLength } from '../viz/sceneEngine.js';
import { Mascot } from '../components/ui.jsx';
import { api } from '../api.js';

function predictOptions(scene, atStep) {
  const captions = (scene?.steps || []).map((s) => s.caption || '');
  const correct = captions[atStep + 1];
  if (!correct) return null;
  const others = captions
    .map((c, i) => ({ c, i }))
    .filter(({ c, i }) => c && i !== atStep + 1 && c !== correct);
  const pool = others.sort(() => Math.random() - 0.5).slice(0, 2).map(({ c }) => c);
  const opts = [...pool, correct].sort(() => Math.random() - 0.5);
  return { options: opts, correct };
}

export default function Visualizer({ token, session, round, adaptNote, onContinue, onError }) {
  const concept = session.concept_history?.[0];
  const brief = session.metadata?.topic_brief;
  const isCustom = !!brief;
  const optSpec = session.interaction_state?.current_visualization;
  const bfSpec = session.interaction_state?.current_visualization_bf;

  // Show duel ONLY when we have two distinct valid visualization specs
  const duel = bfSpec?.scene?.steps?.length > 0 && optSpec?.scene?.steps?.length > 0;

  const methods = concept?.methods || [];
  const naiveMethod = methods.find((m) => /brute|naive|approach-1|basic/i.test(m.id + m.name)) || methods[0];
  const cleverMethod = methods.find((m) => m !== naiveMethod) || methods[1];
  const naiveBadge = naiveMethod ? `🐢 ${naiveMethod.name}` : '🐢 Initial approach';
  const cleverBadge = cleverMethod ? `⚡ ${cleverMethod.name}` : '⚡ Better approach';

  const [stepIndex, setStepIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [predict, setPredict] = useState(null);
  const [predictDone, setPredictDone] = useState(false);
  const [checkpoint, setCheckpoint] = useState(false);
  const [answers, setAnswers] = useState({});
  const [saved, setSaved] = useState(false);
  const predictFired = useRef(false);

  const mainScene = optSpec?.scene;
  const total = Math.max(sceneLength(mainScene), duel ? sceneLength(bfSpec?.scene) : 0, 1);
  const atEnd = stepIndex >= total - 1;

  const checkpointQuestions = useMemo(
    () => (optSpec?.questions || []).slice(0, 2),
    [optSpec]
  );

  // Playback ticker
  useEffect(() => {
    if (!playing || predict) return;
    const t = setTimeout(() => {
      setStepIndex((i) => {
        const next = i + 1;
        if (next >= total) {
          setPlaying(false);
          return i;
        }
        return next;
      });
    }, 2400 / speed);
    return () => clearTimeout(t);
  }, [playing, stepIndex, speed, predict, total]);

  // Fire predict moment
  useEffect(() => {
    if (!playing || predictFired.current || total < 4 || stepIndex !== Math.floor(total / 2) - 1) return;
    const p = predictOptions(mainScene, stepIndex);
    if (p) {
      predictFired.current = true;
      setPredict({ ...p, picked: null });
    }
  }, [playing, stepIndex, total, mainScene]);

  useEffect(() => {
    if (atEnd && !playing) setCheckpoint(true);
  }, [atEnd, playing]);

  function pickPredict(opt) {
    if (predict.picked != null) return;
    setPredict({ ...predict, picked: opt });
    setTimeout(() => {
      setPredict(null);
      setPredictDone(true);
    }, 1600);
  }

  async function submitCheckpoint() {
    try {
      for (const q of checkpointQuestions) {
        const ans = (answers[q.id] || '').trim();
        if (ans) await api.submitAnswer(token, session.session_id, q.id, ans);
      }
      setSaved(true);
      setTimeout(() => onContinue(), 500);
    } catch (e) {
      onError(e.message);
    }
  }

  const inputDisplay = brief?.input_display || concept?.title || session.active_topic;
  const targetWalkthrough = brief?.example_walkthrough || concept?.canonical_definition;
  const actors = mainScene?.actors || [];
  const currentStepCaption = captionAt(mainScene, Math.min(stepIndex, sceneLength(mainScene) - 1));

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 18, maxWidth: 960, margin: '0 auto' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0, fontWeight: 900, fontSize: 26 }}>🎬 Step-by-Step Visualizer</h2>
        {round > 1 && <span className="pill purple">Round {round}</span>}
        {duel ? (
          <span className="pill blue">Dual Approach Comparison</span>
        ) : (
          <span className="pill green">Single High-Def Canvas</span>
        )}
      </div>

      {adaptNote && (
        <div className="card" style={{ padding: '12px 18px', borderLeft: '5px solid var(--purple)', fontWeight: 700, fontSize: 14 }}>
          🧭 {adaptNote}
        </div>
      )}

      {/* Problem & Target Context Card */}
      <div className="card" style={{ padding: 20, background: 'var(--blue-soft)', border: '2px solid var(--blue)', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 900, fontSize: 16, color: 'var(--ink)' }}>
          <Target size={18} color="var(--blue)" />
          <span>What We Are Modeling & Solving</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 12, fontSize: 14, fontWeight: 700 }}>
          <div style={{ background: '#fff', padding: '10px 14px', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)' }}>
            <span style={{ color: 'var(--ink-mid)', fontSize: 12, textTransform: 'uppercase', display: 'block' }}>Initial Input / System State</span>
            <span style={{ color: 'var(--ink)', fontSize: 14.5 }}>{inputDisplay}</span>
          </div>
          <div style={{ background: '#fff', padding: '10px 14px', borderRadius: 12, border: '1px solid rgba(0,0,0,0.06)' }}>
            <span style={{ color: 'var(--ink-mid)', fontSize: 12, textTransform: 'uppercase', display: 'block' }}>Goal & Expected Outcome</span>
            <span style={{ color: 'var(--ink)', fontSize: 14.5 }}>{targetWalkthrough ? targetWalkthrough.slice(0, 110) + '...' : 'Reach verified solution'}</span>
          </div>
        </div>
      </div>

      {/* Visual Actor Legend */}
      {actors.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', background: '#fff', padding: '10px 16px', borderRadius: 14, border: '1px solid rgba(0,0,0,0.08)' }}>
          <span style={{ fontWeight: 900, fontSize: 13, color: 'var(--ink-mid)', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Eye size={15} /> Visual Elements on Stage:
          </span>
          {actors.map((a) => (
            <span key={a.id} className="pill" style={{ background: '#f5f5f7', color: 'var(--ink)', fontSize: 12.5, fontWeight: 800 }}>
              {a.icon || '🔘'} {a.label || a.id}
            </span>
          ))}
        </div>
      )}

      {/* Stage Canvas Area */}
      {duel ? (
        <div className="duel" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <StagePanel badge={naiveBadge} color="var(--red)" soft="var(--red-soft)" scene={bfSpec.scene} stepIndex={Math.min(stepIndex, sceneLength(bfSpec.scene) - 1)} />
          <StagePanel badge={cleverBadge} color="var(--green)" soft="var(--green-soft)" scene={mainScene} stepIndex={Math.min(stepIndex, sceneLength(mainScene) - 1)} />
        </div>
      ) : (
        <div style={{ border: '3px solid rgba(0,0,0,0.1)', borderRadius: 20, overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.06)' }}>
          <ScenePlayer scene={mainScene} stepIndex={stepIndex} />
        </div>
      )}

      {/* Active Step Breakdown Panel */}
      <div className="card" style={{ padding: 18, borderLeft: '6px solid var(--yellow)', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="pill yellow" style={{ fontWeight: 900 }}>Step {Math.min(stepIndex + 1, total)} of {total}</span>
          <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--ink-mid)' }}>Active State Breakdown</span>
        </div>
        <div style={{ fontWeight: 800, fontSize: 16, color: 'var(--ink)', lineHeight: 1.5 }}>
          {currentStepCaption || 'Press Play to start the step-by-step transformation.'}
        </div>
      </div>

      {/* Controls */}
      <div className="player-ctrls" style={{ background: '#fff', padding: 14, borderRadius: 18, border: '1px solid rgba(0,0,0,0.08)' }}>
        <button className="ctl" onClick={() => setStepIndex((i) => Math.max(0, i - 1))} disabled={stepIndex === 0} title="Back">
          <SkipBack size={19} />
        </button>
        <button
          className="ctl primary"
          onClick={() => {
            if (atEnd) {
              setStepIndex(0);
              setPlaying(true);
              setCheckpoint(false);
            } else setPlaying((p) => !p);
          }}
          title={atEnd ? 'Replay' : playing ? 'Pause' : 'Play'}
        >
          {atEnd ? <RotateCcw size={19} /> : playing ? <Pause size={19} /> : <Play size={19} />}
        </button>
        <button
          className="ctl"
          onClick={() => {
            setPlaying(false);
            setStepIndex((i) => Math.min(total - 1, i + 1));
          }}
          disabled={atEnd}
          title="Forward"
        >
          <SkipForward size={19} />
        </button>
        <select className="speed" value={speed} onChange={(e) => setSpeed(+e.target.value)}>
          <option value={0.5}>0.5× speed</option>
          <option value={1}>1.0× speed</option>
          <option value={2}>2.0× speed</option>
        </select>
        <div className="dots" style={{ marginLeft: 'auto' }}>
          {Array.from({ length: total }).map((_, i) => (
            <button
              key={i}
              className={`dot ${i === stepIndex ? 'now' : i < stepIndex ? 'on' : ''}`}
              style={{ border: 'none', padding: 0, cursor: 'pointer' }}
              onClick={() => { setPlaying(false); setStepIndex(i); }}
            />
          ))}
        </div>
      </div>

      {/* Predict overlay */}
      {predict && (
        <div className="card fade-in" style={{ border: '2px solid var(--yellow)', background: 'var(--yellow-soft)', padding: 20 }}>
          <div style={{ fontWeight: 900, fontSize: 17, marginBottom: 4 }}>🔮 Predict! What happens next?</div>
          <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--ink-mid)', marginBottom: 12 }}>
            Just a gut check — no grading here.
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {predict.options.map((opt, i) => {
              const isPick = predict.picked === opt;
              const isRight = opt === predict.correct;
              const cls = predict.picked == null ? 'choice' : isRight ? 'choice right' : isPick ? 'choice wrong' : 'choice';
              return (
                <button key={i} className={cls} disabled={predict.picked != null} onClick={() => pickPredict(opt)}>
                  <span className="key">{'123'[i]}</span> {opt}
                </button>
              );
            })}
          </div>
          {predict.picked != null && (
            <div style={{ marginTop: 10, fontWeight: 900, fontSize: 14 }}>
              {predict.picked === predict.correct ? '✅ Exactly right — watch it play out!' : '👀 Interesting guess — watch closely now…'}
            </div>
          )}
        </div>
      )}

      {/* Checkpoint after playback */}
      {checkpoint && !predict && (
        <div className="card fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 14, padding: 22 }}>
          <div style={{ fontWeight: 900, fontSize: 18 }}>🏁 Checkpoint — Confirm Your Understanding</div>
          {checkpointQuestions.map((q, i) => (
            <div key={q.id} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label style={{ fontWeight: 800, fontSize: 14.5 }}>
                {i + 1}. {q.prompt}
              </label>
              <textarea
                className="field"
                rows={2}
                placeholder="Explain in one or two clear sentences in your own words…"
                value={answers[q.id] || ''}
                onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
              />
            </div>
          ))}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
            <button className="btn3d ghost" onClick={() => { setStepIndex(0); setPlaying(true); setCheckpoint(false); }}>
              <RotateCcw size={16} /> Watch again
            </button>
            <button className="btn3d green" onClick={submitCheckpoint}>
              {saved ? 'Saved ✓' : 'Lock in answers'} <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {!checkpoint && (
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn3d ghost" onClick={() => { setPlaying(false); setCheckpoint(true); }}>
            Skip to checkpoint <ArrowRight size={16} />
          </button>
        </div>
      )}

      <Mascot
        token={token}
        session={session}
        screen="visualizer"
        text={
          predictDone
            ? 'Nice — your predictions match the step-by-step transformation!'
            : 'Press play to watch the system transform step by step. Have questions about an element? Tap my bubble!'
        }
      />
    </div>
  );
}

function StagePanel({ badge, color, soft, scene, stepIndex }) {
  return (
    <div className="stage-wrap" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <span className="pill" style={{ background: soft, color, alignSelf: 'flex-start', fontWeight: 900 }}>{badge}</span>
      <div style={{ border: '2px solid rgba(0,0,0,0.08)', borderRadius: 16, overflow: 'hidden' }}>
        <ScenePlayer scene={scene} stepIndex={stepIndex} />
      </div>
    </div>
  );
}
