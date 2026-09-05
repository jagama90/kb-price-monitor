import unittest
from price_changes import compare
class Changes(unittest.TestCase):
    def snap(self,price,area=1,status='kb_general'):
        return {'schema_version':2,'collected_at':'test','items':[{'complex_id':1,'area_id':area,'general_price_manwon':price,'price_status':status}]}
    def test_crossing(self):
        self.assertEqual(len(compare(self.snap(150001),self.snap(150000))['newly_below']),1)
        self.assertEqual(len(compare(self.snap(150000),self.snap(149000))['newly_below']),0)
    def test_no_legacy_comparison(self):
        r=compare({'schema_version':1,'items':[]},self.snap(100000))
        self.assertFalse(r['baseline_available']);self.assertEqual(r['newly_below'],[])
    def test_new_or_missing(self):
        self.assertEqual(len(compare(self.snap(None),self.snap(100000))['newly_available_below']),1)
        self.assertEqual(len(compare(self.snap(200000,area=2),self.snap(100000))['newly_below']),0)
        self.assertEqual(len(compare(self.snap(200000),self.snap(None,status='unavailable'))['newly_below']),0)
if __name__=='__main__':unittest.main()
