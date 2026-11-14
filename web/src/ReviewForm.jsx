import React, { useState } from 'react'

/** Confirm or override one ticket. Shows the top-5 intents and a searchable select grouped by team. */
export default function ReviewForm({ ticket, taxonomy, api, onDone }) {
  const [reviewer, setReviewer] = useState('asha')
  const [mode, setMode] = useState('confirm')
  const [intent, setIntent] = useState('')
  const [urgency, setUrgency] = useState('')
  const [note, setNote] = useState('')
  const [search, setSearch] = useState('')
  const [msg, setMsg] = useState('')
  const [saved, setSaved] = useState(null)
  const top = (ticket.prediction && ticket.prediction.top_intents) || []
  const teams = taxonomy ? taxonomy.teams : {}

  async function send() {
    setMsg('')
    const body = { reviewer, action: mode, note }
    if (mode === 'override') {
      if (!intent) { setMsg('Pick the correct intent first.'); return }
      body.final_intent = intent
      if (urgency) body.final_urgency = urgency
    }
    try {
      const r = await api.review(ticket.ticket_id, body)
      setSaved(r)
      onDone && onDone(r)
    } catch (e) {
      setMsg(e.status === 409 ? 'Someone already reviewed this ticket. Refresh the queue.' : e.message)
    }
  }

  if (saved) {
    return (
      <p className="ok" data-testid="review-saved">
        {saved.action === 'confirm' ? 'Confirmed' : 'Overridden'} as {saved.final_intent} ({saved.final_team}, {saved.final_urgency}).
        {api.mode === 'replay' ? ' Replay, not saved.' : ' Saved.'}
      </p>
    )
  }
  return (
    <div className="form">
      <label>Reviewer <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} /></label>
      <div className="row">
        <button className={'chip' + (mode === 'confirm' ? ' sel' : '')} onClick={() => setMode('confirm')}>Confirm prediction</button>
        <button className={'chip' + (mode === 'override' ? ' sel' : '')} onClick={() => setMode('override')}>Override</button>
      </div>
      {mode === 'override' && (
        <>
          <div className="chips" aria-label="Top five intents">
            {top.map((t) => (
              <button key={t.intent} className={'chip' + (intent === t.intent ? ' sel' : '')} onClick={() => setIntent(t.intent)}>
                {t.intent} {Math.round(t.prob * 100)}%
              </button>
            ))}
          </div>
          <label>Search all intents <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="type to filter" /></label>
          <select aria-label="Intent" value={intent} onChange={(e) => setIntent(e.target.value)}>
            <option value="">Choose an intent</option>
            {Object.entries(teams).map(([team, intents]) => {
              const shown = intents.filter((i) => i.toLowerCase().includes(search.toLowerCase()))
              return shown.length ? (
                <optgroup key={team} label={team}>{shown.map((i) => <option key={i} value={i}>{i}</option>)}</optgroup>
              ) : null
            })}
          </select>
          <label>Urgency (optional)
            <select aria-label="Urgency" value={urgency} onChange={(e) => setUrgency(e.target.value)}>
              <option value="">keep rubric default</option>
              <option value="high">high</option><option value="medium">medium</option><option value="low">low</option>
            </select>
          </label>
        </>
      )}
      <label>Note (optional) <input value={note} onChange={(e) => setNote(e.target.value)} /></label>
      <button className="primary" data-testid="review-submit" onClick={send}>
        {mode === 'confirm' ? 'Confirm' : 'Save override'}{api.mode === 'replay' ? ' (replay, not saved)' : ''}
      </button>
      {msg && <p className="error" role="alert">{msg}</p>}
    </div>
  )
}
