"""Behavior checks using independent expectations and deliberately invalid edits."""
import contextlib
import io
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_test_fixture import build
from validate_demo import validate


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'test.sqlite'
        with contextlib.redirect_stdout(io.StringIO()):build(self.path)
        self.db=sqlite3.connect(self.path)
        self.db.execute('PRAGMA foreign_keys=ON')

    def tearDown(self):
        self.db.close();self.temp.cleanup()

    def test_orphan_patient_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO Encounter(EncounterID,PatientID,EncounterType,StartDate,EndDate) VALUES(99,999,'outpatient','2026-01-01','2026-01-01')")

    def test_blank_dosage_rejected(self):
        for value in ['', '  ', None]:
            with self.assertRaises(sqlite3.IntegrityError):
                self.db.execute('INSERT INTO MedicationOrder(MedicationOrderID,PatientTreatmentID,MedicationID,Dosage,Frequency) VALUES(99,1,1,?,?)',(value,'Demo'))

    def test_responsible_physician_required(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('UPDATE PatientTreatment SET ResponsiblePhysicianID=NULL WHERE PatientTreatmentID=1')

    def test_date_order_and_invalid_calendar_date_rejected(self):
        for start,end in [('2026-01-04','2026-01-02'),('2026-02-30','2026-03-02')]:
            with self.assertRaises(sqlite3.IntegrityError):
                self.db.execute("INSERT INTO Encounter(EncounterID,PatientID,EncounterType,StartDate,EndDate) VALUES(99,1,'outpatient',?,?)",(start,end))

    def test_outside_treatment_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE PatientTreatment SET EndDate='2026-02-01' WHERE PatientTreatmentID=1")

    def test_parent_date_change_cannot_break_treatment(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE Encounter SET EndDate='2026-01-02' WHERE EncounterID=1")

    def test_score_range_and_integer_type(self):
        for score in [0,11,7.5]:
            with self.assertRaises(sqlite3.IntegrityError):
                self.db.execute('UPDATE Hospitalization SET FallsRisk=? WHERE EncounterID=1',(score,))

    def test_outpatient_cannot_be_hospitalization(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('INSERT INTO Hospitalization(EncounterID) VALUES(6)')

    def test_readmission_boundaries_and_followup(self):
        sql=(ROOT/'sql/queries/05_readmissions.sql').read_text()
        rows=self.db.execute(sql,{'as_of':'2026-08-15'}).fetchall()
        results={r[0]:r[-1] for r in rows}
        self.assertEqual(results[1],1)   # 20 days
        self.assertEqual(results[2],1)   # exactly 30 days
        self.assertEqual(results[4],0)   # 31 days
        self.assertEqual(results[11],1)  # same-day return
        self.assertEqual(results[7],0)   # outpatient follow-up is not readmission
        self.assertNotIn(9,results)      # still hospitalized
        self.assertNotIn(15,results)     # only 10 days of observation

    def test_multiple_treatments_do_not_duplicate_stays(self):
        row=self.db.execute((ROOT/'sql/queries/02_average_stay.sql').read_text(),{'as_of':'2026-08-15'}).fetchone()
        self.assertEqual(row[0],12)
        self.assertAlmostEqual(row[1],44/12,places=3)

    def test_all_validation_checks_pass(self):
        result=validate(self.path)
        self.assertEqual(result.pop('integrity_check'),'ok')
        self.assertTrue(all(v==0 for v in result.values()))

    def test_validator_detects_cross_table_problem(self):
        self.db.execute('DROP TRIGGER PatientBirthUpdate')  # Corrupt only this disposable fixture.
        self.db.execute("UPDATE Patient SET DateOfBirth='2026-02-01' WHERE PatientID=1")
        self.db.commit()
        self.assertGreater(validate(self.path)['encounter_before_birth'],0)

    def test_unknown_prescriber_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('UPDATE MedicationOrder SET PrescribingPhysicianID=999 WHERE MedicationOrderID=1')

    def test_order_date_must_fit_encounter(self):
        for when in ['2025-12-31','2026-01-05']:
            with self.assertRaises(sqlite3.IntegrityError):
                self.db.execute('UPDATE MedicationOrder SET OrderDate=? WHERE MedicationOrderID=1',(when,))

    def test_order_protects_parent_date_edit(self):
        self.db.execute("UPDATE PatientTreatment SET EndDate='2026-01-03' WHERE PatientTreatmentID=1")
        self.db.execute("UPDATE MedicationOrder SET OrderDate='2026-01-04' WHERE MedicationOrderID=1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE Encounter SET EndDate='2026-01-03' WHERE EncounterID=1")

    def test_care_team_view_includes_lead_and_additional_roles(self):
        rows=self.db.execute('SELECT PhysicianID,Role,Responsible FROM TreatmentCareTeam WHERE PatientTreatmentID=1 ORDER BY Responsible DESC').fetchall()
        self.assertEqual(rows,[(1,'Treating physician',1),(3,'Consultant',0)])


if __name__=='__main__':unittest.main()
