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
