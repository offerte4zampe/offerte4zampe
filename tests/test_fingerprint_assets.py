import json
import tempfile
import unittest
from pathlib import Path
from automation.fingerprint_assets import build,restore
class FingerprintedAssetsTests(unittest.TestCase):
    def test_dependencies_bytes_external_links_cache_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);assets=root/'assets';assets.mkdir()
            (assets/'worker.js').write_text('self.onmessage=()=>{}')
            (assets/'main.js').write_text("new Worker('assets/worker.js?v=1');const affiliate='https://tc.tradetracker.net/?u=assets/main.js';")
            (assets/'icon.svg').write_text('<svg/>')
            (assets/'style.css').write_text("body{background:url('icon.svg')}")
            (root/'index.html').write_text('<script src="assets/main.js"></script><link href="assets/style.css"><a href="https://shop.test/assets/main.js?affiliate=exact">Shop</a>')
            (root/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n')
            mapping=build(root);html=(root/'index.html').read_text();main=(root/mapping['main.js'].lstrip('/')).read_text()
            self.assertIn('src="'+mapping['main.js']+'"',html)
            self.assertIn('href="'+mapping['style.css']+'"',html)
            self.assertIn(mapping['worker.js'].lstrip('/')+'?v=1',main)
            self.assertIn('https://tc.tradetracker.net/?u=assets/main.js',main)
            self.assertIn('https://shop.test/assets/main.js?affiliate=exact',html)
            self.assertIn(' defer>',html)
            self.assertIn('max-age=31536000, immutable',(root/'_headers').read_text())
            self.assertIn('stale-while-revalidate=300',(root/'_headers').read_text())
            self.assertIn('nosniff',(root/'_headers').read_text())
            self.assertEqual(mapping,build(root));self.assertEqual(html,(root/'index.html').read_text())
            restore(root)
            self.assertIn('src="/assets/main.js"',(root/'index.html').read_text())
            (assets/'worker.js').write_text('self.onmessage=()=>42')
            changed=build(root);self.assertNotEqual(mapping['worker.js'],changed['worker.js']);self.assertNotEqual(mapping['main.js'],changed['main.js'])
            self.assertNotEqual(html,(root/'index.html').read_text())
