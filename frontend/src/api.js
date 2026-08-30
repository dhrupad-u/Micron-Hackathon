const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

async function request(path, { method = 'GET', body, token } = {}) {
  const res = await fetch(API_BASE + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) {
    const err = new Error('Session expired — please sign in again.');
    err.status = 401;
    throw err;
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (data.detail) detail = data.detail;
    } catch { /* keep default */ }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  signup: (username, password) =>
    request('/api/auth/signup', { method: 'POST', body: { username, password } }),
  login: (username, password) =>
    request('/api/auth/login', { method: 'POST', body: { username, password } }),
  startSession: (token, payload) =>
    request('/api/session/start', { method: 'POST', token, body: payload }),
  advance: (token, sessionId, answer = null) =>
    request('/api/session/advance', { method: 'POST', token, body: { session_id: sessionId, answer } }),
  submitAnswer: (token, sessionId, questionId, answer) =>
    request('/api/session/answer', { method: 'POST', token, body: { session_id: sessionId, question_id: questionId, answer } }),
  askChatbot: (token, sessionId, userQuestion, currentScreen = 'general') =>
    request('/api/chat/ask', { method: 'POST', token, body: { session_id: sessionId, user_question: userQuestion, current_screen: currentScreen } }),
};

export const staticUrl = (path) => (path ? API_BASE + path : null);

export function defaultProfile(username) {
  return {
    name: username || 'Explorer',
    current_level: 'beginner',
    goals: ['Understand the mechanism, not just the answer'],
    known_concepts: [],
    difficult_concepts: [],
    time_budget_minutes: 20,
  };
}
