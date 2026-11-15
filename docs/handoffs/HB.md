# HB handoff: candidate handbook. Status: done (nothing committed)
Wrote `docs/CANDIDATE_HANDBOOK.md` (1,775 lines, 11 sections, 160 questions, 10 exercises), `docs/CANDIDATE_HANDBOOK.html`
(TOC, collapsible bank, light/dark, 390 px scrollWidth 390 checked) and `docs/CANDIDATE_HANDBOOK.pdf` (A4, 73 pages, page numbers),
all from `scripts/build_handbook_html.py --pdf` (Node playwright from web/node_modules + /opt/pw-browsers Chromium). ruff clean.
Component reference: 36 Python modules, 6 scripts, 13 API routes, 11 web files; PRAHARI 11-row module table.
Measured 2026-11-15 (cited as such): `make test` 261 passed, 1 xfailed (README badge still says 259); live /api/health ok, 250 tickets;
live urgent-fraud chip 0.793 / team 0.966 / auto; live /api/compare `nn: null` (no onnxruntime on Vercel); all SQL answers run on a
fresh seed DB; exercises 6-10 outputs; retrain demo on a scratch artifacts copy: sabotage 0.3 rejected at 71% top-5, honest promoted,
both candidates test F1 0.9027 (so the test gate alone would have promoted poison).
Discrepancy: `make seed` now gives auto 373, queued 13, reviewed 14, overrides 11 (B4 handoff and INTERVIEW_GUIDE exercise 5 say
15/12/10 and `('sim-reviewer', 12, 0.83)`); caused by the V1 seed change (skip at most half the queue). Handbook uses the new numbers.
Not verified: every Tech Mahindra/news link (proxy refused), marked "check this"; DPDP Act details marked "check this".
Untouched: pre-existing uncommitted README.md edit and AUTHORS.md (not mine). Repo artifacts unchanged (v1 only).
