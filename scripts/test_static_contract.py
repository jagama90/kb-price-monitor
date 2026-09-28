"""Check the buildless UI contract without opening a browser."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.assets=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='script' and 'src' in a:self.assets.append(a['src'])
        if tag=='link' and a.get('rel')=='stylesheet':self.assets.append(a['href'])
class StaticContract(unittest.TestCase):
    def test_assets_and_selectors(self):
        page=Page();page.feed((ROOT/'dist/index.html').read_text())
        self.assertEqual(len(page.ids),len(set(page.ids)))
        for asset in page.assets:
            clean=asset.split('?',1)[0]
            self.assertTrue((ROOT/'dist'/clean).is_file(),asset)
        # Validate each dashboard script against the HTML page that actually owns it.
        # market.js belongs to market.html; index.html may host a separate lightweight shell.
        pages=['index.html','market.html']
        combined_code=[]
        for name in pages:
            path=ROOT/'dist'/name
            if not path.exists(): continue
            p=Page();p.feed(path.read_text())
            self.assertEqual(len(p.ids),len(set(p.ids)),name)
            scripts=[a.split('?',1)[0] for a in p.assets if a.split('?',1)[0].endswith('.js')]
            code='\n'.join((ROOT/'dist'/s).read_text() for s in scripts)
            combined_code.append(code)
            generated=set(re.findall(r'''id=["']([A-Za-z][\w-]*)''',code))
            for selector in re.findall(r"(?:querySelector\(|\$\()['\"]#([A-Za-z][\w-]*)",code):
                self.assertTrue(selector in p.ids or selector in generated,f'{name}: {selector}')
        code='\n'.join(combined_code)
        self.assertNotIn('seoul_snapshot.json',code)
        self.assertNotIn('min_price_manwon',code)
if __name__=='__main__':unittest.main()
