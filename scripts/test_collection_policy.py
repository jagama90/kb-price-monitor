"""Offline regression tests: failed/sample runs never replace published prices."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import collect_types

class CollectionPolicy(unittest.TestCase):
    def run_collection(self, response=None, failure=None, extra=()):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'data').mkdir();(root/'dist').mkdir()
            complex_row={'complex_id':1,'name':'test','district':'송파구','dong':'오금동','households':438}
            (root/'data/seoul_snapshot.json').write_text(json.dumps({'items':[complex_row],'complex_count':1,'collected_at':'2026-09-04T00:00:00Z'}))
            (root/'dist/seoul_types.json').write_text('previous validated publication')
            raw=[{'단지기본일련번호':1,'면적일련번호':2,'공급면적':'102','공급면적평':'30.85','시세제공여부':'1','매매일반거래가':162000}]
            with patch.object(collect_types,'ROOT',root), patch.object(collect_types,'api_get',return_value=raw if response is None else response,side_effect=failure), patch('sys.argv',['collect_types.py','--publish-data',*extra]),contextlib.redirect_stdout(io.StringIO()):
                status=collect_types.main()
            return status,(root/'dist/seoul_types.json').read_text()
    def test_failed_run_preserves_publication(self):
        status,result=self.run_collection(failure=RuntimeError('network unavailable'))
        self.assertEqual(status,2);self.assertEqual(result,'previous validated publication')
    def test_sample_run_preserves_publication(self):
        status,result=self.run_collection(extra=('--ids','1'))
        self.assertEqual(status,0);self.assertEqual(result,'previous validated publication')
    def test_complete_run_publishes_exact_type(self):
        status,result=self.run_collection()
        data=json.loads(result)
        self.assertEqual(status,0)
        self.assertEqual(data['items'][0]['general_price_manwon'],162000)
        self.assertEqual(data['items'][0]['supply_pyeong'],30.85)
        self.assertEqual(data['type_count'],1)
    def test_invalid_identity_preserves_publication(self):
        status,result=self.run_collection(response=[{'단지기본일련번호':999,'면적일련번호':2}])
        self.assertEqual(status,2);self.assertEqual(result,'previous validated publication')

if __name__=='__main__':unittest.main()
