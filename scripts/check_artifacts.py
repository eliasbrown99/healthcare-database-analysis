"""Rebuild in a temporary directory and detect drift in published artifacts.

SQLite files are compared by schema and row values, not page layout. This avoids
false failures when equivalent files are built by different SQLite releases.
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATABASES=['data/healthcare_demo.sqlite','data/source_snapshot.sqlite']
TEXT_FILES=['README.md','docs/DESIGN.md','docs/SCENARIOS.md','docs/rebuild_manifest.json',
            'docs/source_audit_results.json','results/report_context.json']
COMMANDS=[['scripts/audit_source.py'],['scripts/rebuild_synthetic.py'],
          ['scripts/validate_demo.py'],['scripts/run_queries.py','--patient-id','2','--as-of','2023-12-31'],
          ['scripts/document_scenarios.py'],['scripts/diagrams.py','--source-only']]


def logical_database(path):
    con=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        schema=con.execute("SELECT type,name,tbl_name,sql FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
        rows={}
        for (name,) in con.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            quoted='"'+name.replace('"','""')+'"'
            rows[name]=sorted(con.execute(f'SELECT * FROM {quoted}').fetchall(),key=repr)
        return schema,rows
    finally:
        con.close()


def differences(original,rebuilt):
    errors=[]
    paths=set(TEXT_FILES)
    for root in [original,rebuilt]:
        paths.update(str(p.relative_to(root)) for p in (root/'results').glob('*.csv'))
        paths.update(str(p.relative_to(root)) for p in (root/'docs/diagrams').glob('*.dot'))
    for rel in sorted(paths):
        a,b=original/rel,rebuilt/rel
        if not a.is_file() or not b.is_file() or a.read_bytes()!=b.read_bytes():errors.append(rel)
    for rel in DATABASES:
        a,b=original/rel,rebuilt/rel
        if not a.is_file() or not b.is_file() or logical_database(a)!=logical_database(b):errors.append(rel)
    return errors


def check(root=ROOT):
    with tempfile.TemporaryDirectory(prefix='healthcare-rebuild-') as temp:
        rebuilt=Path(temp)
        for directory in ['scripts','sql','data/source']:
            shutil.copytree(root/directory,rebuilt/directory,ignore=shutil.ignore_patterns('__pycache__'))
        (rebuilt/'docs').mkdir(exist_ok=True)
        for rel in ['README.md','docs/DESIGN.md']:
            shutil.copy2(root/rel,rebuilt/rel)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
        for command in COMMANDS:
            result=subprocess.run([sys.executable,'-B',*command],cwd=rebuilt,env=env,text=True,capture_output=True)
            if result.returncode:
                raise RuntimeError(f"Rebuild failed: {' '.join(command)}\n{result.stdout}\n{result.stderr}")
        errors=differences(root,rebuilt)
        if errors:
            raise RuntimeError('Generated artifacts differ: '+', '.join(errors)+'\nRegenerate, inspect, and commit the updated artifacts.')
    print('Artifact check passed: both database schemas/rows, CSVs, generated docs/counts, manifests, and diagram sources match a clean rebuild.')


if __name__=='__main__':
    try:check()
    except (RuntimeError,sqlite3.DatabaseError) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(1)
