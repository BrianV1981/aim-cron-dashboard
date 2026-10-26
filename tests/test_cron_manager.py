import subprocess
import unittest
from unittest.mock import MagicMock, patch
import importlib.util
from pathlib import Path

DASHBOARD_PATH = Path(__file__).resolve().parent.parent / "bin" / "dashboard.py"
spec = importlib.util.spec_from_file_location("dashboard", DASHBOARD_PATH)
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)
CronManager = dashboard.CronManager


class TestCronManagerIssue9(unittest.TestCase):
    def test_get_crontab_parses_standard_and_at_shortcuts_and_ignores_prose_comments(self):
        sample_crontab = "\n".join([
            "# Edit this file to introduce tasks to be run by cron.",
            "# Each task to run has to be defined through a single line",
            "# m h  dom mon dow   command",
            "SHELL=/bin/bash",
            "PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin",
            "",
            "0 4 * * * /usr/local/bin/nightly_sync.sh --verbose",
            "@daily /usr/local/bin/daily_backup.sh",
            "@reboot tmux new-session -d -s agent 'python3 run.py'",
            "# */15 * * * * /usr/local/bin/paused_five_field.sh",
            "# @midnight /usr/local/bin/paused_midnight.sh --flag 1",
        ])
        mock_result = MagicMock(stdout=sample_crontab, returncode=0)
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            jobs = CronManager.get_crontab()
            mock_run.assert_called_once_with(
                ["crontab", "-l"], capture_output=True, text=True, check=True
            )

        self.assertEqual(len(jobs), 5)

        # 1. Standard 5-field active job
        self.assertEqual(jobs[0]["raw_schedule"], "0 4 * * *")
        self.assertEqual(jobs[0]["cmd"], "/usr/local/bin/nightly_sync.sh --verbose")
        self.assertFalse(jobs[0]["is_paused"])

        # 2. @daily 2-token job (previously dropped because len(parts) < 6)
        self.assertEqual(jobs[1]["raw_schedule"], "@daily")
        self.assertEqual(jobs[1]["cmd"], "/usr/local/bin/daily_backup.sh")
        self.assertFalse(jobs[1]["is_paused"])
        self.assertNotEqual(jobs[1]["human_schedule"], "@daily")

        # 3. @reboot multi-word command (previously swallowed command tokens into schedule)
        self.assertEqual(jobs[2]["raw_schedule"], "@reboot")
        self.assertEqual(jobs[2]["cmd"], "tmux new-session -d -s agent 'python3 run.py'")
        self.assertFalse(jobs[2]["is_paused"])
        self.assertIn("startup", jobs[2]["human_schedule"].lower())

        # 4. Paused 5-field job
        self.assertEqual(jobs[3]["raw_schedule"], "*/15 * * * *")
        self.assertEqual(jobs[3]["cmd"], "/usr/local/bin/paused_five_field.sh")
        self.assertTrue(jobs[3]["is_paused"])
        self.assertTrue(jobs[3]["human_schedule"].startswith("[PAUSED] "))

        # 5. Paused @midnight job
        self.assertEqual(jobs[4]["raw_schedule"], "@midnight")
        self.assertEqual(jobs[4]["cmd"], "/usr/local/bin/paused_midnight.sh --flag 1")
        self.assertTrue(jobs[4]["is_paused"])
        self.assertTrue(jobs[4]["human_schedule"].startswith("[PAUSED] "))

    def test_validate_schedule_accepts_valid_expressions(self):
        valid_schedules = [
            "* * * * *",
            "0 4 * * *",
            "*/5 * * * *",
            "0 0 * * 1-5",
            "15,45 9-17/2 1,15 JAN-DEC MON-FRI",
            "0 0 * * 7",
            "@reboot",
            "@hourly",
            "@midnight",
            "@daily",
            "@weekly",
            "@monthly",
            "@yearly",
            "@annually",
        ]
        for sched in valid_schedules:
            with self.subTest(schedule=sched):
                ok, err = CronManager.validate_schedule(sched)
                self.assertTrue(ok, f"Expected '{sched}' to be valid, got error: {err}")
                self.assertEqual(err, "")

    def test_validate_schedule_rejects_invalid_expressions(self):
        invalid_schedules = [
            "",
            "@every5m",
            "* * * *",
            "* * * * * *",
            "60 * * * *",
            "0 24 * * *",
            "0 0 32 * *",
            "0 0 0 * *",
            "0 0 * 13 *",
            "0 0 * * 8",
            "*/0 * * * *",
            "10-5 * * * *",
            "Edit this file to introduce",
            "SHELL=/bin/bash",
        ]
        for sched in invalid_schedules:
            with self.subTest(schedule=sched):
                ok, err = CronManager.validate_schedule(sched)
                self.assertFalse(ok, f"Expected '{sched}' to be rejected as invalid")
                self.assertTrue(bool(err))

    def test_add_job_rejects_invalid_schedule_without_calling_crontab(self):
        with patch("subprocess.run") as mock_run:
            with self.assertRaises(ValueError):
                CronManager.add_job("60 25 * * *", "/bin/true")
            mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
