# Phase 0: Model Lifecycle Closed Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the train → staging/canary → manual stable → predict → rollback loop with app-level canary traffic and cache invalidation.

**Architecture:** Training registers models as `staging`, auto-promotes to `canary` when RMSE/MAE pass env thresholds. Ops CLI promotes/rollbacks DynamoDB statuses. Inference picks `canary` vs `stable` by `CANARY_TRAFFIC_PERCENT`, reloads ONNX when the resolved version changes.

**Tech Stack:** Python 3.9 + boto3 (training/CLI), Go + Gin + ONNX Runtime (inference), Terraform Lambda env vars, Makefile DX, unittest + Go testing.

**Spec:** `docs/superpowers/specs/2026-07-31-mlops-portfolio-roadmap-design.md` (Phase 0 only)

---

## File map

| File | Responsibility |
|------|----------------|
| `training/gate.py` | Pure `decide_status(metrics, rmse_threshold, mae_threshold) -> str` |
| `training/train.py` | Call gate in `register_model`; read threshold env; write `Config` |
| `tests/test_gate.py` | Unit tests for gate |
| `scripts/promote_model.py` | CLI: `promote` / `rollback` / `list` against DynamoDB |
| `tests/test_promote_model.py` | Pure transition logic tests (extract helpers from script) |
| `inference/lane.go` | Pure lane selection + traffic split (testable without ONNX) |
| `inference/lane_test.go` | Table-driven Go tests |
| `inference/main.go` | Wire lane resolve, `serving_lane` response, version-aware cache |
| `infra/modules/lambda/main.tf` | Env: thresholds + `CANARY_TRAFFIC_PERCENT` |
| `infra/modules/lambda/variables.tf` | Optional vars with defaults |
| `Makefile` | `promote-stable`, `rollback`, `list-models`; fix `check-metadata` |
| `registry/schema.md` | Status flow + Config |
| `docs/decisions.md` + `docs/decisions_zh-TW.md` | ADR for promotion policy |
| `README.md` + `README_zh-TW.md` | Demo checklist |

---

### Task 1: Metrics gate (pure Python)

**Files:**
- Create: `training/gate.py`
- Create: `tests/test_gate.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_gate.py
import unittest
from training.gate import decide_status


class TestDecideStatus(unittest.TestCase):
    def test_pass_gate_returns_canary(self):
        self.assertEqual(
            decide_status({"rmse": 10.0, "mae": 5.0}, 100.0, 80.0),
            "canary",
        )

    def test_fail_rmse_returns_staging(self):
        self.assertEqual(
            decide_status({"rmse": 150.0, "mae": 5.0}, 100.0, 80.0),
            "staging",
        )

    def test_fail_mae_returns_staging(self):
        self.assertEqual(
            decide_status({"rmse": 10.0, "mae": 90.0}, 100.0, 80.0),
            "staging",
        )

    def test_missing_metric_returns_staging(self):
        self.assertEqual(decide_status({"rmse": 1.0}, 100.0, 80.0), "staging")
        self.assertEqual(decide_status({}, 100.0, 80.0), "staging")

    def test_boundary_equal_passes(self):
        self.assertEqual(
            decide_status({"rmse": 100.0, "mae": 80.0}, 100.0, 80.0),
            "canary",
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m unittest tests.test_gate -v`

Expected: FAIL (`ModuleNotFoundError: No module named 'training.gate'` or import error)

- [ ] **Step 3: Implement gate**

```python
# training/gate.py
"""Promotion gate: staging vs canary based on evaluation metrics."""


def decide_status(metrics, rmse_threshold, mae_threshold):
    """
    Return 'canary' if rmse and mae are present and both <= thresholds;
    otherwise 'staging'. Never returns 'stable'.
    """
    try:
        rmse = float(metrics["rmse"])
        mae = float(metrics["mae"])
    except (KeyError, TypeError, ValueError):
        return "staging"

    if rmse <= float(rmse_threshold) and mae <= float(mae_threshold):
        return "canary"
    return "staging"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m unittest tests.test_gate -v`

Expected: OK (5 tests)

- [ ] **Step 5: Commit**

```bash
git add training/gate.py tests/test_gate.py
git commit -m "$(cat <<'EOF'
feat(training): add metrics gate for staging vs canary

EOF
)"
```

---

### Task 2: Wire gate into training registration

**Files:**
- Modify: `training/train.py`
- Modify: `tests/test_train_local.py` (assert register uses gate if mocked; keep existing flow green)

- [ ] **Step 1: Add threshold env + update `register_model`**

In `training/train.py`, after existing env config block, add:

```python
RMSE_THRESHOLD = float(os.environ.get("RMSE_THRESHOLD", "100.0"))
MAE_THRESHOLD = float(os.environ.get("MAE_THRESHOLD", "80.0"))
```

Add import:

```python
from training.gate import decide_status
```

Replace `register_model` with:

```python
def register_model(model_name, version, metrics, artifact_path):
    status = decide_status(metrics, RMSE_THRESHOLD, MAE_THRESHOLD)
    logger.info(
        f"Registering model {model_name}:{version} status={status} "
        f"(rmse_th={RMSE_THRESHOLD}, mae_th={MAE_THRESHOLD})"
    )
    item = {
        "ModelName": model_name,
        "Version": version,
        "Status": status,
        "Metrics": json.dumps(metrics),
        "ArtifactUrl": artifact_path,
        "OnnxUrl": artifact_path.replace(".joblib", ".onnx"),
        "CreatedAt": datetime.utcnow().isoformat(),
        "Config": json.dumps(
            {
                "rmse_threshold": RMSE_THRESHOLD,
                "mae_threshold": MAE_THRESHOLD,
                "gate_status": status,
            }
        ),
    }
    table.put_item(Item=item)
```

Also include `status` in the Lambda success body:

```python
status = decide_status(metrics, RMSE_THRESHOLD, MAE_THRESHOLD)
# ... after save artifacts ...
register_model(...)
return {
    "statusCode": 200,
    "body": json.dumps(
        {
            "message": "Training successful",
            "version": version,
            "metrics": metrics,
            "status": status,
        }
    ),
}
```

Note: avoid calling `decide_status` twice — compute once before `register_model` and pass `status` into `register_model` instead:

```python
def register_model(model_name, version, metrics, artifact_path, status):
    ...
```

- [ ] **Step 2: Run local training test**

Run:

```bash
make generate-sample-data
export S3_RAW_BUCKET=test-bucket S3_MODEL_BUCKET=test-bucket DYNAMODB_TABLE=test-table AWS_REGION=us-east-1
uv run --extra training python -m unittest tests.test_train_local -v
uv run python -m unittest tests.test_gate -v
```

Expected: both suites PASS (mock DynamoDB/table as today)

- [ ] **Step 3: Commit**

```bash
git add training/train.py tests/test_train_local.py
git commit -m "$(cat <<'EOF'
feat(training): register models as staging or canary via gate

EOF
)"
```

---

### Task 3: Promote / rollback / list CLI (pure logic + script)

**Files:**
- Create: `scripts/promote_logic.py` (pure helpers, easy to unit test)
- Create: `scripts/promote_model.py` (CLI + boto3)
- Create: `tests/test_promote_logic.py`

- [ ] **Step 1: Write failing tests for transition planning**

```python
# tests/test_promote_logic.py
import unittest
from scripts.promote_logic import plan_promote, plan_rollback


class TestPromoteLogic(unittest.TestCase):
    def test_promote_archives_current_stable(self):
        plan = plan_promote(
            target_version="v2",
            target_status="canary",
            current_stable_version="v1",
        )
        self.assertEqual(
            plan,
            [
                {"version": "v1", "status": "archived"},
                {"version": "v2", "status": "stable"},
            ],
        )

    def test_promote_without_prior_stable(self):
        plan = plan_promote(
            target_version="v1",
            target_status="staging",
            current_stable_version=None,
        )
        self.assertEqual(plan, [{"version": "v1", "status": "stable"}])

    def test_promote_idempotent_when_already_stable(self):
        plan = plan_promote(
            target_version="v1",
            target_status="stable",
            current_stable_version="v1",
        )
        self.assertEqual(plan, [])

    def test_promote_rejects_missing_target(self):
        with self.assertRaises(ValueError):
            plan_promote(
                target_version="v9",
                target_status=None,
                current_stable_version="v1",
            )

    def test_rollback_same_as_promote_from_archived(self):
        plan = plan_rollback(
            target_version="v1",
            target_status="archived",
            current_stable_version="v2",
        )
        self.assertEqual(
            plan,
            [
                {"version": "v2", "status": "archived"},
                {"version": "v1", "status": "stable"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify fail**

Run: `uv run python -m unittest tests.test_promote_logic -v`

Expected: FAIL (import error)

- [ ] **Step 3: Implement pure logic**

```python
# scripts/promote_logic.py
"""Pure planning helpers for model promote/rollback (no AWS I/O)."""


def plan_promote(target_version, target_status, current_stable_version):
    if target_status is None:
        raise ValueError(f"target version not found: {target_version}")
    if target_status == "stable" and current_stable_version == target_version:
        return []
    actions = []
    if current_stable_version and current_stable_version != target_version:
        actions.append({"version": current_stable_version, "status": "archived"})
    actions.append({"version": target_version, "status": "stable"})
    return actions


def plan_rollback(target_version, target_status, current_stable_version):
    # Same transition rules; allow archived/staging/canary/stable sources
    return plan_promote(target_version, target_status, current_stable_version)
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `uv run python -m unittest tests.test_promote_logic -v`

- [ ] **Step 5: Implement CLI `scripts/promote_model.py`**

```python
#!/usr/bin/env python3
"""Promote / rollback / list model versions in DynamoDB registry."""
import argparse
import json
import os
import sys

import boto3
from boto3.dynamodb.conditions import Key

from scripts.promote_logic import plan_promote, plan_rollback

DEFAULT_MODEL = "stock-prediction"


def get_table():
    table_name = os.environ.get("DYNAMODB_TABLE")
    if not table_name:
        raise SystemExit("DYNAMODB_TABLE env var is required")
    region = os.environ.get("AWS_REGION", "us-east-1")
    return boto3.resource("dynamodb", region_name=region).Table(table_name)


def get_item(table, model_name, version):
    resp = table.get_item(Key={"ModelName": model_name, "Version": version})
    return resp.get("Item")


def find_stable_version(table, model_name):
    resp = table.query(
        KeyConditionExpression=Key("ModelName").eq(model_name),
        ScanIndexForward=False,
        Limit=50,
    )
    for item in resp.get("Items", []):
        if item.get("Status") == "stable":
            return item["Version"]
    return None


def apply_actions(table, model_name, actions, dry_run=False):
    for action in actions:
        print(f"{'[dry-run] ' if dry_run else ''}SET {model_name} {action['version']} -> {action['status']}")
        if dry_run:
            continue
        table.update_item(
            Key={"ModelName": model_name, "Version": action["version"]},
            UpdateExpression="SET #S = :s",
            ExpressionAttributeNames={"#S": "Status"},
            ExpressionAttributeValues={":s": action["status"]},
        )


def cmd_list(table, model_name, limit):
    resp = table.query(
        KeyConditionExpression=Key("ModelName").eq(model_name),
        ScanIndexForward=False,
        Limit=limit,
    )
    for item in resp.get("Items", []):
        metrics = item.get("Metrics", "{}")
        print(f"{item['Version']}\t{item.get('Status')}\t{metrics}")


def cmd_promote(table, model_name, version, dry_run=False):
    item = get_item(table, model_name, version)
    target_status = item.get("Status") if item else None
    current = find_stable_version(table, model_name)
    actions = plan_promote(version, target_status, current)
    if not actions:
        print(f"{version} already stable; nothing to do")
        return
    apply_actions(table, model_name, actions, dry_run=dry_run)


def cmd_rollback(table, model_name, version, dry_run=False):
    item = get_item(table, model_name, version)
    target_status = item.get("Status") if item else None
    current = find_stable_version(table, model_name)
    actions = plan_rollback(version, target_status, current)
    if not actions:
        print(f"{version} already stable; nothing to do")
        return
    apply_actions(table, model_name, actions, dry_run=dry_run)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Model registry promote/rollback")
    parser.add_argument("--model-name", default=DEFAULT_MODEL)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--limit", type=int, default=20)

    p_prom = sub.add_parser("promote")
    p_prom.add_argument("--version", required=True)
    p_prom.add_argument("--dry-run", action="store_true")

    p_rb = sub.add_parser("rollback")
    p_rb.add_argument("--version", required=True)
    p_rb.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    table = get_table()
    if args.command == "list":
        cmd_list(table, args.model_name, args.limit)
    elif args.command == "promote":
        cmd_promote(table, args.model_name, args.version, dry_run=args.dry_run)
    elif args.command == "rollback":
        cmd_rollback(table, args.model_name, args.version, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
```

Ensure `scripts/` is importable: tests already use `sys.path` project root; running via `uv run python scripts/promote_model.py` needs:

```python
# at top of promote_model.py if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

Prefer package-style: from repo root `uv run python -m` is awkward for scripts/; keep `sys.path.insert` as shown.

- [ ] **Step 6: Run unit tests again**

Run: `uv run python -m unittest tests.test_promote_logic -v`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add scripts/promote_logic.py scripts/promote_model.py tests/test_promote_logic.py
git commit -m "$(cat <<'EOF'
feat(registry): add promote/rollback/list CLI for model lifecycle

EOF
)"
```

---

### Task 4: Makefile DX + fix check-metadata

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Add targets after `check-metadata` section**

```makefile
list-models: ## List recent model registry versions
	uv run python scripts/promote_model.py list

promote-stable: ## Promote VERSION=... to stable (archives previous stable)
	@if [ -z "$(VERSION)" ]; then echo "Usage: make promote-stable VERSION=vYYYYMMDDHHMMSS"; exit 1; fi
	uv run python scripts/promote_model.py promote --version $(VERSION)

rollback: ## Rollback stable to VERSION=...
	@if [ -z "$(VERSION)" ]; then echo "Usage: make rollback VERSION=vYYYYMMDDHHMMSS"; exit 1; fi
	uv run python scripts/promote_model.py rollback --version $(VERSION)
```

- [ ] **Step 2: Fix `check-metadata` to show canary/staging/stable (not only training)**

Replace the scan filter with a query on `stock-prediction` (or remove filter and scan all). Preferred:

```makefile
check-metadata: ## List recent model registry items for stock-prediction
	aws dynamodb query \
		--table-name $(DYNAMODB_TABLE) \
		--key-condition-expression "ModelName = :m" \
		--expression-attribute-values '{":m": {"S": "stock-prediction"}}' \
		--scan-index-forward false \
		--limit 10 \
		--output json
```

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "$(cat <<'EOF'
chore(make): add promote/rollback/list and fix metadata query

EOF
)"
```

---

### Task 5: Inference lane selection (Go, pure + tests)

**Files:**
- Create: `inference/lane.go`
- Create: `inference/lane_test.go`

- [ ] **Step 1: Write failing Go tests**

```go
// inference/lane_test.go
package main

import "testing"

func TestSelectLane_BothPresent(t *testing.T) {
	stable := &RegistryModel{Version: "v1", OnnxURL: "s3://b/v1.onnx", Status: "stable"}
	canary := &RegistryModel{Version: "v2", OnnxURL: "s3://b/v2.onnx", Status: "canary"}

	got := SelectLane(stable, canary, 0) // 0% canary → always stable
	if got.Version != "v1" || got.Lane != "stable" {
		t.Fatalf("expected stable v1, got %+v", got)
	}

	got = SelectLane(stable, canary, 100) // 100% canary
	if got.Version != "v2" || got.Lane != "canary" {
		t.Fatalf("expected canary v2, got %+v", got)
	}
}

func TestSelectLane_OnlyCanary(t *testing.T) {
	canary := &RegistryModel{Version: "v2", OnnxURL: "s3://b/v2.onnx", Status: "canary"}
	got := SelectLane(nil, canary, 10)
	if got == nil || got.Version != "v2" {
		t.Fatalf("expected canary only, got %+v", got)
	}
}

func TestSelectLane_Neither(t *testing.T) {
	if SelectLane(nil, nil, 10) != nil {
		t.Fatal("expected nil")
	}
}

func TestPickCanary_DeterministicWithStub(t *testing.T) {
	// Inject rand by testing percent bounds via SelectLane 0 and 100 only (above).
}
```

- [ ] **Step 2: Run tests — expect fail**

Run: `cd inference && go test ./... -count=1`

Expected: FAIL (undefined types)

- [ ] **Step 3: Implement `lane.go`**

```go
// inference/lane.go
package main

import (
	"math/rand"
	"os"
	"strconv"
)

type RegistryModel struct {
	Version string
	OnnxURL string
	Status  string
}

type ServingChoice struct {
	Version string
	OnnxURL string
	Lane    string // "stable" | "canary"
}

func CanaryTrafficPercent() int {
	v := os.Getenv("CANARY_TRAFFIC_PERCENT")
	if v == "" {
		return 10
	}
	n, err := strconv.Atoi(v)
	if err != nil || n < 0 {
		return 10
	}
	if n > 100 {
		return 100
	}
	return n
}

// SelectLane chooses stable vs canary. percent is 0–100 canary probability when both exist.
// Uses math/rand global source (acceptable for traffic split demos).
func SelectLane(stable, canary *RegistryModel, canaryPercent int) *ServingChoice {
	if stable == nil && canary == nil {
		return nil
	}
	if canary == nil {
		return &ServingChoice{Version: stable.Version, OnnxURL: stable.OnnxURL, Lane: "stable"}
	}
	if stable == nil {
		return &ServingChoice{Version: canary.Version, OnnxURL: canary.OnnxURL, Lane: "canary"}
	}
	if canaryPercent >= 100 || (canaryPercent > 0 && rand.Intn(100) < canaryPercent) {
		return &ServingChoice{Version: canary.Version, OnnxURL: canary.OnnxURL, Lane: "canary"}
	}
	return &ServingChoice{Version: stable.Version, OnnxURL: stable.OnnxURL, Lane: "stable"}
}

// LatestStableAndCanary scans items already sorted newest-first.
func LatestStableAndCanary(items []RegistryModel) (stable, canary *RegistryModel) {
	for i := range items {
		it := &items[i]
		switch it.Status {
		case "stable":
			if stable == nil {
				stable = it
			}
		case "canary":
			if canary == nil {
				canary = it
			}
		}
		if stable != nil && canary != nil {
			break
		}
	}
	return stable, canary
}
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd inference && go test ./... -count=1`

- [ ] **Step 5: Commit**

```bash
git add inference/lane.go inference/lane_test.go
git commit -m "$(cat <<'EOF'
feat(inference): add app-level canary lane selection

EOF
)"
```

---

### Task 6: Wire inference resolve + cache invalidation + `serving_lane`

**Files:**
- Modify: `inference/main.go`

- [ ] **Step 1: Extend response type**

```go
type PredictResponse struct {
	PredictedPrice float32 `json:"predicted_price"`
	ModelVersion   string  `json:"model_version"`
	ServingLane    string  `json:"serving_lane"`
}
```

Add package-level:

```go
var servingLane string
```

- [ ] **Step 2: Change `ensureModelLoaded` to version-aware reload**

Replace the early “if modelCache != nil return” logic with resolve-first behavior:

1. If `LOCAL_MODEL_PATH` set → keep current local behavior (`serving_lane = "local"`).
2. Else query DynamoDB with `Limit: 20`.
3. Map items to `[]RegistryModel`.
4. `stable, canary := LatestStableAndCanary(items)`.
5. `choice := SelectLane(stable, canary, CanaryTrafficPercent())`.
6. If `choice == nil` → return error `"no stable or canary model found; run make promote-stable"`.
7. Under write lock: if `modelCache != nil && modelVersion == choice.Version` → set `servingLane = choice.Lane` and return nil (no download).
8. Else download `choice.OnnxURL`, create session, destroy/replace old session if API allows (if Destroy exists on session, call it; otherwise overwrite reference), set `modelVersion`, `servingLane`.

Update `handlePredict` (or whatever the predict handler is named — currently inline in router) to pass `ServingLane: servingLane` in JSON. Read `servingLane` under `RLock` together with session/version.

Update 503 message body to actionable text when load fails for missing model.

- [ ] **Step 3: Run Go tests + local container smoke (optional if Docker available)**

```bash
cd inference && go test ./... -count=1
# optional:
# make test-local-inference
```

Expected: tests PASS; local predict still works with `LOCAL_MODEL_PATH`.

- [ ] **Step 4: Commit**

```bash
git add inference/main.go
git commit -m "$(cat <<'EOF'
feat(inference): resolve canary/stable traffic and invalidate model cache

EOF
)"
```

---

### Task 7: Terraform env vars for thresholds and canary %

**Files:**
- Modify: `infra/modules/lambda/main.tf`
- Modify: `infra/modules/lambda/variables.tf` (add vars with defaults)

- [ ] **Step 1: Add variables**

```hcl
# infra/modules/lambda/variables.tf — append
variable "rmse_threshold" {
  type    = string
  default = "100.0"
}

variable "mae_threshold" {
  type    = string
  default = "80.0"
}

variable "canary_traffic_percent" {
  type    = string
  default = "10"
}
```

- [ ] **Step 2: Wire into Lambda environment**

Training `environment.variables` add:

```hcl
RMSE_THRESHOLD = var.rmse_threshold
MAE_THRESHOLD  = var.mae_threshold
```

Inference `environment.variables` add:

```hcl
CANARY_TRAFFIC_PERCENT = var.canary_traffic_percent
```

Root `infra/main.tf` module `"lambda"` can rely on defaults (no change required unless you want to expose root variables).

- [ ] **Step 3: Validate**

Run:

```bash
cd infra && terraform validate
```

Expected: Success (after `terraform init` if needed)

- [ ] **Step 4: Commit**

```bash
git add infra/modules/lambda/main.tf infra/modules/lambda/variables.tf
git commit -m "$(cat <<'EOF'
feat(infra): pass gate thresholds and canary traffic env to Lambdas

EOF
)"
```

---

### Task 8: Docs — schema, ADR, README demo path

**Files:**
- Modify: `registry/schema.md`
- Modify: `docs/decisions.md`
- Modify: `docs/decisions_zh-TW.md`
- Modify: `README.md`
- Modify: `README_zh-TW.md`

- [ ] **Step 1: Update `registry/schema.md` status flow**

Add a short “Lifecycle” section:

```markdown
## Lifecycle (Phase 0)

1. Training registers `staging`, or `canary` if RMSE/MAE pass thresholds.
2. Operator runs `make promote-stable VERSION=...` → `stable` (previous `stable` → `archived`).
3. `make rollback VERSION=...` restores an older version to `stable`.
4. Inference serves `stable` and optionally `canary` via `CANARY_TRAFFIC_PERCENT`.
```

Document `Config` as JSON string with `rmse_threshold`, `mae_threshold`, `gate_status`.

- [ ] **Step 2: Add ADR #6 to both decision files**

English:

```markdown
## 6. Registry Promotion Policy (staging → canary → stable)
**Context**: Inference only serves canary/stable; training must not silently become production.
**Decision**: Auto `staging`; auto `canary` on metric gate; manual `stable` via CLI; app-level canary traffic before Lambda alias weights.
**Consequences**: Clear demo story; requires operator promote for production lane.
```

Chinese equivalent in `docs/decisions_zh-TW.md`.

- [ ] **Step 3: README demo checklist (EN + ZH)**

Add section **Demo: model lifecycle**:

```bash
make fetch-data          # or upload CSV → triggers training
make check-metadata      # expect staging or canary
make list-models
make promote-stable VERSION=v...
make predict-lambda      # note model_version + serving_lane
make rollback VERSION=v...
make predict-lambda
```

Note: first-time bootstrap — if only `staging` exists, still `make promote-stable` from staging; if only `canary`, inference serves 100% canary until promote.

- [ ] **Step 4: Commit**

```bash
git add registry/schema.md docs/decisions.md docs/decisions_zh-TW.md README.md README_zh-TW.md
git commit -m "$(cat <<'EOF'
docs: document Phase 0 promotion lifecycle and demo path

EOF
)"
```

---

### Task 9: Phase 0 verification checklist

- [ ] **Step 1: Run all automated tests**

```bash
uv run python -m unittest tests.test_gate tests.test_promote_logic -v
uv run --extra training python -m unittest tests.test_train_local -v
cd inference && go test ./... -count=1
cd infra && terraform validate
```

Expected: all green

- [ ] **Step 2: Manual AWS E2E (when credentials + stack available)**

1. `make tf-apply` (picks up new env vars)  
2. Rebuild/push images: `make deploy-images` then `make deploy-inference-lambda` (+ training update analog if Makefile has it)  
3. `make fetch-data` → wait → `make list-models` shows `canary` or `staging`  
4. `make promote-stable VERSION=...` → `make predict-lambda` shows that version / `serving_lane=stable`  
5. Train again or keep prior version → `make rollback VERSION=...` → predict shows old version  

- [ ] **Step 3: Mark Phase 0 done in spec**

Set `Status: Phase 0 implemented` at top of  
`docs/superpowers/specs/2026-07-31-mlops-portfolio-roadmap-design.md`  
(or add a short note under Phase 0). Commit if status text changes:

```bash
git add docs/superpowers/specs/2026-07-31-mlops-portfolio-roadmap-design.md
git commit -m "$(cat <<'EOF'
docs: mark Phase 0 lifecycle closed loop as implemented

EOF
)"
```

---

## Spec coverage (self-review)

| Spec Phase 0 item | Task |
|-------------------|------|
| staging / auto canary + thresholds + Config | Task 1–2, 7 |
| promote / rollback / list Makefile | Task 3–4 |
| App canary traffic % | Task 5–6 |
| Cache invalidation by version | Task 6 |
| `serving_lane` response | Task 6 |
| Docs + demo path | Task 8 |
| Bootstrap staging promote | Task 8 README note |
| Out of scope alias/OIDC/feature store | Not in this plan |

## Placeholder scan

No TBD/TODO left in task steps; defaults match spec (`100.0` / `80.0` / `10`).
