"""Exercise production renewal control flow without ACME or live services."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CertificateTests(unittest.TestCase):
    def test_ip_issuance_arguments(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            fake = tmp/'certbot'
            fake.write_text('#!/bin/bash\nprintf "%s\\n" "$@" > "$CAPTURE"\n')
            fake.chmod(0o755)
            source = (ROOT/'lib/certs.sh').read_text().replace('/opt/single443-certbot-5.8.0/bin/certbot', str(fake))
            (tmp/'certs.sh').write_text(source)
            script = '''source "$MODULE"
prepare_ip_certbot() { :; }
chmod() { :; }
helper() { case $2 in domain) echo 8.8.8.8;; reality_domain) echo 8-8-8-8.cdn-one.org;; ip_tls) echo yes;; esac; }
ACME_EMAIL= ACME_STAGING=no
obtain_cert
'''
            subprocess.run(['bash', '-c', script], check=True, env=dict(os.environ, MODULE=str(tmp/'certs.sh'), CAPTURE=str(tmp/'args')))
            args = (tmp/'args').read_text().splitlines()
            self.assertEqual(args[args.index('--ip-address')+1], '8.8.8.8')
            self.assertEqual(args[args.index('-d')+1], '8-8-8-8.cdn-one.org')
            self.assertEqual(args[args.index('--required-profile')+1], 'shortlived')
            self.assertEqual(args[args.index('--config-dir')+1], '/etc/single443/acme')
            self.assertIn('--no-directory-hooks', args)
            self.assertEqual(args.count('-d'), 1)

    @unittest.skipUnless(shutil.which('flock') and shutil.which('sha256sum'), 'Linux renewal tools required')
    def test_reload_failure_retried_without_reissuance(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            lineage = tmp/'acme/live/single443'
            lineage.mkdir(parents=True)
            (lineage/'fullchain.pem').write_text('test certificate')
            hook = tmp/'acme/renewal-hooks/deploy/single443'
            hook.parent.mkdir(parents=True)
            hook.write_text('#!/bin/bash\necho called >> "$CALLS"\n[[ ! -f "$FAIL" ]]\n')
            hook.chmod(0o755)
            bot = tmp/'certbot'
            bot.write_text('#!/bin/bash\nexit 0\n')
            bot.chmod(0o755)
            source = (ROOT/'lib/renew-ip.sh').read_text().replace('/etc/single443/acme',str(tmp/'acme')).replace('/run/lock/single443.lock',str(tmp/'lock')).replace('/opt/single443-certbot-5.8.0/bin/certbot',str(bot))
            runner = tmp/'renew.sh'; runner.write_text(source)
            env = dict(os.environ, CALLS=str(tmp/'calls'), FAIL=str(tmp/'fail'))
            (tmp/'fail').touch()
            self.assertNotEqual(subprocess.run(['bash',str(runner)],env=env).returncode,0)
            marker = tmp/'acme/last-deployed-sha256'
            self.assertFalse(marker.exists())
            (tmp/'fail').unlink()
            subprocess.run(['bash',str(runner)],env=env,check=True)
            self.assertTrue(marker.exists())
            subprocess.run(['bash',str(runner)],env=env,check=True)
            self.assertEqual((tmp/'calls').read_text().splitlines(),['called','called'])
