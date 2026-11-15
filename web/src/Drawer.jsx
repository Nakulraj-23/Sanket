import React, { useEffect, useState } from 'react'
import ReviewForm from './ReviewForm.jsx'
import { STAGE_TITLES } from './samples.js'

const TABS = [['what', 'What it does'], ['why', 'Why this way'], ['code', 'Code'], ['live', 'Live example']]
const PLACEHOLDER = /(\[(?:EMAIL|PHONE|CARD|ACCOUNT)\])/

function Marked({ text }) {
  return <>{String(text).split(PLACEHOLDER).map((p, i) => (PLACEHOLDER.test(p) ? <mark key={i}>{p}</mark> : <span key={i}>{p}</span>))}</>
}

function Bars({ rows, max, fmt }) {
  const top = max || Math.max(...rows.map((r) => Math.abs(r.value)), 0.0001)
  return (
    <ul className="bars">
      {rows.map((r) => (
        <li key={r.label}>
          <span className="lab">{r.label}</span>
          <span className="track"><span className="fill" style={{ width: Math.min(100, (Math.abs(r.value) / top) * 100) + '%' }} /></span>
          <span className="val">{fmt ? fmt(r.value) : r.value}</span>
        </li>
      ))}
    </ul>
  )
}

function ruleInWords(d, pred) {
  const th = d.thresholds
  if (pred.decision === 'human' && pred.reason === 'low_confidence') return `Sent to a person: team confidence ${pred.team_conf} is below ${th.tau_team}.`
  if (pred.decision === 'human') return `Sent to a person: too many unfamiliar words (limit ${th.oov_max}).`
  return `Routed automatically: team confidence ${pred.team_conf} is at least ${th.tau_team} and the words were familiar.`
}

function Classify({ detail, result, api }) {
  const [cmp, setCmp] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    setCmp(null); setErr('')
    api.compare(result.text_redacted, result.ticket_id).then(setCmp).catch((e) => setErr(e.message))
  }, [result, api])
  return (
    <>
      <Bars rows={detail.top_intents.map((t) => ({ label: t.intent, value: t.prob }))} max={1} fmt={(v) => Math.round(v * 100) + '%'} />
      <h4>Second opinion (small neural net)</h4>
      {err && <p className="error">{err}</p>}
      {cmp && (
        <table><thead><tr><th>Model</th><th>Intent</th><th>Confidence</th><th>Time</th></tr></thead><tbody>
          <tr><td>Baseline</td><td>{cmp.baseline.intent}</td><td>{cmp.baseline.conf}</td><td>{cmp.baseline.ms} ms</td></tr>
          {cmp.nn && <tr><td>Neural net</td><td>{cmp.nn.intent}</td><td>{cmp.nn.conf}</td><td>{cmp.nn.ms} ms</td></tr>}
        </tbody></table>
      )}
      {cmp && !cmp.nn && <p className="muted">{cmp.nn_note || 'The neural network is not available in this deployment.'}</p>}
    </>
  )
}

function Example({ id, result, api, taxonomy, drift, onReviewed }) {
  if (id === 'monitor') {
    if (!drift) return <p className="muted">No drift report yet.</p>
    return (
      <>
        <p>Status <span className={'chip st-' + drift.status}>{drift.status}</span> over {drift.n_tickets} tickets.</p>
        <table><thead><tr><th>Indicator</th><th>Test</th><th>Value</th><th>p</th><th>Status</th></tr></thead><tbody>
          {drift.indicators.map((x) => (
            <tr key={x.name}><td>{x.name}</td><td>{x.kind}</td><td>{x.value}</td><td>{x.p_value == null ? '-' : x.p_value}</td>
              <td><span className={'chip st-' + x.status}>{x.status}</span></td></tr>
          ))}
        </tbody></table>
      </>
    )
  }
  if (!result) return <p className="muted">Run a sample first to see this stage's data.</p>
  if (id === 'review') {
    if (result.status === 'reviewed' || result.review) {
      const r = result.review
      return <p className="ok">Already reviewed{r ? ': ' + r.action + ' as ' + r.final_intent : ''}.</p>
    }
    if (result.status === 'auto_routed') return <p>This ticket was routed automatically. No review is needed.</p>
    return <ReviewForm ticket={result} taxonomy={taxonomy} api={api} onDone={(r) => onReviewed({ ...result, status: 'reviewed', review: r })} />
  }
  const t = result.trace.find((x) => x.stage === id)
  if (!t) return <p className="muted">No data for this stage.</p>
  const d = t.detail
  if (id === 'ingest') return <p>{d.problems.length ? 'Problems: ' + d.problems.join('; ') : 'No problems found. Text accepted.'}</p>
  if (id === 'clean') {
    return (
      <>
        <h4>Before (masked for display)</h4><p className="mono"><Marked text={d.before_masked} /></p>
        <h4>After</h4><p className="mono"><Marked text={d.after} /></p>
        <p className="muted">Found: {Object.keys(d.pii).length ? Object.entries(d.pii).map(([k, v]) => k + ' x' + v).join(', ') : 'nothing to mask'}</p>
      </>
    )
  }
  if (id === 'classify') return <Classify detail={d} result={result} api={api} />
  if (id === 'explain') {
    return <Bars rows={d.terms.map((x) => ({ label: x.term, value: x.weight }))} fmt={(v) => v.toFixed(2)} />
  }
  if (id === 'route') {
    return (
      <>
        <Bars rows={Object.entries(d.team_probs).map(([k, v]) => ({ label: k, value: v }))} max={1} fmt={(v) => Math.round(v * 100) + '%'} />
        <p>Chance this is high urgency: {d.p_high} (flag at {d.thresholds.tau_high}).</p>
        <p>Thresholds: team {d.thresholds.tau_team}, urgency {d.thresholds.tau_high}, unfamiliar words {d.thresholds.oov_max}.</p>
        <p><strong>{ruleInWords(d, result.prediction)}</strong></p>
        <p className="muted">Rule: {d.rule}. Team and urgency come from this project's rubric, not the dataset.</p>
      </>
    )
  }
  return null
}

/** Side drawer with four tabs. Esc closes it. */
export default function Drawer({ drawer, setDrawer, stages, result, api, taxonomy, drift, onReviewed }) {
  const stage = stages.find((s) => s.id === drawer.id)
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') setDrawer(null) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [setDrawer])
  return (
    <aside className="drawer" role="dialog" aria-label={STAGE_TITLES[drawer.id] + ' details'} data-testid="drawer">
      <div className="row between">
        <h2>{STAGE_TITLES[drawer.id]}</h2>
        <button onClick={() => setDrawer(null)} aria-label="Close drawer">Close (Esc)</button>
      </div>
      <div role="tablist" className="tabs">
        {TABS.map(([k, label]) => (
          <button key={k} role="tab" aria-selected={drawer.tab === k} className={drawer.tab === k ? 'sel' : ''}
            onClick={() => setDrawer({ ...drawer, tab: k })}>{label}</button>
        ))}
      </div>
      <div role="tabpanel" className="tabpanel" data-testid="tabpanel">
        {drawer.tab === 'what' && <p>{stage ? stage.what : 'Loading...'}</p>}
        {drawer.tab === 'why' && <p>{stage ? stage.why : 'Loading...'}</p>}
        {drawer.tab === 'code' && (stage ? (
          <>
            <p className="muted">{stage.file} : {stage.function}</p>
            <pre>{stage.code}</pre>
          </>
        ) : <p>Loading...</p>)}
        {drawer.tab === 'live' && <Example id={drawer.id} result={result} api={api} taxonomy={taxonomy} drift={drift} onReviewed={onReviewed} />}
      </div>
    </aside>
  )
}
