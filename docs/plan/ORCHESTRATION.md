# ORCHESTRATION — runbook for the session that drives the build

You are the orchestrator. You dispatch agents, read handoff notes, run `make test`, and commit.
You do not write project code and you do not read source files unless a gate fails twice.

## Before wave 0

`cd /home/user/sanket && git init` (if not yet a repo). Check `df -h /home/user`; if under 2.5 GB free, run
`pip cache purge` (frees about 3 GB). Never install torch (see CONTRACTS conventions).

## Agents: 6 builders (Sonnet), 3 audit gates + 1 docs agent (Opus), advisor (Fable) only on escalation

| Wave | Spawn | Model | Then |
|---|---|---|---|
| 0 | B0 scaffold | sonnet | `make setup && make test`; commit |
| 1 | B1 data and clean | sonnet | Q1 data audit (opus); one fix round with B1; commit |
| 2 | B2 baseline, routing, retrain ∥ B3 PyTorch, ONNX, bench, drift ∥ B5 web (on fixtures) | sonnet | `make bench` if B3 could not; Q2 model audit (opus); one fix round; commit |
| 3 | B4 API, review, seed, replay | sonnet | B5 gets one message: "API is up, run live-mode e2e, fix"; Q3 system audit (opus); one fix round; commit |
| 4 | D1 docs | opus | `make test`; commit; give the user `docs/INTERVIEW_GUIDE.html` and `docs/DEPLOY.md` |

Parallel means one message with several Agent calls. Parallel agents own different directories (CONTRACTS layout).

## Spawn prompt (the whole prompt; fill in the id)

> Work in `/home/user/sanket`. Read `docs/plan/CONTRACTS.md` and `docs/plan/briefs/<ID>.md`, plus the handoff
> notes your brief lists. Do the work, run it, and finish by writing `docs/handoffs/<ID>.md` (30 lines max).
> Do not commit. Reply with five lines at most: done or not done, measured numbers, blockers.

Spawn with `subagent_type: "general-purpose"` and an explicit `model`. An agent never inherits this chat.

## Fix rounds (budgeted: one after each gate)

1. The Q-agent writes findings in `docs/handoffs/Q<n>.md`, ranked HIGH/MED/LOW, each with evidence and a suggested fix.
2. Send the HIGH and MED findings to the owning builder with SendMessage (its context is reused). LOW findings
   are fixed only if cheap; otherwise they go to the limitations list.
3. The builder fixes, adds a test per finding, and appends to `docs/AUDIT_LOG.md`: finding, evidence, fix, test name.
4. Send the Q-agent one message: "re-check only the items you raised". It appends PASS or FAIL per item to its handoff.
5. A finding that is still open after this round counts as fix attempt one; a second failed attempt triggers escalation.

`docs/AUDIT_LOG.md` is the candidate's "what reviewers found and fixed" story. Keep it factual.

## Token rules

1. Reading lists. Builders: CONTRACTS + own brief + listed handoffs. Only B4 and D1 read `EXPLAINABILITY.md`.
   Only D1 reads `PLAN.md`. Q-agents read their brief, the listed handoffs, then the code they audit. Nobody reads other briefs.
2. Size caps: brief 40 lines, handoff 30 lines, agent reply 5 lines, escalation 1 page, AUDIT_LOG entry 6 lines.
3. The orchestrator reads only handoff notes and the `make test` tail (`make test 2>&1 | tail -15`).
4. Agents talk through files (`CONTRACTS.md`, `fixtures/`, `docs/handoffs/`), never through the orchestrator's context.
5. Deliberately not done, to save tokens without hurting quality:
   - no hyper-parameter sweeps beyond the small grids named in the briefs; at most 3 NN variants;
   - no transformer or LLM baseline, no notebooks, no second browser in e2e;
   - Q-agents re-check only what they raised, never the whole area again;
   - builders write no prose docs beyond docstrings, model cards and handoffs; D1 writes all docs once, at the end;
   - the web app is built once against fixtures and touched again only for live-mode fixes;
   - no screenshots except two taken by D1 for the README;
   - deployment is prepared and documented, not executed (no credentials).

## Commits

The stop hook demands commits. After every wave and every fix round: `git add -A && git commit -m "wave N: <what>"`.
Agents never commit or push. Push only when the user asks. Do not commit `.venv`, `node_modules`, `*.db`, `dist/`.

## Escalation to the advisor (Fable)

Only when the same problem survived two fix attempts, or a contract change affects more than one agent.
The stuck agent writes `docs/escalations/<n>.md` (goal, what was tried, exact error or number, the question).
Spawn one agent with `model: "fable"`: "Read `docs/plan/CONTRACTS.md` and `docs/escalations/<n>.md`. Answer in
`docs/escalations/<n>.answer.md`. Do not read the code base. Do not build." Record it in `docs/EXPERIMENTS.md`.

## Definition of done

- From a clean clone: `make setup data train seed serve` and `make web` work; `make test` and `make lint` are green.
- Model quality gates pass on the frozen test set; `make bench` writes `docs/bench.md`; `make retrain` records a
  decision in `artifacts/registry.json`; the sabotage run is rejected by the gate.
- `docker build` succeeds and the container answers `/api/health` (or is recorded as not verified, with the reason).
- The dashboard shows Live against the local API and Replay with the API stopped; e2e passes in both modes.
- No raw PII in the database (Q3 test). `artifacts/` under 40 MB, every file under 10 MB.
- Every number in the docs appears in a model card, `docs/bench.md` or a handoff note.
- `docs/AUDIT_LOG.md` lists every HIGH and MED finding with its fix or an explicit "accepted limitation".
- Project directory under 1 GB including `.venv` and `node_modules`.
