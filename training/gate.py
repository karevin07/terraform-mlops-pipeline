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
