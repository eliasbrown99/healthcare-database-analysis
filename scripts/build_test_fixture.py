"""Build the revised schema with explicitly new, deterministic synthetic cases."""
import sqlite3
from pathlib import Path
from database import connect

ROOT = Path(__file__).resolve().parents[1]


def build(path=None):
    path = Path(path or ROOT / 'data/boundary_cases.sqlite')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.unlink(missing_ok=True)
    con = connect(path,create=True)
    con.executescript((ROOT / 'sql/schema.sql').read_text())
    con.executemany('INSERT INTO Patient(PatientID,FirstName,LastName,DateOfBirth,Email,EmergencyContactName) VALUES (?,?,?,?,?,?)',
      [(i,f'Demo{i}','Patient','1980-01-01',f'patient{i}@example.invalid',f'Demo contact {i}') for i in range(1,9)])
    con.executemany('INSERT INTO Physician(PhysicianID,FirstName,LastName,Specialty) VALUES (?,?,?,?)',
      [(1,'Demo','ClinicianA','Demo specialty'),(2,'Demo','ClinicianB','Demo specialty'),(3,'Demo','ClinicianC','Demo specialty')])
    cases = [
      (1,1,'inpatient','2026-01-01','2026-01-04'),
      (2,1,'inpatient','2026-01-24','2026-01-27'),
      (3,1,'inpatient','2026-02-26','2026-03-01'),
      (4,2,'inpatient','2026-01-01','2026-01-05'),
      (5,2,'inpatient','2026-02-05','2026-02-08'),
      (6,3,'outpatient','2026-02-01','2026-02-01'),
      (7,3,'inpatient','2026-03-01','2026-03-08'),
      (8,3,'outpatient','2026-03-15','2026-03-15'),
      (9,4,'inpatient','2026-04-01',None),
      (10,5,'inpatient','2026-05-01','2026-05-05'),
      (11,6,'inpatient','2026-06-01','2026-06-05'),
      (12,6,'inpatient','2026-06-05','2026-06-08'),
      (13,7,'inpatient','2026-07-01','2026-07-04'),
      (14,7,'inpatient','2026-08-04','2026-08-07'),
      (15,8,'inpatient','2026-08-01','2026-08-05')]
    con.executemany('INSERT INTO Encounter(EncounterID,PatientID,EncounterType,StartDate,EndDate) VALUES (?,?,?,?,?)',cases)
    con.executemany('INSERT INTO Hospitalization(EncounterID,FallsRisk,ADLScore,FallsOccurred,MedicationErrors,Diet,CarePlanAdherence,ActivityLevel) VALUES (?,?,?,?,?,?,?,?)',
       [(i,7+i%4,3+i%6,int(i%4==0),i%3,'Demo diet',1,'Demo activity') for i,p,k,s,e in cases if k=='inpatient'])
    con.executemany('INSERT INTO Treatment VALUES (?,?,?)',[(1,'Demo treatment A','Fictional procedure'),(2,'Demo treatment B','Fictional supportive care')])
    for i,p,k,s,e in cases:
        con.execute('INSERT INTO PatientTreatment(PatientTreatmentID,EncounterID,TreatmentID,ResponsiblePhysicianID,StartDate,EndDate,Outcome,Compliance,FrequencyTreatment,ResponsibleRole) VALUES (?,?,?,?,?,?,?,?,?,?)',
                    (i,i,1 if i%2 else 2,1 if i%2 else 2,s,e,'Illustrative outcome','Illustrative adherence','Once','Treating physician'))
    # A second treatment within the same stay demonstrates the one-to-many relation.
    con.execute('INSERT INTO PatientTreatment(PatientTreatmentID,EncounterID,TreatmentID,ResponsiblePhysicianID,StartDate,EndDate,Outcome,Compliance,FrequencyTreatment,ResponsibleRole) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (16,1,2,2,'2026-01-02','2026-01-03','Illustrative outcome','Illustrative adherence','Once','Treating physician'))
    con.executemany('INSERT INTO PhysicianTreatment VALUES (?,?,?)',[(3,1,'Consultant'),(3,2,'Consultant'),(1,16,'Supporting clinician')])
    con.executemany('INSERT INTO Medication(MedicationID,MedicationName) VALUES (?,?)',[(1,'Demo medication A'),(2,'Demo medication B')])
    con.executemany('INSERT INTO MedicationOrder(MedicationOrderID,PatientTreatmentID,MedicationID,Dosage,Frequency) VALUES (?,?,?,?,?)',
       [(i,i,1 if i%2 else 2,'1 fictional unit','Demo frequency') for i in range(1,17)])
    con.executemany('INSERT INTO SideEffect VALUES (?,?)',[(1,'Illustrative effect A'),(2,'Illustrative effect B')])
    con.executemany('INSERT INTO MedicationSideEffect VALUES (?,?)',[(1,1),(1,2),(2,2)])
    con.executemany('INSERT INTO TreatmentSideEffect VALUES (?,?)',[(1,1),(2,2)])
    con.executemany('INSERT INTO InfectionType VALUES (?,?)',[(1,'Demo infection category A'),(2,'Demo infection category B')])
    con.executemany('INSERT INTO HospitalInfection(HospitalInfectionID,EncounterID,InfectionTypeID,DetectedDate,HospitalAcquired,ResolvedDate) VALUES (?,?,?,?,?,?)',
       [(1,1,1,'2026-01-02',1,'2026-01-03'),(2,1,2,'2026-01-03',1,None),
        (3,2,1,'2026-01-25',1,'2026-01-26'),(4,7,2,'2026-03-01',0,'2026-03-05')])
    con.commit()
    assert not con.execute('PRAGMA foreign_key_check').fetchall()
    assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    con.close()
    print(f'Built {path.name}: 8 synthetic patients, 15 encounters, 16 treatments.')
    return path


if __name__ == '__main__':
    build()
