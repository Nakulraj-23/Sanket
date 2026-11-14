import React from 'react'
import { STAGE_ORDER, STAGE_TITLES } from './samples.js'

function cardText(id, result, drift) {
  if (id === 'review') return result ? 'Status: ' + result.status.replace('_', ' ') : ''
  if (id === 'monitor') return drift ? 'Drift: ' + drift.status : ''
  const t = result && result.trace.find((x) => x.stage === id)
  return t ? t.summary : ''
}

function cardMs(id, result) {
  const t = result && result.trace.find((x) => x.stage === id)
  return t ? t.ms + ' ms' : ''
}

/** Seven cards left to right; cards light up one after another once a result arrives. */
export default function Pipeline({ result, lit, drift, onOpen }) {
  return (
    <section aria-label="Pipeline">
      <div className="strip" data-testid="strip">
        {STAGE_ORDER.map((id, i) => {
          const on = result && i < lit
          return (
            <React.Fragment key={id}>
              <button className={'card' + (on ? ' on' : '')} data-testid={'card-' + id} onClick={() => onOpen(id)}>
                <span className="num">{i + 1}</span>
                <strong>{STAGE_TITLES[id]}</strong>
                <span className="summary">{on || (!result && id === 'monitor') ? cardText(id, result, drift) : ''}</span>
                <span className="ms">{on ? cardMs(id, result) : ''}</span>
              </button>
              {i < STAGE_ORDER.length - 1 && <span className="arrow" aria-hidden="true">→</span>}
            </React.Fragment>
          )
        })}
      </div>
      <div className="return" aria-hidden="true">↩ retrain gate: reviewed tickets feed the next model, which must pass the gate to replace this one</div>
    </section>
  )
}
