"""Generate the implementation dictionary and worked-case tables from SQLite."""
import json
import sqlite3
from pathlib import Path
from scenarios import OUTPATIENT_CAPABILITIES
ROOT=Path(__file__).resolve().parents[1]

def table(headers,rows):
    def cell(value):return str(value if value is not None else '—').replace('|','/').replace('\n',' ')
    return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('| '+' | '.join(map(cell,row))+' |\n' for row in rows)+'\n'

def capability_rows(c):
    rows=[]
    for label,treatment_id in OUTPATIENT_CAPABILITIES.items():
        count=c.execute("SELECT COUNT(*) FROM PatientTreatment t JOIN Encounter e USING(EncounterID) WHERE e.EncounterType='outpatient' AND t.TreatmentID=?",(treatment_id,)).fetchone()[0]
        if not count:
            raise ValueError(f'Advertised capability has no example: {label}')
        rows.append((label,count))
    return rows


def main():
    c=sqlite3.connect(f'file:{ROOT / "data/healthcare_demo.sqlite"}?mode=ro',uri=True)
    p=ROOT/'docs/DESIGN.md';content=p.read_text().split('<!-- GENERATED DICTIONARY -->')[0]+'<!-- GENERATED DICTIONARY -->\n\n'
    for (name,) in c.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name").fetchall():
        refs={r[3]:f'{r[2]}.{r[4]}' for r in c.execute(f'PRAGMA foreign_key_list("{name}")')};rows=[]
        for _,col,typ,required,default,pk,hidden in c.execute(f'PRAGMA table_xinfo("{name}")'):
            keys=([f'PK position {pk}'] if pk else [])+([f'FK → {refs[col]}'] if col in refs else [])
            if hidden:keys.append('Generated; do not edit')
            rows.append((col,typ,'Yes' if required or pk else 'No','; '.join(keys) or '—'))
        content+=f'### {name}\n\n'+table(['Column','SQLite type','Required','Key/reference'],rows)
    p.write_text(content)
    cases=json.loads((ROOT/'docs/rebuild_manifest.json').read_text())['featured_cases']
    content='''# Worked care scenarios

These cases show what the database can accomplish: follow a person's care across visits, distinguish the people responsible for different actions, and produce review worklists with explicit definitions. All cases are fictional. Counts are designed to exercise reports and must not be interpreted as real hospital performance.

## Eight linked examples

The initial visit IDs 1–8 have return visits 161–168 and outpatient follow-up 201–208. Patient IDs are separate identities; they do not equal hospitalization IDs by assumption.

'''
    rows=[]
    for item in cases:
        r=c.execute('SELECT VisitReason,StartDate,EndDate FROM Encounter WHERE EncounterID=?',(item['index_encounter'],)).fetchone()
        nxt=c.execute('SELECT StartDate FROM Encounter WHERE EncounterID=?',(item['return_encounter'],)).fetchone()[0]
        rows.append((item['patient_name'],item['patient_id'],item['index_encounter'],r[0],r[2],nxt,item['gap_days'],'Yes' if item['gap_days']<=30 else 'No'))
    content+=table(['Patient','PatientID','Index visit','Reason','Discharge','Next admission','Gap days','Within 30 days?'],rows)
    content+='''A 30-day return is a review flag, not proof of an avoidable admission or poor care. Planned returns are identified separately. Same-day returns are included in this project's definition; an operational measure would need transfer and exclusion rules.

## Robert Perez: continuity of care

Run `python3 scripts/run_queries.py --patient-id 2 --as-of 2023-12-31`, or run query 07 with those parameters. Robert has a coronary-stent encounter, a return 20 days later, and outpatient rehabilitation. The timeline preserves one row per treatment even when several physicians or medication orders are attached.

'''
    rows=c.execute('''SELECT e.EncounterID,e.EncounterType,p.StartDate,t.TreatmentName,p.Outcome
      FROM PatientTreatment p JOIN Encounter e USING(EncounterID) JOIN Treatment t USING(TreatmentID)
      WHERE e.PatientID=2 ORDER BY p.StartDate,e.EncounterID,p.PatientTreatmentID''').fetchall()
    content+=table(['Visit','Setting','Date','Treatment/workflow','Recorded outcome'],rows)
    content+='''The rehabilitation record documents transportation difficulty and the support arranged. Medication reconciliation records review of access to medicines. These narratives create an actionable review example; they do not establish that a medication gap caused the return admission.

## Selected medication records and the actual prescriber

The following are the selected orders from Robert's first stay. The database does not claim to contain every medication needed during that admission. Query 08 groups by the physician explicitly recorded as the prescriber, rather than all physicians attached to the treatment.

'''
    rows=c.execute('''SELECT m.MedicationName,o.Dosage,o.Frequency,o.Route,o.Indication,p.FirstName||' '||p.LastName
      FROM MedicationOrder o JOIN Medication m USING(MedicationID) JOIN Physician p ON p.PhysicianID=o.PrescribingPhysicianID
      JOIN PatientTreatment t USING(PatientTreatmentID) WHERE t.EncounterID=1 ORDER BY m.MedicationName''').fetchall()
    content+=table(['Medication','Example dose','Frequency','Route','Recorded indication','Prescriber'],rows)
    content+='''## Falls, mobility, and discharge support

Richard Taylor's fracture admission (visit 4) illustrates a high-risk care-planning snapshot, assistance needs, a recorded fall, and a rehabilitation discharge plan. Query 06 exposes these together; a score alone would not explain the support the patient needs. The 1–10 scales are project-specific, with higher ADL meaning more independence.

'''
    rows=c.execute('''SELECT h.FallsRisk,h.ADLScore,h.FallsOccurred,h.ActivityLevel,h.Diet,e.DischargeDisposition,e.FollowUpPlan
      FROM Hospitalization h JOIN Encounter e USING(EncounterID) WHERE e.EncounterID=4''').fetchall()
    content+=table(['Falls risk','ADL','Fall recorded','Assistance','Diet','Disposition','Follow-up'],rows)
    content+='''## Named infection episodes

Type and organism are separate facts. A surgical site infection is an episode category; the organism is a laboratory finding within its fictional narrative. Query 10 distinguishes documented resolution from missing resolution documentation.

'''
    rows=c.execute('''SELECT h.EncounterID,i.TypeName,h.Organism,h.DetectedDate,h.ResolvedDate
      FROM HospitalInfection h JOIN InfectionType i USING(InfectionTypeID) ORDER BY h.HospitalInfectionID LIMIT 3''').fetchall()
    content+=table(['Visit','Episode type','Organism','Detected','Resolution date'],rows)
    content+='''The examples contain limited signs, dates, and device history to make the cases recognizable. Hospital-acquired classification is fictional input; these rows do not contain the complete evidence required to compute NHSN definitions.

## What the reports currently return

At a reporting date of 2023-12-31:

'''
    mean=c.execute((ROOT/'sql/queries/02_average_stay.sql').read_text(),{'as_of':'2023-12-31'}).fetchone()
    returns=c.execute((ROOT/'sql/queries/09_readmission_review.sql').read_text(),{'as_of':'2023-12-31'}).fetchall()
    high=c.execute('SELECT COUNT(*) FROM Hospitalization WHERE FallsRisk>=7').fetchone()[0]
    unresolved=c.execute('SELECT COUNT(*) FROM HospitalInfection WHERE ResolvedDate IS NULL').fetchone()[0]
    content+=table(['Result','Value','Interpretation'],[
      ('Completed inpatient stays',mean[0],'Each stay is counted once, regardless of the number of treatments.'),
      ('Mean elapsed stay',mean[1],'Calendar-day difference; synthetic and not benchmarkable.'),
      ('Returns within 30 days',len(returns),'Includes planned and unplanned returns.'),
      ('Planned among those returns',sum(r[-1]=='planned' for r in returns),'Visible separately; not silently described as preventable.'),
      ('High-falls-risk stays',high,'A care-review worklist, not an adverse-outcome rate.'),
      ('Infection episodes lacking a resolution date',unresolved,'Missing documentation does not prove an active infection.')])
    content+='''## Additional capabilities and limits

These capabilities are counted from actual outpatient treatment rows. Documentation generation fails if any advertised capability has no example. No medication order is forced onto a treatment that does not need one in the recorded subset.

The original catalogs remain available, including treatment types unused in these cases. This preserves the project's breadth while keeping the worked scenarios coherent. [FIELD_MAPPING.md](FIELD_MAPPING.md) records preservation and changes; [CLINICAL_CONTEXT.md](CLINICAL_CONTEXT.md) identifies the sources and interpretation limits.
'''
    content+='\n'+table(['Outpatient capability','Treatment occurrences'],capability_rows(c))
    content+='## Supplemental pediatric cases\n\nPatients 501 and 502 are newly authored fictional identities. All 500 source patients retain their original birth dates. These visits illustrate caregiver involvement and preventive documentation; they do not assert a complete pediatric chart or vaccination schedule.\n\n'
    rows=c.execute("""SELECT p.PatientID,p.FirstName || ' ' || p.LastName,p.DateOfBirth,e.EncounterID,e.StartDate,
      p.EmergencyContactName,p.EmergencyContactRelationship,t.Outcome
      FROM Patient p JOIN Encounter e USING(PatientID) JOIN PatientTreatment t USING(EncounterID)
      WHERE p.PatientID IN (501,502) ORDER BY p.PatientID""").fetchall()
    content+=table(['PatientID','Patient','Birth date','Visit','Visit date','Contact','Relationship','Recorded outcome'],rows)
    content+='## Synthetic patterns and snapshot timing\n\nAll 24 infected stays last 12 days, detection is on day 6, return gaps cycle through selected boundary values, and some outcomes repeat. These deliberate patterns make checks reproducible; they are not estimates of clinical frequencies or recovery times. Falls cases cover adults of different ages, without claiming a typical geriatric case mix. Hospitalization care metrics and IsolationType are discharge-time snapshots, not admission assessments or a time series. Query 06 includes only completed stays by the cutoff. See [REPORTING.md](REPORTING.md) for date and missing-value policies.\n'
    counts=json.loads((ROOT/'docs/rebuild_manifest.json').read_text())
    n=counts['row_counts']
    readme=ROOT/'README.md'
    text=readme.read_text()
    summary=(f"The current scenario database has **{n['Patient']} patients ({n['Patient']-2} original plus 2 supplemental pediatric identities), "
             f"{n['Hospitalization']} inpatient stays, {n['Encounter']-n['Hospitalization']} outpatient encounters, "
             f"{n['PatientTreatment']:,} treatment occurrences, and {n['MedicationOrder']} selected medication orders**. "
             f"Its {counts['physician_assignments_total']:,} physician assignments comprise {n['PatientTreatment']:,} responsible physicians "
             f"and {n['PhysicianTreatment']} additional associations. The catalog has {n['Treatment']} treatment types and {n['Medication']} medications. "
             "Every original source row remains separately available.")
    start=text.index('<!-- GENERATED COUNTS -->')+len('<!-- GENERATED COUNTS -->')
    end=text.index('<!-- END GENERATED COUNTS -->')
    readme.write_text(text[:start]+'\n'+summary+'\n'+text[end:])
    (ROOT/'docs/SCENARIOS.md').write_text(content)
    c.close();print('Updated design dictionary and worked-case report.')

if __name__=='__main__':main()
