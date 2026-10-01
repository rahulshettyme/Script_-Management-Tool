"""
Internal regression test (not deployed). Run from project root:
    python "Internal Tests/python/test_dos_format.py"

Runs the REAL (unchanged) Crop & DOS step copy with requests patched in-process (no network) and checks
the exact sowingDate it would PUT for:
  - the master form's <input type="date"> value (YYYY-MM-DD, passed through QA_Data_Setup_Master)
  - an Excel date cell as the standalone script receives it (serial number), for parity
Also checks the master maps the form DOS into the step's 'Date of Sowing (YYYY-MM-DD)' column unchanged.
"""
import importlib.util
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, 'Converted Scripts')
sys.path[:0] = [ROOT, SCRIPTS]

import requests  # noqa: E402  (the copy does `import requests` inside run(); same module object)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeResp:
    def __init__(self, payload, status=200):
        self._p, self.status_code, self.ok, self.text = payload, status, 200 <= status < 300, str(payload)

    def json(self):
        return self._p


class DosFormatTests(unittest.TestCase):
    def setUp(self):
        self.puts = []
        self._orig = (requests.get, requests.post, requests.put)
        crops = [{'id': 1005, 'name': 'Potato', 'children': [{'id': 3424001, 'name': 'RS PR Potato'}]}]
        requests.get = lambda url, **kw: FakeResp({'id': 777, 'usableArea': {'count': 1}, 'declaredArea': {'count': 1}})
        requests.post = lambda url, **kw: FakeResp(crops)
        requests.put = lambda url, **kw: (self.puts.append(kw.get('json')), FakeResp({}))[1]
        self.copy = load(os.path.join(SCRIPTS, 'master_components', 'Add_or_update_Crop_and_DOS_to_CA.py'), 'dos_copy_under_test')

    def tearDown(self):
        requests.get, requests.post, requests.put = self._orig

    def run_copy(self, dos, variety=''):
        row = {'CA Name': 'A', 'CA ID': 777, 'Variety Name': variety, 'Date of Sowing (YYYY-MM-DD)': dos}
        out = self.copy.run([row], 'tok', {'apiBaseUrl': 'http://fake', 'batchSize': 1})
        return out[0], (self.puts[-1] if self.puts else None)

    def test_form_date_value_is_sent_in_api_format(self):
        res, body = self.run_copy('2026-09-01')        # what <input type="date"> produces
        self.assertEqual(res['Status'], 'Pass')
        self.assertEqual(body['sowingDate'], '2026-09-01T00:00:00.000+0000')

    def test_matches_standalone_excel_serial_date(self):
        # Excel cell 01-Sep-2026 arrives in the standalone script as serial 46266 (SheetJS sheet_to_json)
        _, excel_body = self.run_copy(46266)
        _, form_body = self.run_copy('2026-09-01')
        self.assertEqual(excel_body['sowingDate'], form_body['sowingDate'])

    def test_empty_dos_sends_no_sowing_date(self):
        res, body = self.run_copy('', variety='RS PR Potato')   # variety only
        self.assertEqual(res['Status'], 'Pass')
        self.assertNotIn('sowingDate', body)
        self.assertEqual(body['varietyId'], 3424001)

    def test_master_passes_form_dos_unchanged(self):
        master = load(os.path.join(SCRIPTS, 'QA_Data_Setup_Master.py'), 'master_dos_under_test')
        seen = []
        fake = types.ModuleType('fake_edit')
        fake.run = lambda data, token, env: (seen.extend(dict(r) for r in data), [dict(r, Status='Pass') for r in data])[1]
        ok = lambda fields: types.SimpleNamespace(run=lambda d, t, e: [dict(r, Status='Pass', **fields) for r in d])
        master._loaded_modules.update({'asset': ok({'Asset ID': 5001}), 'validate': ok({'CA ID': 105001}), 'editCa': fake})
        plan = {'Farmer #': 1, 'Existing Farmer ID': '1001', 'Asset Names': ['A1']}
        env = {'masterFlow': {'steps': {'farmer': False, 'asset': True, 'validate': True, 'editCa': True},
                              'projectId': '1', 'asset': {}, 'editCa': {'varietyName': '', 'dos': '2026-09-01'}}}
        out = master.run([plan], 'tok', env)
        self.assertEqual(seen[0]['Date of Sowing (YYYY-MM-DD)'], '2026-09-01')
        self.assertEqual(out[0]['DOS'], '2026-09-01')


if __name__ == '__main__':
    unittest.main(verbosity=2)
