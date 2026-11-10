"""Reproduce findings from exported source records using standard-library SQL."""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def snapshot():
    manifest = json.loads((ROOT / 'data/source/manifest.json').read_text())
    path = ROOT / 'data/source_snapshot.sqlite'
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    for name, info in manifest['schema'].items():
        # Deliberately retain the source values; no inferred repairs or new constraints.
        cols = [(c['name'], 'INTEGER' if c['access_type_code'] in (1, 2, 3, 4)
                 else 'REAL' if c['access_type_code'] in (6, 7) else 'TEXT')
                for c in info['columns']]
        con.execute(f'CREATE TABLE "{name}" (' + ', '.join(f'"{k}" {t}' for k, t in cols) + ')')
        rows = json.loads((ROOT / 'data/source' / (name + '.json')).read_text())
        con.executemany(f'INSERT INTO "{name}" VALUES (' + ','.join('?' for _ in cols) + ')',
                        [[row[k] for k, _ in cols] for row in rows])
    con.commit()
    return con, manifest


def audit():
    con, manifest = snapshot()
    scalar = lambda q: con.execute(q).fetchone()[0]
    metrics = {'row_counts': {k: v['row_count'] for k,v in manifest['schema'].items()}}
    checks = {
        'stays_linked_to_multiple_patients': '''SELECT COUNT(*) FROM
          (SELECT PatientCareID FROM PatientTreatment WHERE PatientCareID IS NOT NULL
           GROUP BY PatientCareID HAVING COUNT(DISTINCT PatientID)>1)''',
        'stays_without_any_treatment_link': '''SELECT COUNT(*) FROM Hospitalization h
          WHERE NOT EXISTS (SELECT 1 FROM PatientTreatment p WHERE p.PatientCareID=h.PatientCareID)''',
        'treatments_without_physicians': '''SELECT COUNT(*) FROM PatientTreatment p
          WHERE NOT EXISTS (SELECT 1 FROM PhysicianTreatment x WHERE x.PatientTreatmentID=p.PatientTreatmentID)''',
        'blank_dosages': "SELECT COUNT(*) FROM PatientTreatmentMedication WHERE Dosage IS NULL OR trim(Dosage)=''",
        'linked_treatments': 'SELECT COUNT(*) FROM PatientTreatment WHERE PatientCareID IS NOT NULL',
        'linked_treatments_outside_stay': '''SELECT COUNT(*) FROM PatientTreatment p
          JOIN Hospitalization h ON p.PatientCareID=h.PatientCareID
          WHERE p.StartDate<h.AdmitDate OR p.EndDate>h.DischargeDate''',
        'inpatient_flag_disagreements': '''SELECT COUNT(*) FROM PatientTreatment
          WHERE InPatient <> (PatientCareID IS NOT NULL)''',
        'average_length_of_stay_days': 'SELECT AVG(julianday(DischargeDate)-julianday(AdmitDate)) FROM Hospitalization',
        'hai_stays_with_known_type': 'SELECT COUNT(*) FROM Hospitalization WHERE HospitalAcquiredInfection=1 AND Infection IS NOT NULL',
        'stored_readmission_flags': 'SELECT COUNT(*) FROM Hospitalization WHERE Readmit30Days=1',
        'high_falls_risk_stays': 'SELECT COUNT(*) FROM Hospitalization WHERE FallsRisk>=7',
        'invalid_hospital_dates': 'SELECT COUNT(*) FROM Hospitalization WHERE DischargeDate<AdmitDate',
        'invalid_treatment_dates': 'SELECT COUNT(*) FROM PatientTreatment WHERE EndDate<StartDate',
        'emergency_contacts_equal_truncated_placeholder': "SELECT COUNT(*) FROM Patient WHERE EmergencyContact='Emergency Conta'",
    }
    metrics.update({name: scalar(q) for name,q in checks.items()})
    metrics['foreign_key_orphans'] = {}
    for r in manifest['relationships']:
        q = f'''SELECT COUNT(*) FROM "{r['szObject']}" c
           WHERE c."{r['szColumn']}" IS NOT NULL AND NOT EXISTS
           (SELECT 1 FROM "{r['szReferencedObject']}" p
            WHERE p."{r['szReferencedColumn']}"=c."{r['szColumn']}")'''
        metrics['foreign_key_orphans'][r['szRelationship']] = scalar(q)
    metrics['duplicate_primary_keys'] = {}
    for name, info in manifest['schema'].items():
        cols = ','.join('"' + c + '"' for c in info['primary_key'])
        metrics['duplicate_primary_keys'][name] = scalar(
            f'SELECT COUNT(*) FROM (SELECT {cols} FROM "{name}" GROUP BY {cols} HAVING COUNT(*)>1)')
    metrics['stay_162_patients'] = [r[0] for r in con.execute(
        'SELECT DISTINCT PatientID FROM PatientTreatment WHERE PatientCareID=162 ORDER BY PatientID')]
    metrics['patient_212_medications'] = [r[0] for r in con.execute('''
        SELECT DISTINCT m.MedicationName FROM PatientTreatment t
        JOIN PatientTreatmentMedication p USING(PatientTreatmentID)
        JOIN Medication m USING(MedicationID) WHERE t.PatientID=212 ORDER BY m.MedicationName''')]
    metrics['hai_distribution'] = [dict(r) for r in con.execute('''
        SELECT Infection,COUNT(*) AS count FROM Hospitalization
        WHERE HospitalAcquiredInfection=1 AND Infection IS NOT NULL GROUP BY Infection ORDER BY Infection''')]
    metrics['medication_counts'] = [dict(r) for r in con.execute('''
        SELECT m.MedicationName,COUNT(*) AS count FROM PatientTreatmentMedication p
        JOIN Medication m USING(MedicationID) GROUP BY m.MedicationName ORDER BY count DESC,m.MedicationName''')]
    metrics['saved_queries'] = manifest['saved_queries']
    metrics['forms'] = manifest['forms']
    metrics['reports'] = manifest['reports']
    con.close()
    (ROOT / 'docs/source_audit_results.json').write_text(json.dumps(metrics, indent=2)+'\n')
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == '__main__':
    audit()
