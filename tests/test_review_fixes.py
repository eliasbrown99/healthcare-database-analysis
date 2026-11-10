"""Regression tests from independent review, including legal lifecycle transitions."""
import sqlite3
import unittest
import test_database
from pathlib import Path
from validate_demo import validate
from database import connect

ROOT=Path(__file__).resolve().parents[1]


class ReviewTests(unittest.TestCase):
    setUp=test_database.DatabaseTests.setUp
    tearDown=test_database.DatabaseTests.tearDown

    def query(self,number,as_of='2026-08-15',patient_id=1):
        path=next((ROOT/'sql/queries').glob(f'{number:02}_*.sql'))
        return self.db.execute(path.read_text(),{'as_of':as_of,'patient_id':patient_id}).fetchall()

    def corrupt(self,sql):
        # Exercise the independent validator even after SQL starts enforcing the rule.
        # This is deliberately restricted to a disposable test database.
        self.db.commit()
        self.db.execute('PRAGMA foreign_keys=OFF')
        self.db.execute('PRAGMA ignore_check_constraints=ON')
        for (name,) in self.db.execute("SELECT name FROM sqlite_schema WHERE type='trigger'").fetchall():
            self.db.execute(f'DROP TRIGGER "{name}"')
        self.db.executescript(sql)
        self.db.commit()

    def test_connection_helper_enables_foreign_keys(self):
        with connect(self.path) as c:
            self.assertEqual(c.execute('PRAGMA foreign_keys').fetchone()[0],1)
        with self.assertRaises(sqlite3.OperationalError):
            connect(self.path.parent/'missing.sqlite')

    def test_missing_subtype_rejected_at_commit(self):
        self.db.execute('DELETE FROM Hospitalization WHERE EncounterID=5')
        with self.assertRaises(sqlite3.IntegrityError):self.db.commit()
        self.db.rollback()
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM Hospitalization WHERE EncounterID=5').fetchone()[0],1)

    def test_new_inpatient_without_subtype_rejected_at_commit(self):
        self.db.execute("INSERT INTO Encounter(EncounterID,PatientID,EncounterType,StartDate) VALUES(99,8,'inpatient','2027-01-01')")
        with self.assertRaises(sqlite3.IntegrityError):self.db.commit()
        self.db.rollback()

    def test_type_correction_can_finish_in_one_transaction(self):
        self.db.execute('DELETE FROM Hospitalization WHERE EncounterID=5')
        self.db.execute("UPDATE Encounter SET EncounterType='outpatient',AdmissionType=NULL,DischargeDisposition=NULL WHERE EncounterID=5")
        self.db.commit()
        self.assertEqual(validate(self.path)['inpatient_without_hospitalization'],0)
        self.db.execute("UPDATE Encounter SET EncounterType='inpatient' WHERE EncounterID=5")
        self.db.execute('INSERT INTO Hospitalization(EncounterID) VALUES(5)')
        self.db.commit()
        self.assertEqual(validate(self.path)['hospitalization_with_wrong_type'],0)

    def test_complete_episode_deletion_is_possible(self):
        self.db.execute("INSERT INTO Encounter(EncounterID,PatientID,EncounterType,StartDate) VALUES(99,8,'inpatient','2027-01-01')")
        self.db.execute('INSERT INTO Hospitalization(EncounterID) VALUES(99)');self.db.commit()
        self.db.execute('DELETE FROM Hospitalization WHERE EncounterID=99')
        self.db.execute('DELETE FROM Encounter WHERE EncounterID=99');self.db.commit()
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM Encounter WHERE EncounterID=99').fetchone()[0],0)

    def test_subtype_missing_parent_blocked_even_without_foreign_keys(self):
        self.db.execute('PRAGMA foreign_keys=OFF')
        with self.assertRaisesRegex(sqlite3.IntegrityError,'requires an inpatient'):
            self.db.execute('INSERT INTO Hospitalization(EncounterID) VALUES(999)')
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('UPDATE Hospitalization SET EncounterID=999 WHERE EncounterID=5')

    def test_infection_insert_update_and_parent_edit_protected(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError,'Infection detection'):
            self.db.execute("INSERT INTO HospitalInfection VALUES(99,5,1,'2026-02-09',1,NULL,NULL,NULL)")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'Infection detection'):
            self.db.execute("UPDATE HospitalInfection SET DetectedDate='2025-12-31' WHERE HospitalInfectionID=2")
        self.db.execute("UPDATE PatientTreatment SET StartDate='2026-01-03' WHERE PatientTreatmentID=1")
        self.db.execute("UPDATE PatientTreatment SET StartDate='2026-01-03' WHERE PatientTreatmentID=16")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'infection detection'):
            self.db.execute("UPDATE Encounter SET StartDate='2026-01-03' WHERE EncounterID=1")

    def test_infection_resolution_can_follow_discharge(self):
        self.db.execute("UPDATE HospitalInfection SET ResolvedDate='2026-01-10' WHERE HospitalInfectionID=2")
        self.db.commit()
        self.assertEqual(validate(self.path)['infection_detected_outside_stay'],0)

    def test_overlap_insert_and_reassignment_blocked(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError,'Overlapping'):
            self.db.execute("INSERT INTO Encounter(EncounterID,PatientID,EncounterType,StartDate,EndDate) VALUES(99,1,'inpatient','2026-01-02','2026-01-06')")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'Overlapping'):
            self.db.execute('UPDATE Encounter SET PatientID=1 WHERE EncounterID=4')

    def test_patient_correction_keeps_one_owner_and_records_history(self):
        self.db.execute('UPDATE Encounter SET PatientID=8 WHERE EncounterID=5');self.db.commit()
        self.assertEqual(self.db.execute('SELECT EncounterID,PreviousPatientID,NewPatientID FROM EncounterPatientChange').fetchall(),[(5,2,8)])
        self.assertEqual(self.db.execute('SELECT e.PatientID FROM PatientTreatment t JOIN Encounter e USING(EncounterID) WHERE t.PatientTreatmentID=5').fetchone()[0],8)
        self.assertTrue(all(v==0 for k,v in validate(self.path).items() if k!='integrity_check'))

    def test_birth_date_and_encounter_edits_rejected(self):
        for sql in ["UPDATE Patient SET DateOfBirth='2026-02-01' WHERE PatientID=1",
                    "INSERT INTO Encounter(EncounterID,PatientID,EncounterType,StartDate) VALUES(99,1,'outpatient','1979-12-31')"]:
            with self.subTest(sql=sql),self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)
        self.db.execute("INSERT INTO Patient(PatientID,FirstName,LastName,DateOfBirth) VALUES(99,'New','Patient','2027-01-01')")
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('UPDATE Encounter SET PatientID=99 WHERE EncounterID=5')

    def test_duplicate_responsible_and_additional_roles_rejected(self):
        for sql in ['INSERT INTO PhysicianTreatment VALUES(1,1,\'Consultant\')',
                    'UPDATE PhysicianTreatment SET PhysicianID=1 WHERE PatientTreatmentID=1',
                    'UPDATE PatientTreatment SET ResponsiblePhysicianID=3 WHERE PatientTreatmentID=1']:
            with self.subTest(sql=sql),self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)

    def test_role_must_be_explicit(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO PatientTreatment(PatientTreatmentID,EncounterID,TreatmentID,ResponsiblePhysicianID,StartDate,EndDate) VALUES(99,1,1,1,'2026-01-01','2026-01-02')")

    def test_outpatient_has_no_inpatient_admission_fields(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE Encounter SET AdmissionType='planned' WHERE EncounterID=6")

    def test_treatment_move_protects_dated_orders(self):
        self.db.execute("UPDATE PatientTreatment SET EndDate='2026-01-03' WHERE PatientTreatmentID=1")
        self.db.execute("UPDATE MedicationOrder SET OrderDate='2026-01-04' WHERE MedicationOrderID=1")
        self.db.execute("INSERT INTO Encounter(EncounterID,PatientID,EncounterType,StartDate,EndDate) VALUES(99,1,'outpatient','2026-01-01','2026-01-03')")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'Treatment move'):
            self.db.execute('UPDATE PatientTreatment SET EncounterID=99 WHERE PatientTreatmentID=1')

    def test_infection_distribution_counts_episodes_with_cutoff(self):
        self.assertEqual(self.query(3),[('Demo infection category A',2,66.67),('Demo infection category B',1,33.33)])
        self.assertEqual(self.query(3,'2026-01-02'),[('Demo infection category A',1,100.0)])
        self.assertEqual(self.query(3,'2025-12-31'),[])

    def test_high_risk_report_uses_completed_snapshots(self):
        self.assertEqual([r[0] for r in self.query(6)],[1,2,3,4,5,7,10,11,12,13,14,15])
        self.assertEqual(self.query(6,'2026-01-03'),[])
        self.db.execute('UPDATE Hospitalization SET FallsRisk=6 WHERE EncounterID=1')
        self.assertNotIn(1,[r[0] for r in self.query(6)])

    def test_return_worklist_labels_planned_and_respects_window(self):
        self.db.execute("UPDATE Encounter SET AdmissionType='planned' WHERE EncounterID=2")
        rows=self.query(9)
        self.assertEqual([(r[3],r[7]) for r in rows],[(1,20),(2,30),(11,0)])
        self.assertEqual(rows[0][-1],'planned')
        self.assertEqual(self.query(9,'2026-02-02'),[])

    def test_infection_resolution_cutoff_masks_future_date(self):
        rows=self.query(10,'2026-01-02')
        self.assertEqual(len(rows),1)
        self.assertIsNone(rows[0][7])
        self.assertEqual(rows[0][-1],'Resolution not documented by reporting date')
        rows=self.query(10,'2026-01-03')
        self.assertEqual([r[-1] for r in rows],['Resolution not documented by reporting date','Resolution documented'])
        self.assertEqual(rows[1][7],'2026-01-03')

    def test_medication_reports_exclude_undated_and_future_orders(self):
        self.assertEqual(self.query(1),[])
        self.assertTrue(all(r[1]==0 for r in self.query(4)))
        self.assertEqual(self.query(8),[])
        self.db.execute("UPDATE MedicationOrder SET OrderDate='2026-01-02',PrescribingPhysicianID=1 WHERE MedicationOrderID=1")
        self.db.execute("UPDATE MedicationOrder SET OrderDate='2026-01-03',PrescribingPhysicianID=2 WHERE MedicationOrderID=16")
        self.assertEqual(len(self.query(1,'2026-01-02')),2)  # Two catalog effects for one medication.
        self.assertEqual(dict(self.query(4,'2026-01-02')),{'Demo medication A':1,'Demo medication B':0})
        self.assertEqual(sum(r[5] for r in self.query(8,'2026-01-02')),1)
        self.assertEqual(sum(r[5] for r in self.query(8,'2026-01-03')),2)
        self.db.execute('UPDATE MedicationOrder SET PrescribingPhysicianID=NULL WHERE MedicationOrderID=1')
        self.assertEqual(self.query(8,'2026-01-02'),[])

    def test_timeline_hides_future_orders_and_completion_fields(self):
        self.db.execute("UPDATE MedicationOrder SET OrderDate='2026-01-04' WHERE MedicationOrderID=1")
        rows=self.query(7,'2026-01-02')
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r[5] is None and r[7] is None and r[11] is None for r in rows))


    def test_export_context_reports_unknown_date_and_prescriber_exclusions(self):
        import contextlib,io,json,shutil
        from unittest.mock import patch
        import run_queries
        root=self.path.parent/'export'
        (root/'data').mkdir(parents=True)
        shutil.copytree(ROOT/'sql',root/'sql')
        self.db.execute("UPDATE MedicationOrder SET OrderDate='2026-01-02' WHERE MedicationOrderID=1")
        self.db.commit()
        shutil.copy2(self.path,root/'data/healthcare_demo.sqlite')
        with patch.object(run_queries,'ROOT',root),contextlib.redirect_stdout(io.StringIO()):
            run_queries.run('2026-01-02',1)
        context=json.loads((root/'results/report_context.json').read_text())
        self.assertEqual(context['undated_orders_excluded'],15)
        self.assertEqual(context['dated_orders_without_prescriber_excluded_from_query_08'],1)

    def test_export_rejects_invalid_reporting_date(self):
        import run_queries
        with self.assertRaises(ValueError):run_queries.run('2026-02-30')


class ValidatorFailureTests(unittest.TestCase):
    setUp=test_database.DatabaseTests.setUp
    tearDown=test_database.DatabaseTests.tearDown
    corrupt=ReviewTests.corrupt

    def test_each_business_validator_detects_its_corruption(self):
        cases={
          'empty_patient_table':'DELETE FROM Patient;',
          'empty_treatment_table':'DELETE FROM PatientTreatment;',
          'inpatient_without_hospitalization':'DELETE FROM Hospitalization WHERE EncounterID=5;',
          'hospitalization_with_wrong_type':"UPDATE Encounter SET EncounterType='outpatient' WHERE EncounterID=5;",
          'outpatient_with_admission_fields':"UPDATE Encounter SET AdmissionType='planned' WHERE EncounterID=6;",
          'encounter_before_birth':"UPDATE Patient SET DateOfBirth='2026-02-01' WHERE PatientID=1;",
          'overlapping_inpatient_stays':'UPDATE Encounter SET PatientID=1 WHERE EncounterID=4;',
          'treatment_outside_encounter':"UPDATE PatientTreatment SET EndDate='2026-02-01' WHERE PatientTreatmentID=1;",
          'infection_detected_outside_stay':"UPDATE HospitalInfection SET DetectedDate='2025-12-31' WHERE HospitalInfectionID=2;",
          'medication_order_outside_encounter':"UPDATE MedicationOrder SET OrderDate='2027-01-01' WHERE MedicationOrderID=1;",
          'responsible_physician_repeated_as_additional':"INSERT INTO PhysicianTreatment VALUES(1,1,'Duplicate lead');",
          'foreign_key_violations':'UPDATE Encounter SET PatientID=999 WHERE EncounterID=5;'
        }
        # Isolate every corruption in a fresh fixture; no earlier fault can mask a later one.
        for key,sql in cases.items():
            with self.subTest(check=key):
                self.corrupt(sql)
                self.assertGreater(validate(self.path)[key],0)
                self.tearDown();self.setUp()
