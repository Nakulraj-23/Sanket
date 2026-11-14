// Six sample chips. In replay mode the chip index picks a prepared result from replay.json.
export const CHIPS = [
  { label: 'Clear', text: 'How do I order a physical card?' },
  { label: 'Urgent fraud', text: 'Someone used my card abroad, I did not make this payment' },
  { label: 'Ambiguous', text: 'I tried to pay and it did not work' },
  { label: 'Fake PII', text: 'Mera card 4111 1111 1111 1111 kaam nahi kar raha, mail me at test@example.com' },
  { label: 'Hinglish', text: 'Mera paisa transfer nahi hua, jaldi batao' },
  { label: 'Gibberish', text: 'asdf qwer zxcv' },
]

export const STAGE_ORDER = ['ingest', 'clean', 'classify', 'explain', 'route', 'review', 'monitor']
export const STAGE_TITLES = {
  ingest: 'Ingest', clean: 'Clean', classify: 'Classify', explain: 'Explain',
  route: 'Route', review: 'Review', monitor: 'Monitor',
}
