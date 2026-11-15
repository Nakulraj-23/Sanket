// All data access. Two sources only: the live API and public/replay.json.
// Both return the shapes in docs/plan/CONTRACTS.md.
const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

async function call(method, path, body, timeoutMs = 15000) {
  const ctl = new AbortController()
  const timer = setTimeout(() => ctl.abort(), timeoutMs)
  try {
    const res = await fetch(BASE + '/api' + path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: ctl.signal,
    })
    let data = null
    try { data = await res.json() } catch { data = null }
    if (!res.ok) {
      const err = new Error(formatDetail(data && data.detail) || 'Request failed (' + res.status + ')')
      err.status = res.status
      throw err
    }
    return data
  } finally {
    clearTimeout(timer)
  }
}

function formatDetail(d) {
  if (!d) return ''
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => (typeof x === 'string' ? x : x.msg || JSON.stringify(x))).join('; ')
  return JSON.stringify(d)
}

/** Health check with a 4-second timeout. Resolves to the health object or throws. */
export async function checkHealth() {
  const h = await call('GET', '/health', null, 4000)
  // A static host may answer /api/health with index.html; only a real health body counts.
  if (!h || h.status !== 'ok') throw new Error('not the API')
  return h
}

export async function loadReplay() {
  const res = await fetch('/replay.json')
  if (!res.ok) throw new Error('replay.json missing')
  return res.json()
}

/** Live source: one function per row of the REST table. */
export const liveApi = {
  mode: 'live',
  canFreeText: true,
  health: () => call('GET', '/health'),
  postTicket: (text, channel = 'web') => call('POST', '/tickets', { text, channel }),
  listTickets: (status = 'needs_review', limit = 50) => call('GET', `/tickets?status=${status}&limit=${limit}`),
  getTicket: (id) => call('GET', `/tickets/${id}`),
  review: (id, body) => call('POST', `/tickets/${id}/review`, body),
  stages: () => call('GET', '/stages'),
  taxonomy: () => call('GET', '/taxonomy'),
  compare: (text) => call('POST', '/compare', { text }),
  drift: () => call('GET', '/monitor/drift'),
  runDrift: () => call('POST', '/monitor/drift/run'),
  scenario: (name) => call('POST', '/demo/scenario', { name }),
  metrics: () => call('GET', '/metrics'),
  model: () => call('GET', '/model'),
  // Samples are only used by replay mode.
  samples: () => [],
}

/** A queued ticket with no recorded sample: show what its own stored row says. */
function fromQueueRow(q) {
  if (!q) throw new Error('Ticket not found in replay data')
  return {
    ticket_id: q.ticket_id, created_at: q.created_at, status: q.status, text_redacted: q.text_redacted, trace: [], review: null,
    prediction: { intent: q.intent, intent_conf: q.intent_conf, top_intents: [{ intent: q.intent, prob: q.intent_conf }],
      team: q.team, team_conf: q.team_conf, urgency: q.urgency, decision: q.decision, reason: q.reason, top_terms: [] },
  }
}

/** Replay source: same method names, answers from replay.json, edits kept in memory only. */
export function makeReplayApi(replay) {
  let queue = [...replay.queue]
  let drift = replay.drift
  const reviewed = {}
  const reason = 'Replay mode: the API is not reachable, so free text is off.'
  const sampleOf = (id) => replay.samples.findIndex((s) => s.ticket_id === id)
  return {
    mode: 'replay',
    canFreeText: false,
    freeTextReason: reason,
    health: async () => replay.health,
    postTicket: async () => { throw new Error(reason) },
    listTickets: async () => queue,
    getTicket: async (id) => replay.samples[sampleOf(id)] || fromQueueRow(queue.find((q) => q.ticket_id === id)),
    review: async (id, body) => {
      if (reviewed[id]) { const e = new Error('Already reviewed'); e.status = 409; throw e }
      const row = queue.find((q) => q.ticket_id === id)
      const intent = body.action === 'confirm' ? (row ? row.intent : '') : body.final_intent
      const team = Object.keys(replay.taxonomy.teams).find((t) => replay.taxonomy.teams[t].includes(intent)) || ''
      const urgency = body.final_urgency || replay.taxonomy.urgency[intent] || 'medium'
      reviewed[id] = { ticket_id: id, reviewer: body.reviewer, action: body.action, final_intent: intent,
        final_team: team, final_urgency: urgency, note: body.note || '', created_at: new Date().toISOString() }
      queue = queue.filter((q) => q.ticket_id !== id)
      return reviewed[id]
    },
    stages: async () => replay.stages,
    taxonomy: async () => replay.taxonomy,
    compare: async (text, ticketId) => replay.compare[String(sampleOf(ticketId))] || Object.values(replay.compare)[0],
    drift: async () => drift,
    runDrift: async () => drift,
    scenario: async (name) => {
      drift = name === 'reset' ? replay.drift : replay.drift_after_scenario
      return { inserted: name === 'reset' ? 0 : 300 }
    },
    metrics: async () => replay.metrics,
    model: async () => replay.model,
    samples: () => replay.samples,
    sampleOf,
  }
}
