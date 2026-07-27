# my_env — handoff

Operational state as of 2026-07-27. Read `README.md` for what the environment *is* and
`DESIGN.md` for generator/verifier internals; this file covers **how to run it, what was
changed recently, what the numbers say, and what is still broken**.

---

## 1. Platform: this does not run on native Windows

`verifiers.v1` imports `fcntl` (`verifiers/v1/runtimes/limiters.py`), which is POSIX-only,
so `import verifiers.v1` fails on Windows before anything else happens. `docker/` guards
on `sys.platform`; `limiters.py` does not.

### macOS / Linux

Works natively — `my_env` was originally developed on macOS. Nothing special:

```bash
uv sync
```

If `pycosat` fails to build (a `reasoning-gym` -> dev-group dependency) you need a C
compiler and Python headers.

### Windows — use WSL

Set up here in the **Ubuntu-24.04** distro (`Ubuntu` and `docker-desktop` also exist):

- Repo stays on the Windows filesystem at `/mnt/c/Users/<user>/projects/verifiers`, so one
  git worktree serves both sides.
- **The venv must live on the WSL-native filesystem**: `UV_PROJECT_ENVIRONMENT=$HOME/.venvs/verifiers`.
  A default `.venv` in the repo would collide with the Windows one (`Scripts/` vs `bin/`)
  and is slow over the 9p mount.
- `~/.vf-dev.sh` defines a `vf-dev` function (sourced from `~/.bashrc`) that sets PATH and
  `UV_PROJECT_ENVIRONMENT`, cds to the repo, and exports `.env`.
- One-time apt installs needed for `pycosat`: `build-essential`, `python3.12-dev`.

`bash -lc` does **not** run `.bashrc` (Ubuntu short-circuits it for non-interactive
shells), so automation must source the helper explicitly:

```bash
wsl -d Ubuntu-24.04 -- bash -lc '. ~/.vf-dev.sh && vf-dev && <command>'
```

> **Gotcha that will waste your time.** When invoking WSL from a Windows shell, `$VAR`
> references and quoted heredocs are expanded by the *Windows* shell first, even inside
> single quotes — they arrive empty. Pass literal values, use `printenv NAME` to inspect,
> and put multi-line scripts in a file rather than a heredoc. A silently-empty
> `--client.base-url` produces the misleading error
> `ProviderError: Request URL is missing an 'http://' or 'https://' protocol`.

---

## 2. Credentials and models

All model calls go through **OpenRouter**. The CLI defaults point at Prime
(`api.pinference.ai`), so they must be overridden on every run.

- Credentials live in the **repo-root `.env`** — gitignored, and `verifiers.v1` does *not*
  auto-load it. `vf-dev` exports it; otherwise `set -a; . ./.env; set +a`. Ask the owner if
  the file is missing.
  - `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
  - `OPENROUTER_API_KEY=...`
- **`openai/gpt-5-mini`** — authoring and judging (the judge default is on `ChatTaskConfig.judge`).
- **`openai/gpt-5-nano`** — trial evaluations.

---

## 3. Running it

`my_env` is deliberately **not** a `[tool.uv.sources]` workspace member (AGENTS.md forbids
adding deps to the root `pyproject.toml`), so a bare `uv run` re-syncs the project env and
drops it. Always layer it in:

```bash
# author a batch: L1 plus one rewrite per extra rung, one JSONL per rung
uv run --with-editable environments/my_env python -m my_env.author \
  --num 5 --levels 5 --p-open 0.3 --p-invalid 0.35 \
  --out-dir environments/my_env/samples_v3

# evaluate one rung
uv run --with-editable environments/my_env eval my_env \
  --taskset.dataset environments/my_env/samples_v3/authored_tasks_l3.jsonl \
  --harness.id null -m openai/gpt-5-nano -r 1 \
  --client.base-url https://openrouter.ai/api/v1 \
  --client.api-key-var OPENROUTER_API_KEY \
  --no-push --uuid my-run-name
```

**CLI flags use hyphens, not underscores**, and there is no `--env.` prefix (the README's
original command predated a CLI change and silently did nothing). `--uuid` names the output
directory leaf, which makes collecting results scriptable.

Checks: `uv run ruff check environments/my_env/` and `uv run pytest tests/`.

---

## 4. What exists

Beyond the pipeline described in `README.md`:

| path | what |
| --- | --- |
| `my_env/world.py` | the seeded workspace — 24 users, 6 chats, 40 threaded messages |
| `my_env/authored_tasks_l1..l4.jsonl` | 12-task batch, authored under **older** rules — stale |
| `my_env/authored_tasks.jsonl` | pre-ladder single-file dataset — **superseded**, safe to delete |
| `samples_v2/` | 5 tasks x 3 rungs + `eval_results.md` |
| `samples_v3/` | 5 tasks x 5 rungs + `eval_results.md` + `ladder_example.md` (current) |
| `samples_v3/repeat3_l1_l4/` | L1 vs L4 at 3 rollouts/task, paired stats |
| `samples_v3/ladder_example.md` | **hand this to anyone who needs to understand the pipeline** |

`sample_output.json` in each samples dir is the raw generator output (seed / expected /
timeline) for the same tasks, produced with the same parameters as the authoring run.

---

## 5. The ambiguity ladder

One JSONL per rung. For a given `idx` the seed, expected state, steps and golds are
**byte-identical across rungs** — only `prompt` differs, so a score gap is attributable to
wording rather than to authoring noise (authoring runs at temperature 0.7; re-authoring
changes far more than the difficulty).

| rung | adds |
| --- | --- |
| L1 | explicit — intended as the easy floor |
| L2 | descriptive; numbering, tool names, ids and handles forbidden |
| L3 | relational / temporal references |
| L4 | conditional logic resolved against live state |
| L5 | 2–5 realistic typos, prose only |

Each rewrite is re-anchored to the original plan and app state, not just handed its
predecessor, so chained rewrites don't accumulate drift. A task failing at any rung is
dropped from every file to keep the set paired.

An **anaphoric** rung was built and removed: generated plans touch a different entity at
almost every step, so no referent recurs and a pronoun has nothing to bind to. The rewriter
invented a numbered index to point into, and when that was banned it just compressed the
prose. It needs the generator to reuse entities across steps.

---

## 6. What the numbers say

Single rollout, 5 tasks, `gpt-5-nano` agent / `gpt-5-mini` judge (`samples_v3/eval_results.md`):

| rung | mean reward | discovery reads |
| --- | --- | --- |
| L1 explicit | 0.934 | 7 |
| L2 descriptive | 0.865 | 23 |
| L3 relational | 0.937 | 15 |
| L4 conditional | **0.735** | 19 |
| L5 noisy | 0.777 | 19 |

Follow-up at 3 rollouts/task on L1 vs L4 (`samples_v3/repeat3_l1_l4/eval_results.md`):

- Mean **paired** delta L4 − L1: **−0.096** (sd 0.162). Paired t = −1.33, df = 4 —
  **not significant**. 3/5 tasks worse at L4.
- The single-rollout estimate (−0.20) halved once repeated. Treat one-rollout numbers as
  provisional.

**Conclusions that hold:**

1. **Referential ambiguity changes behaviour, not outcome.** L1/L2/L3 are indistinguishable
   on reward, but discovery reads (read-only calls before the first write) go up 2–3×. The
   de-referencing works; the model absorbs it.
2. **Conditionals make the model inconsistent rather than worse.** L4's stdev is roughly
   double L1's — e.g. one task's three rollouts were `[0.88, 0.38, 0.32]` at L4 against
   `[0.76, 0.82, 0.76]` at L1. The "otherwise skip" branch is an escape hatch and the model
   takes it about half the time.
3. **L5 (typos) is inert** for this model.
4. **n=5 cannot resolve a 0.1 reward difference.** ~20–30 tasks would be needed. Behavioural
   metrics (discovery reads, variance) are cheaper and less noise-limited.

---

## 7. Uncommitted change you are inheriting

`adapter.signature` now emits two extra facts:

```python
facts.add(("in", message.id, message.chat_id))
if message.reply_to:
    facts.add(("replyto", message.id, message.reply_to))
```

Before this, the signature recorded only that a message existed — **sending to the wrong
chat, or replying to the wrong parent, scored identically to getting it right**, which left
most of the referential difficulty unmeasured. Text, emoji and chat names remain excluded
(content); a message's chat and parent are structure.

Signatures are computed at scoring time from stored states, so existing datasets pick this
up with **no re-authoring**. But `state_diff` is now stricter, so **every number in section
6 predates the fix and will shift down**. Nothing has been re-scored — that is the first
thing to do if you need comparable figures.

---

## 8. Open issues, roughly by value

1. **No solvability check.** Nothing verifies a rewrite kept the intent uniquely
   recoverable, so a damaged prompt and a genuinely hard one score the same. The intended
   design: give a model only the seed state and the prompt, have it reconstruct the action
   plan, compare `(tool, object_id)` pairs against the ground truth already stored. Run it
   k times — same wrong plan every time means misleading; different plans each time means
   ambiguous. *A real instance exists today:* in `samples_v3` idx0 the prompt says "the
   oldest unread message in the launch channel that reads 'If it slips…'" — all seven launch
   messages are unread, so the ordinal points at `m_001` while the quote pins `m_004`.
2. **L1 is an unstable baseline.** It scored 0.827 in `samples_v2` (agent guessed chat ids
   and failed 5 calls) and 0.934 in `samples_v3`. The pathology fires when L1 names a *tool*
   but omits the *id* — being told which function to call makes the agent act before it
   looks. L1 should stop naming tools while staying explicit about entities.
3. **Empirical gating.** Rather than assuming L1 < … < L5, measure solve rate per rung and
   accept only within a target band (cf. Prime Intellect's general-agent post: "difficulty
   isn't guessed, it's measured"). Gate on `state_diff` alone and skip the judge — the judge
   is the dominant cost.
4. **Gold-replay soundness check.** Assert per task that `signature(expected) − signature(seed)`
   is non-empty. A task whose sampled actions are all reads/invalid has `expected == seed`,
   so `state_diff` returns 1.0 for doing nothing. Also flag *low*-delta tasks: `samples_v3`
   idx2 has a delta of **1 fact**, making its 0.5-weighted reward effectively a coin flip.
5. **Two of five L4 conditionals are degenerate** — the rewriter hedged into trivially-true
   existence checks ("if the engineering channel exists"). Forbid existence-of-entity as a
   condition; require mutable state (reactions, read status, thread contents).
6. **Conditions are constants.** Reactions in `world.py` are hardcoded, not rng-varied, so
   e.g. "if m_005 has any reactions" is true in every task and the else-branch never fires.
7. **`open_ended` returns 1.0 when a task has no open items** — a free 0.3. Same vacuous
   pattern as (4).
8. **Reward weights (0.5 / 0.2 / 0.3) are arbitrary.** `tool_calls` is ~always 0.20 and
   carries almost no signal.
9. **The judge reads the whole rollout** and is now more expensive than the agent it grades
   (one run: $0.07 judge vs $0.03 agent). It grades *delivery* — an answer retrieved but not
   reported does not count, by design. If cost bites, include tool calls without their
   results.
10. **Invalid steps are naked.** Prompts say "look up the user with id `u_missing`". They
    leave no state footprint, so naturalising them ("check whether Marta from finance is
    registered") is free and removes an obvious tell.
11. **Housekeeping.** `author.py` imports `openai`, which is undeclared in this package's
    `pyproject.toml`. `ruff format` has never been run on `my_env` (9 files would change) and
    `README.md` has 12 pre-existing markdownlint errors — both will bite when
    `pre-commit install` is run.

---

## 9. Gotchas worth knowing before you change anything

- **`p_invalid` is conditional.** In `generate.py` the open-ended draw happens first and
  `continue`s, so the effective invalid rate is `(1 - p_open) × p_invalid`. At
  `p_open=0.3, p_invalid=0.35` that is ~24%, observed 18%.
- **Task length** is bounded by `timesteps × max_actions_per_t`; at the defaults (3 × 3)
  every task has 3–9 actions. No separate knob.
- **`initial_state(rng)` is called twice** by `generate` — once for the simulation, once for
  the pristine seed — and both must be identical. Keep rng consumption a fixed count, and
  build fresh containers so the two states never share mutables.
- **Id counters must exceed every seeded id.** `world._next_id` derives them from the
  highest suffix rather than counting, because ids are a creation-order counter.
- **The authoring rewriter routes around surface-form bans.** It evaded a
  "don't write 'refer to X as Y'" ban by emitting a numbered index instead. State rules as
  intent, not as forbidden phrasings.
- **Judge input must never see the golds.** The rewriter returns only `{"prompt": ...}`;
  golds and hints never pass through it.
- **Repo names and question text are load-bearing** — golds are keyed to them character for
  character. Every rewrite invariant protects them, and L5 explicitly exempts quoted spans.

---

## 10. Verifying your own changes

There is no committed test suite for `my_env` (AGENTS.md prefers e2e tests and discourages
adding unit tests). Write throwaway scripts. The invariants worth re-checking after touching
the generator, world, or authoring:

- `build_world(Random(i))` is deterministic and consumes a fixed number of rng draws; two
  builds share no mutable containers.
- Referential integrity: every sender/member/reactor exists, replies point at real messages
  in the same chat, `me` is in every chat, ids unique, `ts` sequential.
- `generate()` over ~40 indices raises no assertion (`outcome.error == (kind == "invalid")`)
  and mints no colliding ids.
- `score(seed, expected, faithful_trace)` is 1.0 and `score(seed, expected, seed)` is < 1.0.
- Across rungs: same idx set, byte-identical `seed`/`expected`/`steps`/`open_ended`, prompts
  actually differing, repo names and question text present verbatim.
