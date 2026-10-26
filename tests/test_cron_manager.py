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


class TestCronManagerIssue11(unittest.TestCase):
    def test_get_crontab_records_line_index(self):
        sample_crontab = "\n".join([
            "# header comment",
            "0 1 * * * /bin/job1",
            "",
            "# 0 2 * * * /bin/job2",
        ])
        mock_result = MagicMock(stdout=sample_crontab, returncode=0)
        with patch("subprocess.run", return_value=mock_result):
            jobs = CronManager.get_crontab()

        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["line_index"], 1)
        self.assertEqual(jobs[1]["line_index"], 3)

    def test_edit_job_updates_only_targeted_line_index_and_preserves_paused_state(self):
        sample_crontab = "\n".join([
            "# header",
            "0 4 * * * /bin/same_cmd",
            "# @daily /bin/paused_cmd",
            "0 4 * * * /bin/same_cmd",
        ])
        with patch.object(CronManager, "get_crontab_raw", return_value=sample_crontab), \
             patch.object(CronManager, "save_crontab") as mock_save:
            # Edit the second identical job at line_index=3
            CronManager.edit_job(
                target_raw_line="0 4 * * * /bin/same_cmd",
                new_schedule="*/10 * * * *",
                new_cmd="/bin/updated_cmd --fast",
                line_index=3,
                is_paused=False,
            )
            mock_save.assert_called_once_with([
                "# header",
                "0 4 * * * /bin/same_cmd",
                "# @daily /bin/paused_cmd",
                "*/10 * * * * /bin/updated_cmd --fast",
            ])

        with patch.object(CronManager, "get_crontab_raw", return_value=sample_crontab), \
             patch.object(CronManager, "save_crontab") as mock_save_paused:
            # Edit the paused job at line_index=2 and keep it paused
            CronManager.edit_job(
                target_raw_line="# @daily /bin/paused_cmd",
                new_schedule="@weekly",
                new_cmd="/bin/paused_weekly",
                line_index=2,
                is_paused=True,
            )
            mock_save_paused.assert_called_once_with([
                "# header",
                "0 4 * * * /bin/same_cmd",
                "# @weekly /bin/paused_weekly",
                "0 4 * * * /bin/same_cmd",
            ])

    def test_delete_and_toggle_job_respect_line_index_on_duplicate_lines(self):
        sample_crontab = "\n".join([
            "0 4 * * * /bin/dup_cmd",
            "0 4 * * * /bin/dup_cmd",
        ])
        with patch.object(CronManager, "get_crontab_raw", return_value=sample_crontab), \
             patch.object(CronManager, "save_crontab") as mock_save_del:
            CronManager.delete_job("0 4 * * * /bin/dup_cmd", line_index=1)
            mock_save_del.assert_called_once_with(["0 4 * * * /bin/dup_cmd"])

        with patch.object(CronManager, "get_crontab_raw", return_value=sample_crontab), \
             patch.object(CronManager, "save_crontab") as mock_save_tog:
            CronManager.toggle_job("0 4 * * * /bin/dup_cmd", line_index=0)
            mock_save_tog.assert_called_once_with([
                "# 0 4 * * * /bin/dup_cmd",
                "0 4 * * * /bin/dup_cmd",
            ])

    def test_new_job_modal_stores_initial_values_for_editing(self):
        modal = dashboard.NewJobModal(
            initial_schedule="@daily",
            initial_cmd="/usr/local/bin/backup.sh",
            title="Edit Cron Job",
        )
        self.assertEqual(modal.initial_schedule, "@daily")
        self.assertEqual(modal.initial_cmd, "/usr/local/bin/backup.sh")
        self.assertEqual(modal.dialog_title, "Edit Cron Job")


class TestCronManagerIssue12(unittest.TestCase):
    def test_list_backups_and_restore_backup(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir)
            b1 = backup_dir / "crontab.bak.20261025_120000"
            b2 = backup_dir / "crontab.bak.20261026_153000"
            b1.write_text("# header\n0 4 * * * /bin/old_job\n", encoding="utf-8")
            b2.write_text("@daily /bin/new_job1\n*/5 * * * * /bin/new_job2\n", encoding="utf-8")

            with patch.object(CronManager, "get_backup_dir", return_value=backup_dir):
                backups = CronManager.list_backups()
                self.assertEqual(len(backups), 2)
                # Newest first
                self.assertEqual(backups[0]["name"], "crontab.bak.20261026_153000")
                self.assertEqual(backups[0]["timestamp"], "2026-10-26 15:30:00")
                self.assertEqual(backups[0]["job_count"], 2)
                self.assertEqual(backups[1]["name"], "crontab.bak.20261025_120000")
                self.assertEqual(backups[1]["timestamp"], "2026-10-25 12:00:00")
                self.assertEqual(backups[1]["job_count"], 1)

                with patch.object(CronManager, "save_crontab") as mock_save:
                    CronManager.restore_backup(b1)
                    mock_save.assert_called_once_with(["# header", "0 4 * * * /bin/old_job"])

                modal = dashboard.RestoreBackupModal(backups)
                self.assertEqual(len(modal.backups), 2)


class TestCronManagerIssue13(unittest.TestCase):
    def test_load_and_save_settings_persistence(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            settings_file = Path(tmpdir) / "settings.json"
            with patch.object(CronManager, "get_settings_path", return_value=settings_file):
                # Default settings when file does not exist
                defaults = CronManager.load_settings()
                self.assertTrue(defaults["show_ai_badges"])
                self.assertTrue(defaults["confirm_force_run"])
                self.assertEqual(defaults["left_panel_size"], 60)
                self.assertTrue(defaults["is_horizontal"])
                self.assertFalse(defaults["is_swapped"])

                # Save custom settings and reload
                custom = {
                    "show_ai_badges": False,
                    "confirm_force_run": False,
                    "left_panel_size": 75,
                    "is_horizontal": False,
                    "is_swapped": True,
                }
                CronManager.save_settings(custom)
                self.assertTrue(settings_file.is_file())
                reloaded = CronManager.load_settings()
                self.assertEqual(reloaded, custom)

    def test_execute_command_capture_records_output_and_exit_status(self):
        mock_proc_ok = MagicMock()
        mock_proc_ok.communicate.return_value = ("Backup completed successfully\n", None)
        mock_proc_ok.returncode = 0

        with patch("subprocess.Popen", return_value=mock_proc_ok) as mock_popen:
            res_ok = CronManager.execute_command_capture("/bin/echo hello")
            mock_popen.assert_called_once()
            self.assertEqual(res_ok["status"], "OK")
            self.assertEqual(res_ok["returncode"], 0)
            self.assertIn("Backup completed successfully", res_ok["output"])

        mock_proc_fail = MagicMock()
        mock_proc_fail.communicate.return_value = ("Permission denied\n", None)
        mock_proc_fail.returncode = 1

        with patch("subprocess.Popen", return_value=mock_proc_fail):
            res_fail = CronManager.execute_command_capture("/bin/false")
            self.assertEqual(res_fail["status"], "FAIL")
            self.assertEqual(res_fail["returncode"], 1)
            self.assertIn("Permission denied", res_fail["output"])


if __name__ == "__main__":
    unittest.main()
