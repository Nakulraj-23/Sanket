import React, { useCallback, useEffect, useRef, useState } from 'react'
import { checkHealth, liveApi, loadReplay, makeReplayApi } from './api.js'
import { CHIPS } from './samples.js'
import Pipeline from './Pipeline.jsx'
import Drawer from './Drawer.jsx'
import { QueuePanel, MonitorPanel, ModelPanel } from './Panels.jsx'

const MAX_CHARS = 2000

export default function App() {
  const [api, setApi] = useState(null)
  const [health, setHealth] = useState(null)
  const [stages, setStages] = useState([])
  const [taxonomy, setTaxonomy] = useState(null)
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [lit, setLit] = useState(0)
  const [busy, setBusy] = useState(false)
  const [drift, setDrift] = useState(null)
  const [drawer, setDrawer] = useState(null)
  const [queueVersion, setQueueVersion] = useState(0)
  const replayRef = useRef(null)

  const goLive = useCallback((h) => { setApi(liveApi); setHealth(h) }, [])

  // Decide live or replay once, then keep retrying health while in replay.
  useEffect(() => {
    let dead = false
    async function start() {
      try { const h = await checkHealth(); if (!dead) goLive(h) }
      catch {
        try {
          const replay = await loadReplay()
          replayRef.current = replay
          if (!dead) { setApi(makeReplayApi(replay)); setHealth(replay.health) }
        } catch { if (!dead) setError('Neither the API nor replay.json could be reached.') }
      }
    }
    start()
    return () => { dead = true }
  }, [goLive])

  useEffect(() => {
    if (!api || api.mode !== 'replay') return undefined
    const timer = setInterval(async () => {
      try { goLive(await checkHealth()) } catch { /* stay in replay */ }
    }, 15000)
    return () => clearInterval(timer)
  }, [api, goLive])

  useEffect(() => {
    if (!api) return
    setResult(null); setLit(0)
    api.stages().then(setStages).catch(() => setStages([]))
    api.taxonomy().then(setTaxonomy).catch(() => setTaxonomy(null))
    api.drift().then(setDrift).catch(() => setDrift(null))
  }, [api])

  function light() {
    setLit(0)
    let n = 0
    const timer = setInterval(() => { n += 1; setLit(n); if (n >= 7) clearInterval(timer) }, 120)
  }

  async function run(getResult) {
    setBusy(true); setError('')
    try {
      const r = await getResult()
      setResult(r); light()
    } catch (e) { setError(e.message) }
    setBusy(false)
  }

  function submit() {
    if (!api || !api.canFreeText) return
    run(() => api.postTicket(text))
  }

  function chip(i) {
    setText(CHIPS[i].text)
    if (!api) return
    if (api.mode === 'replay') run(async () => api.samples()[i])
    else run(() => api.postTicket(CHIPS[i].text))
  }

  const mode = api ? api.mode : null
  const model = health ? health.model_version : '...'
  return (
    <div className="page">
      <header className="top">
        <h1>SANKET</h1>
        <span className="sub">संकेत — signal</span>
        <span className={'badge ' + (mode || 'wait')} data-testid="mode-badge">
          {mode === 'live' ? 'Live' : mode === 'replay' ? 'Replay' : '...'}
        </span>
        <span className="ver">model {model}</span>
      </header>
      {mode === 'replay' && (
        <p className="note" data-testid="replay-note">Replay: recorded results, nothing is saved. Reviews stay in this tab only.</p>
      )}
      <section className="try" aria-label="Try it">
        <textarea
          aria-label="Customer message" value={text} maxLength={MAX_CHARS} rows={3}
          disabled={api ? !api.canFreeText : true}
          placeholder={api && !api.canFreeText ? api.freeTextReason : 'Type a customer message'}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="row">
          <span className="count">{text.length} / {MAX_CHARS}</span>
          <button className="primary" onClick={submit} disabled={busy || !api || !api.canFreeText || !text.trim()}>Submit</button>
        </div>
        <div className="chips">
          {CHIPS.map((c, i) => (
            <button key={c.label} className="chip" onClick={() => chip(i)} disabled={busy || !api}>{c.label}</button>
          ))}
        </div>
        {api && !api.canFreeText && <p className="muted">{api.freeTextReason}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </section>
      <Pipeline result={result} lit={lit} drift={drift} onOpen={(id) => setDrawer({ id, tab: 'what' })} />
      {result && <p className="muted">Ticket {result.ticket_id}: {result.text_redacted}</p>}
      <div className="grid">
        <QueuePanel api={api} taxonomy={taxonomy} version={queueVersion}
          onReviewed={() => setQueueVersion((v) => v + 1)} />
        <MonitorPanel api={api} drift={drift} setDrift={setDrift} version={queueVersion} />
        <ModelPanel api={api} />
      </div>
      {drawer && (
        <Drawer drawer={drawer} setDrawer={setDrawer} stages={stages} result={result} api={api}
          taxonomy={taxonomy} drift={drift}
          onReviewed={(r) => { setResult(r); setQueueVersion((v) => v + 1) }} />
      )}
    </div>
  )
}
