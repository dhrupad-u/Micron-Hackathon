import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './theme.css';
import { api, defaultProfile } from './api.js';
import { TopBar, awardXP } from './components/ui.jsx';
import Auth from './screens/Auth.jsx';
import Home from './screens/Home.jsx';
import Intake from './screens/Intake.jsx';
import Forging from './screens/Forging.jsx';
import Lesson from './screens/Lesson.jsx';
import Visualizer from './screens/Visualizer.jsx';
import Challenge from './screens/Challenge.jsx';
import Feedback from './screens/Feedback.jsx';
import Summary from './screens/Summary.jsx';

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('dd_token'));
  const [user, setUser] = useState(() => localStorage.getItem('dd_user'));
  const [xp, setXp] = useState(() => parseInt(localStorage.getItem('dd_xp') || '0', 10));
  const [screen, setScreen] = useState(() => (localStorage.getItem('dd_token') ? 'home' : 'auth'));
  const [session, setSession] = useState(null);
  const [round, setRound] = useState(0);
  const [adaptNote, setAdaptNote] = useState('');
  const [intakeAnswer, setIntakeAnswer] = useState(null);
  const [busy, setBusy] = useState(false);
  const [busyLabel, setBusyLabel] = useState('');
  const [error, setError] = useState('');
  const [xpGained, setXpGained] = useState(0);

  function handleAuth(t, u) {
    localStorage.setItem('dd_token', t);
    localStorage.setItem('dd_user', u);
    setToken(t);
    setUser(u);
    setScreen('home');
  }

  function signOut() {
    localStorage.removeItem('dd_token');
    localStorage.removeItem('dd_user');
    setToken(null);
    setUser(null);
    setSession(null);
    setScreen('auth');
  }

  async function startLearning(payload, label) {
    setBusy(true);
    setBusyLabel(label);
    setError('');
    try {
      const s = await api.startSession(token, { ...payload, student_profile: defaultProfile(user) });
      setSession(s);
      setRound(1);
      setAdaptNote('');
      setIntakeAnswer(null);
      const quiz = s.metadata?.diagnostic_quiz || [];
      if (quiz.length >= 2) {
        setScreen('intake');
      } else {
        setScreen('forging'); // no quiz → forge straight away (null answer → level-based diagnosis)
      }
    } catch (e) {
      if (e.status === 401) signOut();
      else setError(e.message);
    } finally {
      setBusy(false);
      setBusyLabel('');
    }
  }

  function beginForging(quizAnswerText) {
    setIntakeAnswer(quizAnswerText);
    setScreen('forging');
  }

  function enterVisualize() {
    setScreen('lesson');
  }

  async function nextStep(answer = null) {
    setBusy(true);
    setError('');
    try {
      const s = await api.advance(token, session.session_id, answer);
      setSession(s);
      routeByStatus(s);
    } catch (e) {
      if (e.status === 401) signOut();
      else setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function routeByStatus(s) {
    switch (s.session_status) {
      case 'practice':
        setScreen('challenge');
        break;
      case 'evaluate':
        setScreen('feedback');
        break;
      case 'completed': {
        const ev = s.interaction_state?.latest_evaluation || {};
        const gained = 40 + Math.round((ev.score ?? 0) * 60);
        setXp(awardXP(gained));
        setXpGained(gained);
        setScreen('summary');
        break;
      }
      case 'visualize': {
        // adaptation sent us back for another lap
        setRound((r) => r + 1);
        const decision = s.adaptation_log?.[s.adaptation_log.length - 1];
        setAdaptNote(decision ? `${decision.reason}` : 'One more pass, tuned to what just happened.');
        setScreen('visualize');
        break;
      }
      default:
        break;
    }
  }

  function handleAdaptContinue() {
    // Called from Feedback: run the adaptation agent, then route.
    nextStep();
  }

  function replay() {
    setRound(1);
    setAdaptNote('');
    setXpGained(0);
    setScreen('visualize');
  }

  return (
    <div className="app-shell">
      {screen !== 'auth' && <TopBar user={user} xp={xp} onHome={() => setScreen('home')} onSignOut={signOut} />}
      <main className="app-body">
        {error && (
          <div className="err-banner" style={{ marginBottom: 16 }}>
            {error}{' '}
            <button style={{ border: 'none', background: 'none', fontWeight: 900, color: '#c22', textDecoration: 'underline' }} onClick={() => setError('')}>
              dismiss
            </button>
          </div>
        )}

        {screen === 'auth' && <Auth onAuth={handleAuth} />}

        {screen === 'home' && (
          <Home
            busy={busy}
            busyLabel={busyLabel}
            onStartConcept={(id) => startLearning({ concept_id: id }, id)}
            onStartCustom={(topic) => startLearning({ topic_request: topic }, 'custom')}
          />
        )}

        {screen === 'intake' && session && <Intake token={token} session={session} onDone={beginForging} />}

        {screen === 'forging' && session && (
          <Forging
            token={token}
            session={session}
            initialAnswer={intakeAnswer}
            onSession={setSession}
            onDone={() => setScreen('lesson')}
            onError={setError}
          />
        )}

        {screen === 'lesson' && session && <Lesson token={token} session={session} onContinue={() => setScreen('visualize')} />}

        {screen === 'visualize' && session && (
          <Visualizer
            key={round}
            token={token}
            session={session}
            round={round}
            adaptNote={adaptNote}
            onContinue={() => nextStep()}
            onError={setError}
          />
        )}

        {screen === 'challenge' && session && (
          <Challenge token={token} session={session} busy={busy} onSubmit={(answer) => nextStep(answer)} />
        )}

        {screen === 'feedback' && session && (
          <Feedback session={session} busy={busy} onContinue={handleAdaptContinue} />
        )}

        {screen === 'summary' && session && (
          <Summary
            session={session}
            xpGained={xpGained}
            onHome={() => setScreen('home')}
            onReplay={replay}
          />
        )}

        {screen === 'summary' && !session && <button className="btn3d" onClick={() => setScreen('home')}>Back home</button>}
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
