import json
import unittest
from unittest.mock import patch, Mock
from test_engine import e


class AwgListenerTests(unittest.TestCase):
    def required(self, clients):
        row = dict(id=6, protocol='amneziawg', enable=True,
                   settings=json.dumps(dict(clients=clients)))
        with patch.object(e, 'API', return_value=Mock(call=Mock(return_value=[row]))):
            return e.awg_listener_required({'inbound_ids': {'amneziawg': 6}})

    def test_empty_inbound_does_not_require_socket(self):
        self.assertFalse(self.required([]))

    def test_manually_added_peer_requires_socket(self):
        self.assertTrue(self.required([{'email': 'manual', 'enable': True}]))

    def test_malformed_clients_fail_closed(self):
        with self.assertRaises(RuntimeError):
            self.required(None)

    def test_missing_inbound_fails_closed(self):
        with patch.object(e, 'API', return_value=Mock(call=Mock(return_value=[]))):
            with self.assertRaises(RuntimeError):
                e.awg_listener_required({'inbound_ids': {'amneziawg': 6}})

    def test_empty_secondary_checks_hysteria_and_wildcards(self):
        with patch.object(e, 'wait_udp') as wait, patch.object(e.subprocess, 'check_output', return_value=''):
            e.verify_secondary_sockets({'ip': '192.0.2.1', 'secondary_ip': '192.0.2.2'}, False)
            wait.assert_called_once_with('192.0.2.1', 443, 'xray')
