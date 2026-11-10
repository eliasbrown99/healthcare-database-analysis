"""Validate invariants that span tables and cannot be expressed as simple checks."""
import json
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def validate(path=None):
    con=sqlite3.connect(Path(path or ROOT/'data/healthcare_demo.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    checks={
      'empty_patient_table': 'SELECT CASE WHEN COUNT(*)=0 THEN 1 ELSE 0 END FROM Patient',
      'empty_treatment_table': 'SELECT CASE WHEN COUNT(*)=0 THEN 1 ELSE 0 END FROM PatientTreatment',
      'inpatient_without_hospitalization': "SELECT COUNT(*) FROM Encounter e WHERE EncounterType='inpatient' AND NOT EXISTS(SELECT 1 FROM Hospitalization h WHERE h.EncounterID=e.EncounterID)",
      'hospitalization_with_wrong_type': "SELECT COUNT(*) FROM Hospitalization h JOIN Encounter e USING(EncounterID) WHERE e.EncounterType<>'inpatient'",
      'outpatient_with_admission_fields': "SELECT COUNT(*) FROM Encounter WHERE EncounterType='outpatient' AND (AdmissionType IS NOT NULL OR DischargeDisposition IS NOT NULL)",
      'encounter_before_birth': 'SELECT COUNT(*) FROM Encounter e JOIN Patient p USING(PatientID) WHERE e.StartDate<p.DateOfBirth',
      'overlapping_inpatient_stays': '''SELECT COUNT(*) FROM Encounter a JOIN Encounter b
        ON a.PatientID=b.PatientID AND a.EncounterID<b.EncounterID
        WHERE a.EncounterType='inpatient' AND b.EncounterType='inpatient'
        AND a.StartDate<COALESCE(b.EndDate,'9999-12-31') AND b.StartDate<COALESCE(a.EndDate,'9999-12-31')''',
      'treatment_outside_encounter': '''SELECT COUNT(*) FROM PatientTreatment p JOIN Encounter e USING(EncounterID)
        WHERE p.StartDate<e.StartDate OR (e.EndDate IS NOT NULL AND (p.StartDate>e.EndDate OR p.EndDate IS NULL OR p.EndDate>e.EndDate))''',
      'infection_detected_outside_stay': '''SELECT COUNT(*) FROM HospitalInfection h JOIN Encounter e USING(EncounterID)
        WHERE h.DetectedDate<e.StartDate OR (e.EndDate IS NOT NULL AND h.DetectedDate>e.EndDate)''',
      'medication_order_outside_encounter': '''SELECT COUNT(*) FROM MedicationOrder m
        JOIN PatientTreatment p USING(PatientTreatmentID) JOIN Encounter e USING(EncounterID)
        WHERE m.OrderDate<e.StartDate OR (e.EndDate IS NOT NULL AND m.OrderDate>e.EndDate)''',
      'responsible_physician_repeated_as_additional': '''SELECT COUNT(*) FROM PhysicianTreatment x
        JOIN PatientTreatment p USING(PatientTreatmentID) WHERE x.PhysicianID=p.ResponsiblePhysicianID'''
    }
    results={k:con.execute(q).fetchone()[0] for k,q in checks.items()}
    results['foreign_key_violations']=len(con.execute('PRAGMA foreign_key_check').fetchall())
    results['integrity_check']=con.execute('PRAGMA integrity_check').fetchone()[0]
    con.close()
    return results


if __name__=='__main__':
    result=validate();print(json.dumps(result,indent=2))
    if any(v!=0 for k,v in result.items() if k!='integrity_check') or result['integrity_check']!='ok':
        raise SystemExit(1)
