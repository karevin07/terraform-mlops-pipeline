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
