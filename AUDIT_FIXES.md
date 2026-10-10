# Chunk bounds and single execution

Repair branch: `fix/internship-audit-20261010`. Changes are scoped to audit findings; no deployment or live provider action is included.

## Changed

Chunk windows are source-contiguous and token bounded. Invalid overlaps are rejected. Approval transitions use a database compare-and-set so concurrent approvals have one claimant. Failed/uncertain side effects become failed or needs_review rather than silently returning to pending.

## Verification

`pytest -q`

Commands are entry points, not a claim that every live integration was executed. See the repair bundle for actual results.

## Setup and remaining evidence

A process crash after claiming work can leave executing status: manually inspect external effects before resolving it. Do not replay payments/messages automatically. Public demo is trusted/synthetic only. RAG grounded flags/self-reported confidence are not calibrated evaluations; held-out retrieval/answer quality, provider integration and durable deployment storage remain open.
