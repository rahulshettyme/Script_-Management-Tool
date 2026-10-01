"""
Data Generate - internal regression suite (NOT deployed: this folder is not copied by
sync_links.py / publish_release.py).

Run from the project root:
    python "Internal Tests/run_regression.py"
Options:
    --allow-script NAME.py   standalone script the USER explicitly approved changing (repeatable)
    --update-baseline        after adding new checks, record the new total as the baseline
    --skip-smoke             skip the offline runner_bridge smoke tests

Checks (no real API calls are made anywhere):
  1. Syntax       - node --check on JS, py_compile on Python (incl. every Converted Script)
  2. Legacy guard - standalone scripts in Converted Scripts/ unchanged vs git HEAD
                    (strict rule: scripts are never hand-edited unless the user asks)
  3. Copies       - master_components/ step copies byte-identical to their standalone originals
  4. Registry     - System/scripts_registry.json parses, unique filenames, files exist
  5. Python tests - Manager/test_qa_data_setup_master.py (master orchestration) + Internal Tests/python/test_*.py
  6. JS tests     - Internal Tests/js/*.test.js (master flow UI + backend route contract)
  7. Smoke        - a legacy script and the master script through the real runner_bridge.py
                    against a closed local port (proves the execution path is unchanged)
"""
import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'Converted Scripts')
TESTS = os.path.join(ROOT, 'Internal Tests')
BASELINE_FILE = os.path.join(TESTS, 'baseline.json')

MASTER_SCRIPT = 'QA_Data_Setup_Master.py'
# Converted Scripts that are tool/test artefacts, not user scripts
NON_SCRIPT_FILES = {'thread_utils.py', 'geofence_utils.py', 'DraftTest.py', 'TestScript.py', 'verify_fix.py'}

results = []   # (group, name, ok, detail)


def record(group, name, ok, detail=''):
    results.append((group, name, ok, detail))
    mark = 'PASS' if ok else 'FAIL'
    print(f"  [{mark}] {group}: {name}{(' - ' + detail) if detail and not ok else ''}", flush=True)


def run(cmd, cwd=ROOT, timeout=180, env=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                       timeout=timeout, env=env)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------- 1. syntax
def check_syntax():
    print('\n1. Syntax', flush=True)
    js = ['script.js', 'script_management_v2.js', 'script_dashboard.js', 'backend/api.js', 'System/server.js']
    js += sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, 'components', '*.js')))
    for rel in js:
        if os.path.exists(os.path.join(ROOT, rel)):
            code, out = run(['node', '--check', rel])
            record('syntax', rel, code == 0, out.strip()[-300:])
    py = ['Manager/runner_bridge.py', 'Manager/script_generator.py', 'Manager/script_converter.py']
    py += [os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, 'components', '*.py'))]
    py += [os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(SCRIPTS, '*.py')) if not os.path.basename(p).startswith('TEST_')]
    py += [os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(SCRIPTS, 'master_components', '*.py'))]
    bad = []
    for rel in sorted(set(py)):
        if not os.path.exists(os.path.join(ROOT, rel)):
            continue
        code, out = run([sys.executable, '-c', 'import py_compile,sys; py_compile.compile(sys.argv[1], doraise=True)', rel])
        if code != 0:
            bad.append(f"{rel}: {out.strip().splitlines()[-1] if out.strip() else 'error'}")
    record('syntax', f'{len(set(py))} Python files compile', not bad, '; '.join(bad))


# ---------------------------------------------------------------- 2. legacy guard
def check_legacy_scripts(allowed):
    print('\n2. Legacy script guard (standalone scripts unchanged vs git HEAD)', flush=True)
    code, out = run(['git', 'diff', '--name-only', 'HEAD', '--', 'Converted Scripts'])
    if code != 0:
        record('legacy', 'git diff available', False, out.strip()[-200:])
        return
    changed = []
    for line in out.splitlines():
        name = line.strip()
        base = os.path.basename(name)
        if not name.endswith('.py') or '/master_components/' in name or base.startswith('TEST_'):
            continue
        if base == MASTER_SCRIPT or base in NON_SCRIPT_FILES:
            continue
        changed.append(base)
    unapproved = [c for c in changed if c not in allowed]
    approved = [c for c in changed if c in allowed]
    detail = ('changed without approval: ' + ', '.join(unapproved)) if unapproved else ''
    record('legacy', 'no unapproved edits to standalone scripts', not unapproved, detail)
    for a in approved:
        print(f"         (approved change: {a})")
    # TEST_ leftovers would be synced/committed (they are NOT git-ignored)
    leftovers = [os.path.basename(p) for p in glob.glob(os.path.join(SCRIPTS, 'TEST_*.py'))]
    record('legacy', 'no leftover TEST_*.py in Converted Scripts', not leftovers, ', '.join(leftovers))


# ---------------------------------------------------------------- 3. master copies
def check_master_copies():
    print('\n3. Master step copies', flush=True)
    comp = os.path.join(SCRIPTS, 'master_components')
    copies = sorted(glob.glob(os.path.join(comp, '*.py')))
    if not copies:
        record('copies', 'master_components present', False, 'no copies found')
        return
    for c in copies:
        name = os.path.basename(c)
        orig = os.path.join(SCRIPTS, name)
        ok = os.path.exists(orig) and sha(orig) == sha(c)
        record('copies', f'{name} identical to standalone', ok,
               'standalone missing' if not os.path.exists(orig) else
               'DIFFERS - re-copy the standalone script (cp) after an approved change')


# ---------------------------------------------------------------- 4. registry
def check_registry():
    print('\n4. Registry', flush=True)
    path = os.path.join(ROOT, 'System', 'scripts_registry.json')
    try:
        with open(path, encoding='utf-8') as f:
            reg = json.load(f)
    except Exception as e:
        record('registry', 'parses as JSON', False, str(e))
        return
    record('registry', 'parses as JSON array', isinstance(reg, list), type(reg).__name__)
    if not isinstance(reg, list):
        return
    missing_keys = [i for i, e in enumerate(reg) if not e.get('name') or not e.get('filename')]
    record('registry', 'every entry has name + filename', not missing_keys, f'entries {missing_keys}')
    names = [e.get('filename') for e in reg]
    dupes = sorted({n for n in names if names.count(n) > 1})
    record('registry', 'filenames unique', not dupes, ', '.join(map(str, dupes)))
    missing = [e['filename'] for e in reg if e.get('filename') and not os.path.exists(os.path.join(SCRIPTS, e['filename']))]
    record('registry', 'every registered file exists in Converted Scripts', not missing, ', '.join(missing))
    master = next((e for e in reg if e.get('filename') == MASTER_SCRIPT), None)
    record('registry', 'master entry present with uiMapping', bool(master and master.get('outputConfig', {}).get('uiMapping')))


# ---------------------------------------------------------------- 5. python tests
def check_python_tests():
    print('\n5. Python tests', flush=True)
    test = os.path.join(ROOT, 'Manager', 'test_qa_data_setup_master.py')
    if not os.path.exists(test):
        record('python', 'test_qa_data_setup_master.py present', False, 'missing')
        return
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    code, out = run([sys.executable, test], env=env)
    m = re.search(r'Ran (\d+) tests?', out)
    ok = code == 0 and re.search(r'^OK', out, re.M) is not None
    fails = '; '.join(re.findall(r'^(?:FAIL|ERROR): (.+)$', out, re.M))[:400]
    record('python', f"master orchestration ({m.group(1) if m else '?'} cases)", ok, fails or out[-300:])

    # Internal python tests (e.g. real step copies with requests patched in-process - no network)
    for test_file in sorted(glob.glob(os.path.join(TESTS, 'python', 'test_*.py'))):
        code, out = run([sys.executable, test_file], env=env)
        m = re.search(r'Ran (\d+) tests?', out)
        ok = code == 0 and re.search(r'^OK', out, re.M) is not None
        fails = '; '.join(re.findall(r'^(?:FAIL|ERROR): (.+)$', out, re.M))[:400]
        record('python', f"{os.path.basename(test_file)} ({m.group(1) if m else '?'} cases)", ok, fails or out[-300:])


# ---------------------------------------------------------------- 6. js tests
def check_js_tests():
    print('\n6. JS tests', flush=True)
    files = sorted(glob.glob(os.path.join(TESTS, 'js', '*.test.js')))
    for f in files:
        try:
            code, out = run(['node', f], timeout=60)
        except subprocess.TimeoutExpired:
            record('js', os.path.basename(f), False, 'TIMEOUT (possible request loop / hang)')
            continue
        record('js', os.path.basename(f), code == 0 and 'passed' in out, out.strip()[-400:])


# ---------------------------------------------------------------- 7. smoke
def _runner(script_rel, rows, env_cfg):
    with tempfile.TemporaryDirectory() as tmp:
        data_file = os.path.join(tmp, 'rows.json')
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(rows, f)
        env = dict(os.environ, PYTHONIOENCODING='utf-8',
                   PYTHONPATH=ROOT + os.pathsep + os.environ.get('PYTHONPATH', ''))
        for k in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy'):
            env.pop(k, None)
        # cwd = temp dir: runner deletes/reads Uploaded_File.xlsx in cwd, keep the project root untouched
        code, out = run([sys.executable, '-u', os.path.join(ROOT, 'Manager', 'runner_bridge.py'),
                         '--script', os.path.join(ROOT, script_rel), '--data-file', data_file,
                         '--token', 'dummy', '--env', json.dumps(env_cfg), '--columns', '[]'],
                        cwd=tmp, timeout=120, env=env)
    parts = out.split('---JSON_START---')
    parsed = None
    if len(parts) > 1:
        try:
            parsed = json.loads(parts[-1].strip())
        except Exception:
            parsed = None
    return code, parsed, out


def check_smoke():
    print('\n7. Offline runner smoke tests (closed port 127.0.0.1:9, no real APIs)', flush=True)
    offline = {'apiBaseUrl': 'http://127.0.0.1:9', 'batchSize': 1, 'Geocoding_api_key': ''}

    # Legacy script: contract = exit 0, JSON envelope, input columns merged into result rows
    row = {'Farmer Name': 'SMOKE F 1', 'Farmer Code': 'SMOKE1', 'Phone Number': '91 9000000001',
           'AssignedTo User ID': '1', 'Address': '', 'Smoke Extra Column': 'kept'}
    code, parsed, out = _runner('Converted Scripts/Add_Farmer.py', [row], offline)
    ok = code == 0 and parsed and parsed.get('status') == 'success' and len(parsed.get('data') or []) == 1
    record('smoke', 'legacy Add_Farmer.py runs through runner_bridge', bool(ok), out[-400:])
    if ok:
        r = parsed['data'][0]
        record('smoke', 'legacy result keeps input columns (runner merge)', r.get('Smoke Extra Column') == 'kept', str(r)[:200])
        record('smoke', 'legacy result reports failure (no API reachable)', str(r.get('Status')).lower() == 'fail', str(r.get('Status')))

    # Master script: SKIP_INPUT_MERGE honoured (no input-only keys leak into output)
    plan = {'Farmer #': 1, 'Farmer Name': 'SMOKE F 1', 'Farmer Code': 'SMOKE1', 'Phone Number': '91 9000000001',
            'AssignedTo User ID': '1', 'Existing Farmer ID': '', 'Asset Names': ['SMOKE A 1']}
    cfg = dict(offline, masterFlow={'steps': {'farmer': True, 'asset': True, 'validate': True}, 'farmerAddress': '',
                                    'projectId': '1', 'asset': {'soilType': 'x', 'irrigationType': 'y', 'address': 'z', 'declaredArea': '1'}})
    code, parsed, out = _runner(f'Converted Scripts/{MASTER_SCRIPT}', [plan], cfg)
    ok = code == 0 and parsed and parsed.get('status') == 'success' and len(parsed.get('data') or []) == 1
    record('smoke', 'master script runs through runner_bridge', bool(ok), out[-400:])
    if ok:
        r = parsed['data'][0]
        record('smoke', 'master output not merged with input (SKIP_INPUT_MERGE)', 'Asset Names' not in r, str(list(r))[:200])
        record('smoke', 'master marks assets Skipped after farmer failure', r.get('Asset Status') == 'Skipped', str(r.get('Asset Status')))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--allow-script', action='append', default=[])
    ap.add_argument('--update-baseline', action='store_true')
    ap.add_argument('--skip-smoke', action='store_true')
    args = ap.parse_args()

    print('=' * 70)
    print('Data Generate regression suite')
    print('=' * 70)
    check_syntax()
    check_legacy_scripts(set(args.allow_script))
    check_master_copies()
    check_registry()
    check_python_tests()
    check_js_tests()
    if not args.skip_smoke:
        check_smoke()

    total = len(results)
    passed = sum(1 for r in results if r[2])
    baseline = 0
    if os.path.exists(BASELINE_FILE):
        with open(BASELINE_FILE, encoding='utf-8') as f:
            baseline = json.load(f).get('checks', 0)
    if args.update_baseline:
        with open(BASELINE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'checks': total}, f, indent=2)
    existing = min(baseline, total)
    new = max(total - baseline, 0)

    print('\n' + '=' * 70)
    print(f'RESULT: {"PASS" if passed == total else "FAIL"}  {passed}/{total} checks passing '
          f'({existing} existing, {new} new{"; baseline updated" if args.update_baseline else ""})')
    for g, n, ok, d in results:
        if not ok:
            print(f'  FAILED  {g}: {n}\n          {d[:500]}')
    print('=' * 70)
    sys.exit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
