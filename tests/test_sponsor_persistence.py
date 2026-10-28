import ast
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
if (ROOT / 'lib/engine.py').exists():
    ENGINE = ROOT / 'lib/engine.py'
elif (ROOT.parent / 'lib/engine.py').exists():
    ROOT = ROOT.parent
    ENGINE = ROOT / 'lib/engine.py'
else:
    ENGINE = ROOT / 'engine.py'


def module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


installer = module(ROOT / 'install-sponsor-persistence.py')
filter_path = ROOT / 'disable-sponsor-fetch.py'
if not filter_path.exists():
    filter_path = ROOT.parent.parent / 'outputs/disable-sponsor-fetch.py'
filter_script = module(filter_path)
source = ENGINE.read_text()
tree = ast.parse(source)
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in ('require', 'preserve_sponsor_filter', 'render')]
render = next(node for node in functions if node.name == 'render')
# Exercise the actual production render/write loop, before unrelated routing output.
render.body = render.body[:next(i for i, node in enumerate(render.body)
                              if isinstance(node, ast.Assign)
                              and isinstance(node.targets[0], ast.Name)
                              and node.targets[0].id == 'main')]
namespace = {'Path': Path, 're': re}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(ENGINE), 'exec'), namespace)

WEB = '''server {
    listen 127.0.0.1:7443 ssl http2;
    server_name example.org;
    location ^~ /secret/ {
        proxy_pass http://127.0.0.1:2053;
    }
}
'''


class PersistenceTests(unittest.TestCase):
    def preserve(self, old, new=WEB, path='/secret/'):
        with tempfile.TemporaryDirectory() as tmp:
            current = Path(tmp) / 'web.conf'
            if old is not None:
                current.write_text(old)
            return namespace['preserve_sponsor_filter'](new, path, current)

    def test_fresh_install_not_enabled(self):
        self.assertEqual(self.preserve(None), WEB)

    def test_disabled_not_enabled(self):
        self.assertEqual(self.preserve(WEB), WEB)

    def test_existing_v1_filter_preserved(self):
        active = filter_script.plan(WEB)[0]
        self.assertEqual(self.preserve(active), active)

    def test_path_change_and_repeat(self):
        active = filter_script.plan(WEB)[0]
        new = WEB.replace('/secret/', '/new-path/')
        changed = self.preserve(active, new, '/new-path/')
        self.assertEqual(changed, filter_script.plan(new)[0])
        self.assertNotIn('/secret/', changed)
        self.assertEqual(self.preserve(changed, new, '/new-path/'), changed)

    def test_remove_stays_removed(self):
        active = filter_script.plan(WEB)[0]
        removed = filter_script.plan(active, True)[0]
        self.assertEqual(self.preserve(removed), WEB)

    def test_edited_filter_rejected(self):
        active = filter_script.plan(WEB)[0]
        for bad in (active.replace('return 404;', 'return 403;'),
                    active.replace(filter_script.END, ''), active + active):
            with self.assertRaises(RuntimeError):
                self.preserve(bad)

    def test_patcher_idempotent_and_preserves_unrelated_code(self):
        self.assertEqual(installer.patch_engine(source), source)
        original = source.replace(installer.HELPER, '').replace(installer.NEW, installer.OLD)
        original = original.replace('    rendered = []\n' + installer.LOOP, installer.LOOP)
        self.assertEqual(installer.patch_engine(original), source)

    def test_unknown_engine_rejected(self):
        with self.assertRaises(RuntimeError):
            installer.patch_engine('print("unrelated engine")\n')

    def test_render_validation_precedes_any_nginx_write(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / 'state'
            state.mkdir()
            (state / 'subscription.json').write_text('{}')
            templates = root / 'templates'
            templates.mkdir()
            (templates / 'nginx-web.conf.tpl').write_text(WEB)
            (templates / 'nginx-stream.conf.tpl').write_text('new stream')
            web, stream = root / 'web', root / 'stream'
            active = filter_script.plan(WEB)[0]
            web.write_text(active.replace('return 404;', 'return 403;'))
            stream.write_text('old stream')
            mapping = {'/etc/nginx/conf.d/single443-web.conf': web,
                       '/etc/nginx/single443-stream.conf': stream}
            def mapped(path):
                return mapping.get(str(path), Path(path))
            namespace.update(Path=mapped, STATE=state, json=json,
                             load=lambda: dict(domain='example.org', reality_domain='r.example.org',
                                               panel_path='/secret/', ws_path='/ws', xhttp_path='/xh',
                                               grpc_service='grpc'),
                             certificate_dir=lambda s: '/cert/', sub_locations=lambda d: '',
                             masque_route=lambda s: '')
            try:
                with self.assertRaises(RuntimeError):
                    namespace['render'](templates)
                self.assertEqual(stream.read_text(), 'old stream')
                web.write_text(active)
                namespace['render'](templates)
                self.assertEqual(web.read_text(), active)
                self.assertEqual(stream.read_text(), 'new stream')
            finally:
                namespace['Path'] = Path


if __name__ == '__main__':
    unittest.main()
