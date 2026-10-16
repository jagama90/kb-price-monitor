#!/usr/bin/env python3
"""Verify server-side tracker assets are available in the versioned Pages page."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class TestTrackingPagesBundle(unittest.TestCase):
    def test_versioned_script_and_styles_included(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'dist'
            site=Path(temporary)/'site'
            source.mkdir()
            (source/'market.html').write_text(
                '<!doctype html><html><head></head><body><main id="probabilityResearch"></main>'
                '<script src="market.js?v=old"></script></body></html>',
                encoding='utf-8')
            (source/'index.html').write_text('<html><body>old</body></html>',encoding='utf-8')
            (source/'probability-tracker.js').write_text('console.log("tracker");',encoding='utf-8')
            (source/'probability-tracker.css').write_text('.probability-track-v222{}',encoding='utf-8')
            (source/'upside-daily-signals.js').write_text('console.log("signals");',encoding='utf-8')
            (source/'upside-daily-signals.css').write_text('.daily-signal-v1{}',encoding='utf-8')
            subprocess.run([
                sys.executable,str(ROOT/'scripts/prepare_pages.py'),
                '--source',str(source),'--output',str(site),
                '--version','abcdef0123456789test'],
                check=True,capture_output=True,text=True)
            html=(site/'market.abcdef0123456789.html').read_text(encoding='utf-8')
            self.assertIn('probability-tracker.js?v=abcdef0123456789',html)
            self.assertIn('probability-tracker.css?v=abcdef0123456789',html)
            self.assertIn('upside-daily-signals.js?v=abcdef0123456789',html)
            self.assertIn('upside-daily-signals.css?v=abcdef0123456789',html)
            self.assertIn('market.js?v=abcdef0123456789',html)
            self.assertTrue((site/'probability-tracker.js').exists())
            self.assertTrue((site/'probability-tracker.css').exists())
            self.assertTrue((site/'upside-daily-signals.js').exists())
            self.assertTrue((site/'upside-daily-signals.css').exists())
            self.assertIn('market.abcdef0123456789.html',(site/'market.html').read_text())
    def test_missing_assets_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'dist'
            site=Path(temporary)/'site'
            source.mkdir()
            (source/'market.html').write_text('<html><head></head><body></body></html>')
            proc=subprocess.run([
                sys.executable,str(ROOT/'scripts/prepare_pages.py'),
                '--source',str(source),'--output',str(site),'--version','test'],
                capture_output=True,text=True)
            self.assertNotEqual(proc.returncode,0)
            self.assertIn('probability tracking assets missing',proc.stderr+proc.stdout)

if __name__=='__main__':
    unittest.main()
