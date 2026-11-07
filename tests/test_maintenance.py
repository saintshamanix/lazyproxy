"""Exercise cleanup ordering and scheduling without touching host logs/packages."""
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]

class MaintenanceTests(unittest.TestCase):
    def run_case(self, age, autoremove='no', fail=False):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name in ('state', 'logs', 'bin'):
                (base/name).mkdir()
            stamp = str(int(time.time())-age)
            (base/'state/last-success').write_text(stamp+'\n')
            (base/'logs/access.log').write_text('access data')
            (base/'logs/error.log').write_text('error data')
            (base/'logs/access.log.1').write_text('archive')
            for name in ('journalctl', 'apt-get'):
                command = base/'bin'/name
                command.write_text('#!/bin/sh\nprintf "%s\\n" "'+name+' $*" >> "$CALLS"\n'+
                                   ('exit 1\n' if fail and name == 'journalctl' else 'exit 0\n'))
                command.chmod(0o755)
            env = dict(os.environ, PATH=str(base/'bin')+':'+os.environ['PATH'],
                       CALLS=str(base/'calls'), MAINTENANCE_STATE=str(base/'state'),
                       NGINX_LOG_DIR=str(base/'logs'), AUTO_REMOVE=autoremove)
            result = subprocess.run(['bash', '-c', 'source "$1"; maintenance_run', 'test', str(ROOT/'maintenance.sh')],
                                    env=env, capture_output=True, text=True)
            calls = (base/'calls').read_text() if (base/'calls').exists() else ''
            return result, calls, (base/'state/last-success').read_text().strip() != stamp, (base/'logs/access.log').read_text(), (base/'logs/access.log.1').read_text()

    def test_not_due_does_not_clean(self):
        result, calls, changed, log, archive = self.run_case(3600)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls, '')
        self.assertFalse(changed)
        self.assertEqual(log, 'access data')
        self.assertEqual(archive, 'archive')

    def test_due_rotates_vacuums_cleans_without_removing_packages(self):
        result, calls, changed, log, archive = self.run_case(259201)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('journalctl --rotate --vacuum-time=1d --vacuum-size=10M', calls)
        self.assertIn('apt-get -o DPkg::Lock::Timeout=120 clean', calls)
        self.assertNotIn('autoremove', calls)
        self.assertTrue(changed)
        self.assertEqual(log, '')
        self.assertEqual(archive, 'archive')

    def test_opt_in_autoremove(self):
        result, calls, changed, _, _ = self.run_case(259201, autoremove='yes')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('autoremove --purge -y', calls)
        self.assertTrue(changed)

    def test_failure_does_not_advance_schedule_or_run_apt(self):
        result, calls, changed, _, _ = self.run_case(259201, fail=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(changed)
        self.assertNotIn('apt-get', calls)
