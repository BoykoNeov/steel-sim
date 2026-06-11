---
name: commit-push-end-of-batch
description: Standing instruction — always commit AND push at the end of a work batch
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5c5e41ca-e75b-4e59-a4d1-c516dc0ee794
---

At the end of a work batch, **always commit and push** the work — do not leave it
sitting uncommitted in the working tree waiting to be asked.

**Why:** The user wants finished batches durably saved to the remote, not stranded
locally. Overrides the default "commit/push only when asked" posture for this user.

**How to apply:** When a coherent batch of work is done and verified (tests green),
stage it, commit with a clear message (end with the `Co-Authored-By: Claude` line),
and `git push`. This repo's history is **linear on `main`** (no feature-branch/PR
workflow — see the git log), so commit to the working branch and push there rather
than branching, unless the user says otherwise. If there is no remote or the push
fails, say so plainly rather than silently stopping at the commit.
