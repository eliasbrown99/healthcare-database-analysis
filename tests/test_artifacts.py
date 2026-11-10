"""Prove the artifact comparison catches stale text and same-count data changes."""
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_artifacts import DATABASES,TEXT_FILES,differences,logical_database


class ArtifactTests(unittest.TestCase):
    def test_drift_detects_stale_text_rows_and_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)
            paths=list(TEXT_FILES)+DATABASES
            paths += [str(p.relative_to(ROOT)) for p in (ROOT/'results').glob('*.csv')]
            paths += [str(p.relative_to(ROOT)) for p in (ROOT/'docs/diagrams').glob('*.dot')]
            for rel in paths:
                (copy/rel).parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/rel,copy/rel)
            self.assertEqual(differences(ROOT,copy),[])
            scenario=copy/'docs/SCENARIOS.md'
            scenario.write_text(scenario.read_text()+'\nStale claim\n')
            self.assertEqual(differences(ROOT,copy),['docs/SCENARIOS.md'])
            shutil.copy2(ROOT/'docs/SCENARIOS.md',scenario)
            db=copy/'data/healthcare_demo.sqlite'
            with sqlite3.connect(db) as c:
                c.execute("UPDATE Patient SET FirstName='Different' WHERE PatientID=1")
            self.assertEqual(differences(ROOT,copy),['data/healthcare_demo.sqlite'])
            shutil.copy2(ROOT/'data/healthcare_demo.sqlite',db)
            with sqlite3.connect(db) as c:c.execute('DROP TRIGGER InfectionDatesInsert')
            self.assertEqual(differences(ROOT,copy),['data/healthcare_demo.sqlite'])

    def test_database_comparison_ignores_physical_page_layout(self):
        with tempfile.TemporaryDirectory() as temp:
            copy=Path(temp)/'repacked.sqlite'
            shutil.copy2(ROOT/'data/healthcare_demo.sqlite',copy)
            with sqlite3.connect(copy) as c:
                c.execute('PRAGMA page_size=8192');c.execute('VACUUM')
            self.assertNotEqual(copy.read_bytes(),(ROOT/'data/healthcare_demo.sqlite').read_bytes())
            self.assertEqual(logical_database(copy),logical_database(ROOT/'data/healthcare_demo.sqlite'))
