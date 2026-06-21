---
name: upstream-pr-filed
description: The notebook-kernel-wedge investigation culminated in upstream ipykernel PR
metadata: 
  node_type: memory
  type: project
  originSessionId: 8ff9cb0f-0a51-494c-bc02-790d704ab93c
---

The steel-sim notebook-kernel-wedge forensics (the `ZMQ_FD` edge-drain root cause)
were turned into an **upstream fix PR: `ipython/ipykernel#1529`**, filed 2026-06-14
under the user's GitHub account (BoykoNeov), branch
`fix/shell-zmqstream-rearm-after-reply-send` on the fork `BoykoNeov/ipykernel`.

- **What it fixes:** ipykernel 7 on Windows intermittently drops an `execute_request` —
  the dual-use shell ROUTER's out-of-band reply `send_multipart` drains the edge-triggered
  `ZMQ_FD` read edge and the shell `ZMQStream` is never re-armed. The PR re-arms the read
  after each reply send (3 files, +21/-0: `subshell_manager.py`, `shellchannel.py`,
  `kernelapp.py`). Validated 0/20 vs 6/20 control on steel-sim's notebook test.
- **steel-sim side stays as-is:** the retry-on-wedge mitigation in
  `steel/tests/test_steel_notebook.py` is unchanged (orthogonal, ships regardless of the
  upstream outcome). The decision was "keep retry, file upstream" — now done.
- **Provenance in-repo:** `docs/handoffs/notebook-kernel-wedge-upstream-issue.md` (long-form
  rationale, now marked FILED), `docs/handoffs/ipykernel-shell-wedge-rearm.patch` (the
  applicable patch, validated against 7.2.0; `main`/7.3.0 byte-identical at the fix site),
  `docs/memory/notebook-kernel-wedge-rootcause.md` (forensics).
- **Maintainer review landed 2026-06-16 → stream-send fix + test PUSHED, reply POSTED, title FIXED (all
  2026-06-16, user-authorized). PR #1529 fully responded to; now awaiting ianthomas23's re-review.**
  Force-pushed (`--force-with-lease`) the rewritten
  PR branch `fix/shell-zmqstream-rearm-after-reply-send`: **2 clean commits replacing the old re-arm commit** —
  `2784c12` *Send the shell reply through the ZMQStream…* (3 files: subshell_manager stream-send body + shell_stream
  threaded via shellchannel/kernelapp; comments rewritten off "re-arm") + `78782b4` *Add a regression test…*.
  **pre-commit.ci auto-added `1c2eef1`** (benign: stripped 3 unused `# noqa: BLE001` + 1 blank line in the TEST
  only; ruff in ipykernel doesn't enable BLE001). Test green post-autofix; local FF-synced to remote `1c2eef1`.
  Reply POSTED (`reply-1529.md`; issuecomment-4718457255) — user-edited it to drop "not just simpler" +
  practicusai's "thanks/Windows-only" caveat (NB: that removed the cross-OS hedge). **PR TITLE updated** to
  "Send the shell reply through the ZMQStream instead of raw on its socket". Backup branch
  `try/stream-send-variant`@`7efaab3` intact; diagnostics (`ab_*`,
  `validate_harness.py`, `reply-1529.md`) kept OUT of the PR.
  `ianthomas23` (COLLABORATOR) confirmed the red CI was flakiness (re-ran, passed — vindicates the
  2026-06-15 diagnosis below), said **a regression test is important**, and asked: *simpler to use
  `shell_stream.send_multipart` instead of raw `shell_socket.send_multipart`?* He's right and it's the
  BETTER fix (not just simpler): routing the reply through the stream makes the stream the sole user of
  the socket, so its own `_handle_events`→`_rebuild_io_state` recvs any queued request first and re-arms
  POLLIN — eliminates the root cause vs re-arming after it; drops the private `_handle_events` poke.
  Verified against pyzmq 27.1.0 source (`zmqstream.py` `send_multipart`→`_add_io_state`; `_handle_events`
  ends in `_rebuild_io_state`). `practicusai` also reported the symptom on **Ubuntu** (vscode-jupyter#17228)
  — corroborates the mechanism is OS-general, but DON'T claim the patch fixes #17228 (generic symptom).
- **The variant (now PUSHED — see above), built in scratch clone `M:\claud_projects\ipykernel-wedge-work`:**
  (1) the stream-send variant (`subshell_manager.py` only, +11/-7 vs the old re-arm body); (2) a
  **deterministic behavioral regression test** `tests/test_subshell_wedge.py` — manually creates the strand
  precondition (queue a request, drain the ZMQ_FD edge), calls the real `_send_on_shell_channel`, asserts
  delivery to `on_recv`. Passes 8/8 with stream-send AND with the original re-arm impl; **fails by timeout against a
  raw-send BODY (with the `shell_stream` threading present)** → it discriminates. **PRECISION: that negative control
  is NOT literal 3-arg upstream** — the test calls the 4-arg `SubshellManager(...,shell_stream)` ctor, so upstream
  pristine wouldn't even construct; don't tell the maintainer "fails on pristine upstream" verbatim. This
  deterministic test is the **primary evidence and supersedes the 6/20→0/20 statistical A/B** (which only existed
  for lack of a repro). Notebook re-validation this session: control **0/30**, fix **30/30 clean** + engagement
  marker **870 stream / 0 fallback**. **0/30 is statistically INCOMPATIBLE with the historical ~28% (six control
  arms: §3 6/20+8/20, §4 5/20+5/20+6/20; 0.70³⁰≈1.2e-5) → the rate is NON-STATIONARY, NOT "bad luck from a 30%
  urn".** Deps byte-identical to the original env (pyzmq 27.1.0 / tornado 6.5.5 / ipykernel 7.2.0 / nbclient 0.11.0
  / jc 8.9.0) → NOT a version regression; the variables are DRIVER+ENVIRONMENT (historical = `sitecustomize`-
  instrumented kernel; this session = plain `_notebook_exec._execute_once`); the doc itself records the rate
  ranging 0%→30% by notebook comm-traffic/timing. **DON'T claim "historical 30% was an instrumentation artifact"**
  (unsubstantiable; the sham≈control arm already controlled per-send overhead; floating it self-sabotages the PR) —
  it's a possibility, not a finding. **Instrumented-vs-plain A/B RAN 2026-06-16** (scratch `ab_harness.py` +
  `ab_sitecustomize/` faithfully rebuilding the §4 "sham" wrap — per-send overhead + send-gated noop callback,
  NO recovery — interleaved 30/arm on pristine site-packages): **plain 0/30, instrumented 0/30**, instrumentation
  CONFIRMED engaged (841 monkeypatched sends / 29 kernels). **Read it SYMMETRICALLY** (advisor): the within-session
  plain-vs-instrumented null is WEAK for "driver doesn't matter" (a shut window reads 0 either way) AND
  UNDERPOWERED for the artifact hypothesis (a ~0%% base rate gives instrumentation nothing to amplify). What
  actually licenses "ENVIRONMENT/TIMING, not driver/version" is two OTHER things: (1) deps byte-identical → not a
  code/version regression; (2) the LONGITUDINAL drop on a held-constant driver class — the sham instrumentation
  (REBUILT, not original bytes) wedged ~25%% historically (§4 5/20) and 0/30 now → rate collapsed with the
  instrumentation held ~constant. Defensible terminus: **versions ruled out; current env doesn't manufacture wedges
  from nothing; the SPECIFIC env/timing factor is unpinnable while the window is shut** (pinning it needs an env
  where the wedge fires — can't conjure on demand; further archaeology has ZERO bearing on the deliverable). Still
  NO claim of an artifact. The deterministic test is **RATE-IMMUNE** (manufactures
  the strand precondition), so it's the sound evidence and the rate question doesn't gate the answer. **Don't chase the wedge.**
  Site-packages 7.2.0 patched only transiently for the arm, **restored pristine + sha256-verified**.
  The PR still offers a `flush(zmq.POLLIN)` alt; dup-search already done (no dup).
- **2026-06-20: lint blocker CLEARED, PR now effectively green.** After the 06-16 push, CI's sole change-related red was `ruff PT018` ("assertion should be broken down") on the regression test `tests/test_subshell_wedge.py:147` (`assert received and received[-1][-1] == b"req-1"`). **Pushed `70467c2`** splitting it into two asserts (no behavior change); **Test Lint + pre-commit.ci now PASS**. Lone remaining red = `test_subshells.py::test_run_concurrently_sequence[...]` **pytest-timeout(>30s) on macOS qt6 pypy** = pre-existing concurrency-timing flakiness, a DIFFERENT file, unrelated to the change (my regression test passes on that runner). Don't re-run upstream to "fix" the flake. Both maintainer asks (regression test + `shell_stream.send_multipart`) are satisfied → ball is in ianthomas23's court for re-review. (ZupoLlask pinged #1529 on 06-17 for help on #1469 — moot, that work is active there: see [[pr-1469-root-cause]].)
- **2026-06-21 re-check: #1529 UNCHANGED — OPEN/MERGEABLE, still awaiting ianthomas23's re-review, NO new comments since the 06-16 reply** (ZupoLlask's 06-17 cross-link is the only later activity, moot). CI re-verified green except the same `test_run_concurrently_sequence` macOS qt6 pypy timeout flake (confirmed this run: the `[True-*]` variants pass, lone `[False-are_subshells0]` hits the 30s timeout). Companion **#1469's Fix A MERGED into `patch-2` today** and #1469 is now 40/40 green — ball there is also with ianthomas23 (see [[pr-1469-root-cause]]). Nothing owed from us on either PR.
- **#1529 red CI ≠ a problem with the patch (diagnosed 2026-06-15, still 0 maintainer comments).**
  Three failing checks, none reach the 3 patched files: (1) `enforce-label` = maintainer-bot
  label, non-code; (2) `windows qt5/3.10` = `test_pylab` matplotlib font-cache *timeout* in the
  **in-process** kernel (no ZMQ/SubshellManager/kernelapp); (3) `windows qt5/pypy-3.11` =
  `RuntimeError: Kernel died before replying to kernel_info` in `test_subshells.py`. The pypy one
  is REFUTED structurally, not statistically: kernel died at *startup* before kernel_info → before
  any execute_request → before the re-arm code ran; all CPython Windows jobs (qt6 ×4 + qt5/3.14)
  run `test_subshells` under the patch and pass; same pypy-3.11 **passes qt6 / fails qt5** (Qt is
  irrelevant to kernel startup = flake signature); `main` fails the same pypy qt5 job identically
  (same error, 141 passed/42 skipped, attributed to `test_async_interrupt`). "ipykernel tests" is
  red on most recent `main` runs regardless. **Don't re-run/push on ipython/ipykernel to "fix" it.**

This is a different repo from steel-sim, so it is not in steel-sim's git history.
