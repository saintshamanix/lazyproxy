import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('engine', Path(__file__).resolve().parents[1]/'lib/engine.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)

class PanelVersionTests(unittest.TestCase):
    def test_exact_supported_versions_only(self):
        for value in ('3.8.5', 'v3.8.5', '3.9.0\n', 'v3.9.0'):
            with patch.object(e.subprocess, 'check_output', return_value=value):
                self.assertIn(e.panel_version(), e.SUPPORTED_PANEL_VERSIONS)
        for value in ('3.9.1', '3.9.0-dev', '', 'error 3.9.0'):
            with patch.object(e.subprocess, 'check_output', return_value=value), self.assertRaises(RuntimeError):
                e.panel_version()

    def test_ui_upgrade_sync_preserves_both_topologies_and_credentials(self):
        for secondary in (None, '77.222.37.91'):
            with tempfile.TemporaryDirectory() as tmp, patch.object(e, 'STATE', Path(tmp)):
                state = dict(installed_version='v3.8.5', ip='77.222.54.106',
                             private_key='unchanged', sub_ids={'reality':'unchanged'},
                             inbound_ids={'reality':1,'hysteria':5,'amneziawg':6})
                if secondary:
                    state['secondary_ip'] = secondary
                e.save(state)
                with patch.object(e, 'panel_version', return_value='v3.9.0'):
                    e.sync_panel_version()
                    expected = dict(state, installed_version='v3.9.0')
                    self.assertEqual(e.load(), expected)
                    e.sync_panel_version()
                    self.assertEqual(e.load(), expected)
                before = (Path(tmp)/'state.json').read_bytes()
                with patch.object(e, 'panel_version', side_effect=RuntimeError('Unsupported')), self.assertRaises(RuntimeError):
                    e.sync_panel_version()
                self.assertEqual((Path(tmp)/'state.json').read_bytes(), before)
