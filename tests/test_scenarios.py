"""Acceptance checks against the generated worked cases; rebuild before running."""
import json
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(f'file:{ROOT / "data/healthcare_demo.sqlite"}?mode=ro',uri=True)

    def tearDown(self):self.db.close()

    def test_original_catalog_entries_preserved(self):
        for table,id_col,name_col in [('Treatment','TreatmentID','TreatmentName'),('Medication','MedicationID','MedicationName')]:
            for row in json.loads((ROOT/f'data/source/{table}.json').read_text()):
                current=self.db.execute(f'SELECT {name_col} FROM {table} WHERE {id_col}=?',(row[id_col],)).fetchone()
                self.assertEqual(current[0],row[name_col])

    def test_named_cases_have_expected_readmission_boundaries(self):
        query=(ROOT/'sql/queries/05_readmissions.sql').read_text()
        rows={r[0]:r for r in self.db.execute(query,{'as_of':'2023-12-31'})}
        for encounter,gap,flag in [(1,20,1),(2,30,1),(3,31,0)]:
            self.assertEqual(rows[encounter][-2:],(gap,flag))

    def test_timeline_does_not_multiply_events(self):
        query=(ROOT/'sql/queries/07_patient_care_timeline.sql').read_text()
        rows=self.db.execute(query,{'patient_id':2,'as_of':'2023-12-31'}).fetchall()
        expected=self.db.execute('SELECT COUNT(*) FROM PatientTreatment JOIN Encounter USING(EncounterID) WHERE PatientID=2').fetchone()[0]
        self.assertEqual(len(rows),expected)
        self.assertTrue(any('Cardiac Rehabilitation' in row for row in rows))

    def test_prescriber_report_accounts_for_selected_orders(self):
        query=(ROOT/'sql/queries/08_orders_by_prescriber.sql').read_text()
        total=sum(row[5] for row in self.db.execute(query,{'as_of':'2023-12-31'}))
        self.assertEqual(total,self.db.execute('SELECT COUNT(*) FROM MedicationOrder').fetchone()[0])

    def test_infection_categories_are_separate_from_organisms(self):
        rows=self.db.execute('SELECT TypeName,Organism,ClinicalNote FROM HospitalInfection JOIN InfectionType USING(InfectionTypeID)').fetchall()
        self.assertTrue(rows)
        for category,organism,note in rows:
            self.assertNotEqual(category,organism)
            self.assertTrue(organism and note)
            self.assertNotIn('Synthetic infection category',category)

    def test_every_advertised_outpatient_capability_has_examples(self):
        expected={6:'thyroid',20:'well-child',28:'acne',29:'psychotherapy',26:'skin biopsy'}
        for treatment,label in expected.items():
            with self.subTest(capability=label):
                count=self.db.execute("SELECT COUNT(*) FROM PatientTreatment t JOIN Encounter e USING(EncounterID) WHERE e.EncounterType='outpatient' AND t.TreatmentID=?",(treatment,)).fetchone()[0]
                self.assertGreater(count,0)

    def test_supplemental_pediatric_cases_are_minors_led_by_pediatricians(self):
        rows=self.db.execute("""SELECT p.PatientID,p.DateOfBirth,e.StartDate,ph.Specialty,t.ResponsibleRole
          FROM Patient p JOIN Encounter e USING(PatientID) JOIN PatientTreatment t USING(EncounterID)
          JOIN Physician ph ON ph.PhysicianID=t.ResponsiblePhysicianID WHERE t.TreatmentID=20 ORDER BY p.PatientID""").fetchall()
        self.assertEqual([r[0] for r in rows],[501,502])
        from datetime import date
        for _,dob,visit,specialty,role in rows:
            birth=date.fromisoformat(dob);when=date.fromisoformat(visit)
            age=when.year-birth.year-((when.month,when.day)<(birth.month,birth.day))
            self.assertTrue(0<=age<18)
            self.assertEqual((specialty,role),('Pediatrics','Pediatrician'))

    def test_emergency_contact_components_are_separately_queryable(self):
        self.assertEqual(self.db.execute('SELECT EmergencyContactName,EmergencyContactRelationship,EmergencyContactPhone FROM Patient WHERE PatientID=501').fetchone(),('Leah Morgan','Parent','202-555-0198'))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM Patient WHERE EmergencyContactName IS NULL OR EmergencyContactRelationship IS NULL OR EmergencyContactPhone IS NULL").fetchone()[0],0)

    def test_original_patient_identity_fields_unchanged(self):
        for p in json.loads((ROOT/'data/source/Patient.json').read_text()):
            expected=(p['FirstName'],p['LastName'],p['DateOfBirth'][:10],p['PhoneNumber'],p['Address'],p['Gender'])
            actual=self.db.execute('SELECT FirstName,LastName,DateOfBirth,PhoneNumber,Address,Gender FROM Patient WHERE PatientID=?',(p['PatientID'],)).fetchone()
            self.assertEqual(actual,expected)

    def test_generated_report_acceptance_counts(self):
        returns=self.db.execute((ROOT/'sql/queries/09_readmission_review.sql').read_text(),{'as_of':'2023-12-31'}).fetchall()
        self.assertEqual(len(returns),20)
        self.assertEqual(sum(r[-1]=='planned' for r in returns),4)
        infections=self.db.execute((ROOT/'sql/queries/10_infection_followup.sql').read_text(),{'as_of':'2023-12-31'}).fetchall()
        self.assertEqual(len(infections),24)
        self.assertEqual(sum(r[-1]=='Resolution not documented by reporting date' for r in infections),6)
        self.assertEqual(len(self.db.execute((ROOT/'sql/queries/06_high_falls_risk.sql').read_text(),{'as_of':'2023-12-31'}).fetchall()),75)

    def test_document_generator_rejects_missing_advertised_case(self):
        from document_scenarios import capability_rows
        copy=sqlite3.connect(':memory:')
        try:
            self.db.backup(copy)
            copy.execute('DELETE FROM PatientTreatment WHERE TreatmentID=20')
            with self.assertRaisesRegex(ValueError,'Well-child'):
                capability_rows(copy)
        finally:copy.close()

if __name__=='__main__':unittest.main()
