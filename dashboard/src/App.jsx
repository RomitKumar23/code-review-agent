import { useState, useEffect } from 'react'

const SEVERITY_COLORS = {
  error: '#ef4444',
  warning: '#f59e0b',
  suggestion: '#22c55e',
}

function ReviewCard({ review }) {
  const [expanded, setExpanded] = useState(false)
  const statusColor = {
    done: '#22c55e', running: '#3b82f6', pending: '#94a3b8', failed: '#ef4444'
  }[review.status] || '#94a3b8'

  return (
    <div style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: 16, marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <strong>{review.repo}</strong> — PR #{review.pr_number}
          <div style={{ color: '#64748b', fontSize: 14 }}>{review.pr_title}</div>
        </div>
        <span style={{ background: statusColor, color: '#fff', borderRadius: 4, padding: '2px 8px', fontSize: 12 }}>
          {review.status}
        </span>
      </div>
      {review.summary && (
        <div style={{ marginTop: 8, fontSize: 14, color: '#374151' }}>
          <strong>Provider:</strong> {review.provider} / {review.model} &nbsp;·&nbsp;
          <strong>Tokens:</strong> {review.tokens_used}
        </div>
      )}
      {review.comments?.length > 0 && (
        <button onClick={() => setExpanded(!expanded)} style={{ marginTop: 8, cursor: 'pointer', fontSize: 13 }}>
          {expanded ? '▲ Hide' : '▼ Show'} {review.comments.length} comment(s)
        </button>
      )}
      {expanded && review.comments?.map((c, i) => (
        <div key={i} style={{ marginTop: 6, padding: '6px 10px', borderLeft: `3px solid ${SEVERITY_COLORS[c.severity] || '#94a3b8'}`, background: '#f8fafc', fontSize: 13 }}>
          <code>{c.file}</code> line {c.line} — {c.message}
          {c.suggestion && <div style={{ color: '#0369a1', marginTop: 2 }}>💡 {c.suggestion}</div>}
        </div>
      ))}
    </div>
  )
}

export default function App() {
  const [reviews, setReviews] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/health')
      .then(r => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: 'error' }))

    // In a real app, poll /api/reviews endpoint
    // For now show mock data so the dashboard renders meaningfully
    setReviews([
      {
        id: '1', repo: 'owner/my-app', pr_number: 42,
        pr_title: 'Add user authentication flow',
        status: 'done', provider: 'openai', model: 'gpt-4o',
        tokens_used: 1247, summary: 'Overall solid implementation.',
        comments: [
          { file: 'auth/login.py', line: 34, severity: 'error', message: 'Password compared without hashing', suggestion: 'Use bcrypt.checkpw()' },
          { file: 'auth/login.py', line: 58, severity: 'warning', message: 'Token expiry not set', suggestion: null },
        ]
      },
      {
        id: '2', repo: 'owner/my-app', pr_number: 43,
        pr_title: 'Fix pagination bug',
        status: 'running', provider: 'anthropic', model: 'claude-sonnet-4-6',
        tokens_used: 0, summary: null, comments: []
      }
    ])
    setLoading(false)
  }, [])

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: 24, fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 24 }}>🤖 AI Code Review Agent</h1>
        <span style={{ fontSize: 13, color: health?.status === 'ok' ? '#22c55e' : '#ef4444' }}>
          ● API {health?.status ?? 'connecting...'}
        </span>
      </div>

      <div style={{ background: '#f1f5f9', borderRadius: 8, padding: 12, marginBottom: 20, fontSize: 13 }}>
        <strong>Active provider:</strong> openai / gpt-4o &nbsp;·&nbsp;
        <strong>Reviews today:</strong> {reviews.length} &nbsp;·&nbsp;
        <a href="https://github.com" target="_blank" rel="noreferrer">Configure webhook →</a>
      </div>

      {loading ? <div>Loading...</div> : (
        reviews.length === 0
          ? <p style={{ color: '#64748b' }}>No reviews yet. Open a PR in a connected repo to get started.</p>
          : reviews.map(r => <ReviewCard key={r.id} review={r} />)
      )}
    </div>
  )
}
