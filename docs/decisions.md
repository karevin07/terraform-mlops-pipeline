# Architecture Decisions Records (ADR)

[English](decisions.md) | [繁體中文](decisions_zh-TW.md)

## 1. Use of AWS Free Tier
**Context**: Need to build a cost-effective MLOps pipeline for learning and demonstration.
**Decision**: Use AWS Free Tier eligible services only. Strictly avoided ECS Fargate, ALB, and NAT Gateway.
**Consequences**: All compute runs on Lambda; API routing via API Gateway HTTP API.

## 2. Lambda Instead of ECS Fargate
**Context**: ECS Fargate has **no Free Tier**. ALB also has no Free Tier.
**Decision**: Use Lambda (400,000 GB-seconds free/month) + API Gateway (1M free calls/mo for 12 months).
**Trade-offs**:
- Lambda has 15-min timeout (Hard limit) → acceptable for small model training.
- Lambda has 10GB memory limit → sufficient for lightweight models (Scikit-learn).
- Cold start latency → mitigated by keeping inference Lambda warm if needed.
**Benefits**:
- **Zero cost** at low volume.
- No infrastructure management (Serverless).
- Scales to zero automatically.

## 3. Python for Training, Go for Inference (via ONNX)
**Context**: Training is naturally done in the Python ML ecosystem. Serving benefits from a smaller, faster runtime and a language-neutral model format.
**Decision**:
- **Training Lambda**: Python (`scikit-learn`, `pandas`, `skl2onnx`).
- **Inference Lambda**: Go (`Gin` + ONNX Runtime).
- **Interchange format**: Export both `model.joblib` (debug / lineage) and `model.onnx` (serving). Inference loads `OnnxUrl` from DynamoDB.
**Consequences**:
- Clear separation of concerns between train and serve.
- Slightly more complex dual-language repo and Docker builds.
- Avoids shipping heavy Python ML deps in the inference image.

## 4. Custom Model Registry (DynamoDB + S3)
**Context**: Need version control for models without the overhead/cost of a full MLflow server or SageMaker Model Registry (which incurs costs).
**Decision**: Use **S3** for artifact storage and **DynamoDB** for metadata.
**Consequences**: Simple, serverless, and cost-effective. Version switch = DynamoDB metadata update (promote `Status` / point to another `OnnxUrl`).

## 5. AWS Budgets as Cost Guardrail
**Context**: Need automated alerting if any resource accidentally incurs cost.
**Decision**: Set AWS Budgets alarm at **$0.01 threshold** with email notification.
**Consequences**: Immediate notification on any non-Free-Tier usage.
