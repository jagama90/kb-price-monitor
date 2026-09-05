import unittest
from collect_types import normalize
class Normalization(unittest.TestCase):
    def setUp(self):
        self.c={'complex_id':1,'name':'test','district':'송파구','dong':'오금동','households':438}
        self.raw={'단지기본일련번호':1,'면적일련번호':2,'공급면적':'102.00','공급면적평':'30.85','전용면적':'78.39','전용면적평':'23.71','공급면적평N':'30','주택형타입내용':'B','시세제공여부':'1','50세대미만여부':'0','매매일반거래가':162000,'세대수':19}
    def test_exact_mapping(self):
        r=normalize(self.c,[self.raw],'2026-09-04T00:00:00Z')[0]
        self.assertEqual((r['area_id'],r['supply_pyeong'],r['general_price_manwon']),(2,30.85,162000))
        self.assertEqual(r['type_households'],19)
    def test_no_fallback(self):
        for change in [{'매매일반거래가':0},{'시세제공여부':'0'},{'50세대미만여부':'1'},{'매매일반거래가':None}]:
            r=normalize(self.c,[dict(self.raw,**change)],'test')[0]
            self.assertIsNone(r['general_price_manwon'])
    def test_identity_fail_closed(self):
        with self.assertRaises(ValueError):normalize(self.c,[dict(self.raw,단지기본일련번호=3)],'test')
        with self.assertRaises(ValueError):normalize(self.c,[self.raw,self.raw],'test')
        with self.assertRaises(ValueError):normalize(self.c,[dict(self.raw,공급면적=None)],'test')
    def test_empty_placeholder(self):
        empty={'단지기본일련번호':1,'면적일련번호':None,'공급면적':None,'공급면적평':None,'시세제공여부':'0','매매일반거래가':0}
        self.assertEqual(normalize(self.c,[empty],'test'),[])
        with self.assertRaises(ValueError):normalize(self.c,[dict(empty,단지기본일련번호=3)],'test')
if __name__=='__main__':unittest.main()
