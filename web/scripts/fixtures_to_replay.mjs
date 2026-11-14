// Builds public/replay.json from ../fixtures/*.json until the API delivers the real file.
// Usage: node scripts/fixtures_to_replay.mjs [--if-missing]
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const out = path.join(here, '..', 'public', 'replay.json')
if (process.argv.includes('--if-missing') && fs.existsSync(out)) process.exit(0)

const fx = (name) => JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'fixtures', name + '.json'), 'utf8'))
const auto = fx('ticket_result')
const review = fx('ticket_result_review')

// Stage text for stages the fixture does not carry (the fixture has only "clean").
const STAGE_TEXT = {
  ingest: ['Ingest', 'Checks the text is not empty, not too long and has letters.', 'Bad input is refused at the door with a clear reason.', 'sanket/pipeline/clean.py', 'validate'],
  clean: ['Clean', 'Masks emails, phones, card and account numbers, then lowercases.', 'The model never sees personal data.', 'sanket/pipeline/clean.py', 'clean'],
  classify: ['Classify', 'Scores all 77 intents and keeps the top five.', 'A linear model on word and character n-grams is fast and easy to audit.', 'sanket/models/baseline.py', 'predict_proba'],
  explain: ['Explain', 'Lists the words that pushed the answer most.', 'A reviewer can see why, not just what.', 'sanket/models/baseline.py', 'explain'],
  route: ['Route', 'Sums intent probabilities per team and decides auto or human.', 'Low confidence or unfamiliar words go to a person.', 'sanket/routing/decide.py', 'decide'],
  review: ['Review', 'A person confirms or overrides; the decision is stored.', 'Corrections are the only new labels the system learns from.', 'sanket/review.py', 'submit_review'],
  monitor: ['Monitor', 'Compares live tickets with the validation reference.', 'Drift shows up before accuracy complaints do.', 'sanket/monitoring/drift.py', 'drift_report'],
}
const fxStages = fx('stages')
const stages = Object.entries(STAGE_TEXT).map(([id, [title, what, why, file, fn]]) => {
  const own = fxStages.find((s) => s.id === id)
  return own || { id, title, what, why, file, function: fn, code: `def ${fn}(...):\n    ...  # placeholder, real code arrives with the API` }
})

function variant(base, id, text, patch = {}, predPatch = {}) {
  const r = JSON.parse(JSON.stringify(base))
  r.ticket_id = id
  r.text_redacted = text
  Object.assign(r, patch)
  Object.assign(r.prediction, predPatch)
  r.trace[1].detail.before_masked = text
  r.trace[1].detail.after = text
  return r
}

const samples = [
  variant(auto, 201, 'How do I order a physical card?', { status: 'auto_routed' }, { intent: 'order_physical_card', team: 'CARDS', urgency: 'low' }),
  variant(auto, 202, 'Someone used my card abroad, I did not make this payment', {}, { intent: 'card_payment_not_recognised' }),
  variant(review, 203, 'I tried to pay and it did not work', { review: null }, { intent: 'declined_card_payment', team: 'CARD_PAYMENTS' }),
  { ...review },
  variant(review, 205, 'Mera paisa transfer nahi hua, jaldi batao', {}, { intent: 'failed_transfer', team: 'TRANSFERS_TOPUPS', reason: 'unfamiliar_words' }),
  variant(review, 206, 'asdf qwer zxcv', {}, { intent: 'atm_support', team: 'CASH_ATM', reason: 'unfamiliar_words' }),
]
const chips = ['Clear', 'Urgent fraud', 'Ambiguous', 'Fake PII', 'Hinglish', 'Gibberish']
samples.forEach((s, i) => { s.chip = chips[i] })

const list = fx('ticket_list')
const queue = [list[0], { ...list[0], ticket_id: 203, text_redacted: samples[2].text_redacted, intent: 'declined_card_payment', team: 'CARD_PAYMENTS' }, { ...list[0], ticket_id: 205, text_redacted: samples[4].text_redacted, intent: 'failed_transfer', team: 'TRANSFERS_TOPUPS', reason: 'unfamiliar_words' }]
const compare = {}
samples.forEach((_, i) => { compare[i] = fx('compare') })

const replay = {
  generated_at: new Date().toISOString(),
  model_version: fx('health').model_version,
  health: fx('health'), stages, taxonomy: fx('taxonomy'), samples, compare, queue,
  drift: fx('drift_report'), drift_after_scenario: fx('drift_report_red'),
  metrics: fx('metrics'), model: fx('model'),
}
fs.writeFileSync(out, JSON.stringify(replay))
console.log('wrote', out)
