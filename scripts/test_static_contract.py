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
        for asset in page.assets:self.assertTrue((ROOT/'dist'/asset).is_file(),asset)
        code=(ROOT/'dist/app.js').read_text()
        for selector in re.findall(r"\$\('#([A-Za-z][\w-]*)",code):self.assertIn(selector,page.ids)
        self.assertNotIn('seoul_snapshot.json',code)
        self.assertNotIn('min_price_manwon',code)
if __name__=='__main__':unittest.main()
