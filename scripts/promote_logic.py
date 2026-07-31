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
    return plan_promote(target_version, target_status, current_stable_version)
