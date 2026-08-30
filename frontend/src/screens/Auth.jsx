import { useState } from 'react';
import { Mascot } from '../components/ui.jsx';

export default function Auth({ onAuth }) {
  const [tab, setTab] = useState('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Fill in both fields to keep diving!');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const api = (await import('../api.js')).api;
      const fn = tab === 'login' ? api.login : api.signup;
      const res = await fn(username.trim(), password);
      onAuth(res.token, res.username);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 20 }}>
      <div className="card fade-in" style={{ width: 420, maxWidth: '100%', padding: 30 }}>
        <div style={{ fontSize: 54, textAlign: 'center' }}>🤿</div>
        <h1 style={{ textAlign: 'center', margin: '6px 0 2px', fontSize: 30, fontWeight: 900 }}>
          Deep<span style={{ color: 'var(--blue-d)' }}>Dive</span>
        </h1>
        <p style={{ textAlign: 'center', color: 'var(--ink-mid)', fontWeight: 700, margin: '0 0 18px' }}>
          Learn anything by watching it happen.
        </p>

        <Mascot text="Sign in and I'll turn any topic into an animation — built around what you already know." />

        <div style={{ display: 'flex', gap: 8, margin: '20px 0 14px' }}>
          {['login', 'signup'].map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setError(''); }}
              className={`btn3d ${tab === t ? 'green' : 'ghost'}`}
              style={{ flex: 1, fontSize: 14 }}
            >
              {t === 'login' ? 'I have an account' : "I'm new here"}
            </button>
          ))}
        </div>

        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input
            className="field"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
          <input
            className="field"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
          />
          {error && <div className="err-banner">{error}</div>}
          <button className="btn3d green big" disabled={busy} type="submit">
            {busy ? 'One sec…' : tab === 'login' ? 'Dive in 🌊' : 'Create my account ✨'}
          </button>
        </form>
      </div>
    </div>
  );
}
