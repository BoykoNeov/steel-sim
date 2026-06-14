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
- **Open follow-ups (the user's, outward-facing):** respond to any maintainer review on
  #1529; the PR offers a `flush(zmq.POLLIN)` public-API alternative and to add a regression
  test / companion issue if requested. Dup-search already done (no dup; cross-refs in the doc).

This is a different repo from steel-sim, so it is not in steel-sim's git history.
