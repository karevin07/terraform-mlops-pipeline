# Design: MLOps Portfolio Roadmap (Promote / Canary / Observability / CI)

**Date**: 2026-07-31  
**Status**: Draft for review  
**Goal**: Turn this Free-Tier serverless repo into an interview-ready MLOps side project with a closed E2E loop, then deepen platform capabilities.

## 1. Context

### Already working
- Event-driven training: S3 `.csv` → Python Training Lambda
- Artifacts: `model.joblib` + `model.onnx` on S3; metadata in DynamoDB
- Inference: Go + Gin + ONNX Runtime behind API Gateway
- IaC: Terraform modules; cost guardrail via AWS Budgets
- CI: tag `v*` → Terraform + image build/push + Lambda update

### Critical gap
Training always writes `Status: "training"`, while inference only serves `stable` / `canary`. Models never become servable without a manual DynamoDB edit. Canary / rollback are documented but not operable.

### Product choices (agreed)
| Topic | Decision |
|-------|----------|
| Positioning | Interview demo (E2E) **+** platform depth (canary, monitoring, CI) |
| Promotion | Auto `staging` → threshold auto `canary` → **manual** `stable` |
| Canary v1 | Application-level traffic split by registry status |
| Canary v2 | Later upgrade to Lambda alias weighted routing |
| Delivery style | Vertical slices (always demoable) |

## 2. Target story (demo script)

1. `make fetch-data` (or upload CSV) → Training Lambda runs  
2. Logs / `make check-metadata` show new version as `staging` or `canary`  
3. `make promote-stable VERSION=v...` → version becomes `stable`; previous stable → `archived`  
4. `make predict-lambda` returns that `model_version`  
5. `make rollback VERSION=v...` → predict returns the rolled-back version  
6. (Phase 1+) Show CloudWatch alarm / PR CI green  
7. (Phase 2) Show alias weight canary as the “platform” upgrade

## 3. Model lifecycle

### Status machine

```text
training (transient, optional)
    │  on successful train register
    ▼
staging  ──(metrics pass threshold)──► canary ──(manual promote)──► stable
    │                                     │                            │
    │ metrics fail                        │                            │
    └──────── stay staging                │                     archived
                                          │  (on promote of newer, or rollback)
                                          └── may be archived when replaced
```

**Registration rule (Training Lambda)**  
On successful train:
1. Write item with metrics, `ArtifactUrl`, `OnnxUrl`, `CreatedAt`
2. Set `Status = staging`
3. If `rmse <= RMSE_THRESHOLD` **and** `mae <= MAE_THRESHOLD` → set `Status = canary`
4. Never auto-set `stable`

**Thresholds** (env vars on Training Lambda, with defaults suitable for stock demo):
- `RMSE_THRESHOLD` (default `100.0`): loose gate so early demos rarely block; tighten after measuring a real baseline run
- `MAE_THRESHOLD` (default `80.0`): same rationale
- Persist applied thresholds on the item under `Config` (JSON/map) for auditability

**Promote to stable** (`scripts/promote_model.py` or Makefile → AWS CLI/SDK):
- Input: `ModelName` (default `stock-prediction`), `Version`
- Preconditions: target exists; preferred statuses `canary` or `staging` (allow promote from either for ops flexibility)
- Actions (transactional where practical):
  1. Current `stable` (if any) → `archived`
  2. Target → `stable`
- Idempotent if target already `stable`

**Rollback**:
- Input: `Version` that was previously `stable`/`archived`
- Same mechanics as promote: archive current stable, set target `stable`
- Inference cache must invalidate by version (see §5)

## 4. Application-level canary (Phase 0)

### Serving selection
Inference resolves models as follows:
1. Query recent versions for `ModelName` (existing pattern, limit ≥ 10)
2. Collect at most one `stable` and one `canary` item (latest by Version SK desc)
3. Traffic split via env `CANARY_TRAFFIC_PERCENT` (default `10`):
   - If both exist: with probability `p` use canary, else stable
   - If only stable: 100% stable
   - If only canary: 100% canary (bootstrap / early demo)
   - If neither: error (unchanged “no stable model” semantics, message updated)

### Response contract
Keep existing JSON; always return `model_version` so demos prove which lane was hit. Optionally add `serving_lane: "stable"|"canary"` (non-breaking additive field) for clearer demos.

### Why not Lambda alias yet
Faster to ship, Free-Tier friendly, matches registry-driven rollback story. Phase 2 moves traffic control into AWS alias weights without abandoning registry statuses as the source of truth for “which artifact is canary/stable”.

## 5. Inference cache invalidation

Problem: warm Lambda may keep an old ONNX session after promote/rollback.

**Design**:
- Cache key = `model_version` (and lane if needed)
- On each request (or once per invoke after resolve): if resolved version ≠ cached version → download ONNX + rebuild session
- `/tmp/model.onnx` overwrite is fine; protect with existing mutex

## 6. Phased delivery

### Phase 0 — Closed loop (priority)
**Scope**
- Training: status `staging` / auto `canary` + threshold env + gate metadata
- Scripts + Makefile: `promote-stable`, `rollback`, optionally `list-models`
- Inference: dual-model resolve + traffic % + cache invalidation + optional `serving_lane`
- Docs: README demo path; ADR note for promotion policy; update `registry/schema.md` status flow
- Bootstrap: document “first model: if gate fails, `make promote-stable` from staging”

**Out of scope**: Lambda alias weights, feature store writes, OIDC

**Done when**: Upload CSV → canary/staging visible → promote → predict shows version → rollback → predict shows old version

### Phase 1 — Platform baseline
**Scope**
- Fix CloudWatch log group naming to `/aws/lambda/...`
- Alarms: Training Lambda errors; Inference errors; API Gateway 5XX (SNS email reuse Budgets pattern if possible)
- CI on PR: `terraform validate` (+ fmt check), `tests/test_train_local.py` (or `make test-local-training` without long Docker if flaky)
- Optional: GitHub OIDC for deploy workflow (replace long-lived keys)
- Smoke: post-deploy or Makefile target hitting `/health` + `/predict` after promote

**Done when**: Failed train/infer can alert; PR CI catches basic breakage; demo still works

### Phase 2 — Alias canary upgrade
**Scope**
- Publish inference Lambda versions; alias `live` with `routing_config` weights
- API Gateway integration targets alias ARN
- Ops: Makefile/scripts to set weights (e.g. 10/90) and shift 100% after soak
- Align registry: promoting to `stable` may still be metadata; alias weights become traffic mechanism — document dual-control clearly (registry = which artifact/version metadata; alias = AWS traffic)
- Prefer: build **two** published versions only when running “code canary”; for **model** canary, Phase 0 app split remains primary unless we deploy two configs — **clarification locked below**

**Phase 2 model-vs-code canary (locked)**:  
Phase 0 app-level split covers **model** canary (different ONNX via registry). Phase 2 alias weights cover **code/image** canary (two Lambda versions). Both can coexist; demos explain the difference.

**Done when**: Can shift inference **code** traffic via alias weights without redeploying API Gateway routes

## 7. Components & interfaces

| Unit | Responsibility | Interface |
|------|----------------|-----------|
| `training/train.py` | Train, export, register with gate | Env thresholds; DynamoDB PutItem |
| `scripts/promote_model.py` | Promote / rollback / list | CLI flags; DynamoDB UpdateItem |
| `Makefile` | DX wrappers | `promote-stable`, `rollback`, `list-models` |
| `inference/main.go` | Resolve lane, load ONNX, predict | Env `CANARY_TRAFFIC_PERCENT`; response fields |
| `infra/modules/lambda` | Env vars for thresholds / canary % | Terraform variables |
| `infra/modules/cloudwatch` (P1) | Log groups + alarms | SNS / email |
| `.github/workflows` (P1/P2) | PR checks; deploy OIDC | GitHub Actions |

## 8. Error handling

| Case | Behavior |
|------|----------|
| Metrics missing / NaN | Stay `staging`; log warning |
| Promote unknown version | Non-zero exit; clear error |
| Promote while no prior stable | Target → `stable` only |
| Inference no canary/stable | HTTP 503 with actionable message (“promote a model”) |
| ONNX download fail | HTTP 500; log version + S3 key |
| Concurrent promote | Last writer wins; accept for Free-Tier demo (no locking required in P0) |

## 9. Testing

**Phase 0**
- Unit: gate function (pass/fail → status)
- Unit/integration: promote transitions (mock DynamoDB or localstack if already available; else pure function tests + documented manual AWS check)
- Inference: table-driven tests for lane selection given fake registry items + RNG seed
- Manual E2E checklist in README

**Phase 1**
- PR CI runs train local test + terraform validate
- Optional smoke against deployed API when secrets present

**Phase 2**
- Document alias weight verify via AWS CLI `get-alias`

## 10. Non-goals (defer)

- Full feature store pipeline writes
- Experiment tracking UI / MLflow
- Great Expectations-scale data quality
- Terraform remote state (recommend later for multi-device)
- API auth (API key) — schedule after P0 if public URL risk matters
- Replacing Kubernetes badge noise (chore: remove misleading badges)

## 11. Success metrics

- E2E demo under ~10 minutes with Makefile only
- Rollback visible in next `/predict` without redeploy
- Clear verbal story: registry lifecycle vs future alias code canary
- Free Tier posture unchanged (no ALB/Fargate/NAT)

## 12. Open parameters (defaults, tunable later)

| Parameter | Default | Notes |
|-----------|---------|-------|
| `CANARY_TRAFFIC_PERCENT` | `10` | App-level only |
| `RMSE_THRESHOLD` | `100.0` | Loose for first demos; tighten after baseline |
| `MAE_THRESHOLD` | `80.0` | Same |
| Query limit for resolve | `20` | Enough to find latest stable+canary |
