// Curated DSA topic cards shown on the home grid.
export const TOPICS = [
  {
    id: 'two-sum-hashmap',
    emoji: '🎯',
    title: 'Two Sum',
    blurb: 'Find the pair that hits the target — the smart way.',
    grad: 'linear-gradient(135deg,#1cb0f6,#ce82ff)',
  },
  {
    id: 'contains-duplicate',
    emoji: '🔍',
    title: 'Contains Duplicate',
    blurb: 'Spot repeats without checking everything twice.',
    grad: 'linear-gradient(135deg,#58cc02,#1cb0f6)',
  },
  {
    id: 'valid-anagram',
    emoji: '🔤',
    title: 'Valid Anagram',
    blurb: 'Same letters, same counts — prove it fast.',
    grad: 'linear-gradient(135deg,#ffc800,#ff9600)',
  },
  {
    id: 'best-time-stock',
    emoji: '📈',
    title: 'Best Time to Buy & Sell',
    blurb: 'Buy low, sell high, one pass, no regret.',
    grad: 'linear-gradient(135deg,#ff9600,#ff4b4b)',
  },
  {
    id: 'max-subarray',
    emoji: '🏔️',
    title: 'Max Subarray',
    blurb: "Kadane's trick: drop the baggage, keep the gain.",
    grad: 'linear-gradient(135deg,#ce82ff,#ff4b4b)',
  },
  {
    id: 'valid-parentheses',
    emoji: '🧩',
    title: 'Valid Parentheses',
    blurb: 'Brackets must close in reverse order. Stack it.',
    grad: 'linear-gradient(135deg,#1cb0f6,#58cc02)',
  },
];

export const EXAMPLE_CHIPS = ['Photosynthesis 🌱', 'How WiFi works 📡', 'Supply & demand 📦', 'Recursion 🔄'];

export function topicEmoji(title = '') {
  const t = title.toLowerCase();
  if (t.includes('sum')) return '🎯';
  if (t.includes('duplicate')) return '🔍';
  if (t.includes('anagram')) return '🔤';
  if (t.includes('stock') || t.includes('buy')) return '📈';
  if (t.includes('subarray')) return '🏔️';
  if (t.includes('paren') || t.includes('bracket')) return '🧩';
  return '✨';
}
