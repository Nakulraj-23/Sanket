import React, { useCallback, useEffect, useState } from 'react'
import ReviewForm from './ReviewForm.jsx'

function Chip({ status }) { return <span className={'chip st-' + status}>{status}</span> }

export function QueuePanel({ api, taxonomy, version, onReviewed }) {
  const [rows, setRows] = useState([])
  const [open, setOpen] = useState(null)
  const [ticket, setTicket] = useState(null)
  const [err, setErr] = useState('')
  const load = useCallback(() => {
    if (!api) return
    api.listTickets('needs_review', 50).then(setRows).catch((e) => setErr(e.message))
  }, [api])
  useEffect(load, [load, version])

  async function pick(id) {
    setErr('')
    if (open === id) { setOpen(null); return }
    try { setTicket(await api.getTicket(id)); setOpen(id) } catch (e) { setErr(e.message) }
  }
  return (
    <section className="panel" aria-label="Review queue" data-testid="queue">
      <h2>Review queue <span className="muted">({rows.length})</span></h2>
      {err && <p className="error" role="alert">{err}</p>}
      {rows.length === 0 && <p className="muted">Nothing waiting for review.</p>}
      <ul className="list">
        {rows.map((r) => (
          <li key={r.ticket_id} data-testid="queue-item">
            <div className="row between">
              <span>#{r.ticket_id} <span className={'chip urg-' + r.urgency}>{r.urgency}</span> {r.text_redacted}</span>
              <button onClick={() => pick(r.ticket_id)} aria-expanded={open === r.ticket_id}>Review</button>
            </div>
            <div className="muted">{r.intent} ({r.team}), {r.reason.replace('_', ' ')}</div>
            {open === r.ticket_id && ticket && (
              <ReviewForm ticket={ticket} taxonomy={taxonomy} api={api}
                onDone={() => { setTimeout(() => { setOpen(null); onReviewed() }, 1200) }} />
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}

export function MonitorPanel({ api, drift, setDrift, version }) {
  const [metrics, setMetrics] = useState(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  useEffect(() => { if (api) api.metrics().then(setMetrics).catch(() => setMetrics(null)) }, [api, version])

  async function scenario(name) {
    setBusy(true); setMsg('')
    try {
      const r = await api.scenario(name)
      setDrift(await api.runDrift())
      setMsg(name === 'reset' ? 'Scenario reset.' : `Pushed ${r.inserted} Hinglish tickets and re-ran drift.`)
      setMetrics(await api.metrics())
    } catch (e) { setMsg(e.message) }
    setBusy(false)
  }
  const override = metrics ? Object.entries(metrics.override_rate_by_team) : []
  return (
    <section className="panel" aria-label="Monitor" data-testid="monitor">
      <h2>Monitor {drift && <Chip status={drift.status} />}</h2>
      {drift ? <p className="muted">{drift.message} ({drift.n_tickets} tickets)</p> : <p className="muted">No drift report yet.</p>}
      <ul className="list">
        {drift && drift.indicators.map((x) => (
          <li key={x.name} className="row between"><span>{x.name} <span className="muted">{x.kind} {x.value}</span></span><Chip status={x.status} /></li>
        ))}
      </ul>
      <h3>Override rate by team</h3>
      <ul className="bars">
        {override.map(([team, v]) => (
          <li key={team}><span className="lab">{team}</span><span className="track"><span className="fill" style={{ width: Math.min(100, v * 100 * 4) + '%' }} /></span><span className="val">{Math.round(v * 100)}%</span></li>
        ))}
      </ul>
      <div className="row">
        <button onClick={() => scenario('hinglish_surge')} disabled={busy || !api}>Simulate Hinglish surge</button>
        <button onClick={() => scenario('reset')} disabled={busy || !api}>Reset</button>
      </div>
      {msg && <p className="muted" role="status">{msg}</p>}
    </section>
  )
}

function flat(obj, prefix = '') {
  return Object.entries(obj || {}).flatMap(([k, v]) =>
    (v && typeof v === 'object' ? flat(v, prefix + k + ' ') : [[prefix + k, v]]))
}

export function ModelPanel({ api }) {
  const [m, setM] = useState(null)
  useEffect(() => { if (api) api.model().then(setM).catch(() => setM(null)) }, [api])
  if (!m) return <section className="panel" aria-label="Model"><h2>Model</h2><p className="muted">Loading...</p></section>
  const bench = m.bench || {}
  const c = m.champion
  const val = (c.metrics && c.metrics.val) || {}
  const test = (c.metrics && c.metrics.test) || {}
  const th = c.thresholds || {}
  const f = (v) => (typeof v === 'number' ? v.toFixed(3) : v ?? '-')
  const keys = ['intent_macro_f1', 'team_accuracy', 'p50_ms', 'size_mb']
  return (
    <section className="panel" aria-label="Model" data-testid="model">
      <h2>Model {c.version}</h2>
      <table><tbody>
        <tr><td>Model</td><td>{c.model || '-'}</td></tr>
        <tr><td>Version, date</td><td>{c.version}, {c.date}</td></tr>
        <tr><td>Intent macro-F1 (val / test)</td><td>{f(val.intent_macro_f1)} / {f(test.intent_macro_f1)}</td></tr>
        <tr><td>Team accuracy (val / test)</td><td>{f(val.team_accuracy)} / {f(test.team_accuracy)}</td></tr>
        <tr><td>High-urgency recall (val / test)</td><td>{f(val.high_recall)} / {f(test.high_recall)}</td></tr>
        <tr><td>Thresholds</td><td>team {th.tau_team}, urgency {th.tau_high}, unfamiliar {th.oov_max}</td></tr>
        <tr><td>Temperature T</td><td>{f(c.temperature)}</td></tr>
      </tbody></table>
      <details>
        <summary>Full model card</summary>
        <table><tbody>
          {flat(c.metrics).filter(([, v]) => typeof v !== 'object').map(([k, v]) => <tr key={k}><td>{k}</td><td>{f(v)}</td></tr>)}
        </tbody></table>
      </details>
      <h3>Logistic regression vs neural net</h3>
      <table><thead><tr><th>Measure</th><th>LR</th><th>NN</th></tr></thead><tbody>
        {keys.map((k) => <tr key={k}><td>{k}</td><td>{bench.baseline ? f(bench.baseline[k]) : '-'}</td><td>{bench.nn ? f(bench.nn[k]) : '-'}</td></tr>)}
      </tbody></table>
      <h3>Registry history</h3>
      <ul className="list">
        {m.registry.history.map((h) => (
          <li key={h.version + h.created_at}>
            <strong>{h.version}</strong> {h.decision} <span className="muted">{h.created_at}</span>
            {h.reasons && h.reasons.length > 0 && <div className="muted">{h.reasons.join('; ')}</div>}
          </li>
        ))}
      </ul>
    </section>
  )
}
