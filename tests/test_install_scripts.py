import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestInstallScriptsIssue10(unittest.TestCase):
    def test_install_sh_symlinks_existing_aim_cron_entrypoint(self):
        install_sh = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn('ln -sf "$DIR/bin/aim-cron" ~/.local/bin/aim-cron', install_sh)
        self.assertNotIn("aim-dash", install_sh)
        self.assertTrue((ROOT / "bin" / "aim-cron").exists())

    def test_aim_cron_launcher_references_install_sh(self):
        aim_cron = (ROOT / "bin" / "aim-cron").read_text(encoding="utf-8")
        self.assertIn("Please run: ./install.sh", aim_cron)
        self.assertNotIn("./scripts/setup.sh", aim_cron)


if __name__ == "__main__":
    unittest.main()
