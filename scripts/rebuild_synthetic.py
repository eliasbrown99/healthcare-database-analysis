"""Build meaningful, deterministic fictional care scenarios from source catalogs.

The original rows remain in data/source. This is a scenario rebuild, not a
lossless clinical-history migration or a representative sample of a hospital.
"""
import json
import sqlite3
from collections import defaultdict
from datetime import date,timedelta
from pathlib import Path
from scenarios import INPATIENT,ADDED_TREATMENTS,PEDIATRIC_PATIENTS
from database import connect

ROOT=Path(__file__).resolve().parents[1]


def build():
    data={p.stem:json.loads(p.read_text()) for p in (ROOT/'data/source').glob('*.json') if p.stem!='manifest'}
    path=ROOT/'data/healthcare_demo.sqlite';path.unlink(missing_ok=True)
    con=connect(path,create=True);con.executescript((ROOT/'sql/schema.sql').read_text())
    patients={p['PatientID']:p for p in data['Patient']}
    for p in patients.values():
        # All names and contact records are fictional; reserved addresses avoid accidental contact.
        contact=data['Patient'][(p['PatientID']+37)%len(data['Patient'])]
        con.execute('INSERT INTO Patient VALUES (?,?,?,?,?,?,?,?,?,?,?)',
          (p['PatientID'],p['FirstName'],p['LastName'],p['DateOfBirth'][:10],
           f"patient{p['PatientID']}@example.invalid",f"{contact['FirstName']} {contact['LastName']}",'Designated contact',f"202-555-{100+p['PatientID']%100:04d}",p['PhoneNumber'],p['Address'],p['Gender']))
    physicians=defaultdict(list)
    for p in data['Physician']:
        con.execute('INSERT INTO Physician VALUES (?,?,?,?,?)',(p['PhysicianID'],p['FirstName'],p['LastName'],p['Specialty'],f"physician{p['PhysicianID']}@example.invalid"))
        physicians[p['Specialty']].append(p['PhysicianID'])
    for t in data['Treatment']:
        description=t['Description']
        if t['TreatmentID']==27:description='Treats skin issues with focused light'
        if t['TreatmentID']==28:description='Improves skin by reducing acne'
        con.execute('INSERT INTO Treatment VALUES (?,?,?)',(t['TreatmentID'],t['TreatmentName'],description))
    con.executemany('INSERT INTO Treatment VALUES (?,?,?)',ADDED_TREATMENTS)
    for m in data['Medication']:
        con.execute('INSERT INTO Medication VALUES (?,?,?)',(m['MedicationID'],m['MedicationName'],m['StandardDosage']))
    con.execute('INSERT INTO Medication VALUES (21,?,?)',('Acetaminophen','650 mg (example order dose)'))
    effects={}
    for table,field,bridge in [('Medication','MedicationID','MedicationSideEffect'),('Treatment','TreatmentID','TreatmentSideEffect')]:
        for row in data[table]:
            for raw in (row.get('SideEffects') or '').split(','):
                effect=raw.strip().rstrip('.').strip()
                if not effect:continue
                key=effect.casefold()
                if key not in effects:
                    effects[key]=len(effects)+1;con.execute('INSERT INTO SideEffect VALUES (?,?)',(effects[key],effect))
                con.execute(f'INSERT OR IGNORE INTO {bridge} VALUES (?,?)',(row[field],effects[key]))
    con.executemany('INSERT INTO InfectionType VALUES (?,?)',[(1,'Surgical site infection'),(2,'Catheter-associated urinary tract infection'),(3,'Hospital-acquired pneumonia')])
    tid=oid=0;stays={};latest={};case_log=[]

    def clinician(specialty,offset=0):
        values=physicians[specialty];return values[offset%len(values)]

    def treatment(eid,type_id,start,end,specialty,outcome,compliance,frequency='Once',role=None,additional=None):
        nonlocal tid
        tid+=1;lead=clinician(specialty,tid)
        role=role or ('Operating surgeon' if type_id in [2,8,9,10,17,19] else 'Anesthesiologist' if type_id in [11,12] else 'Treating physician')
        con.execute('INSERT INTO PatientTreatment VALUES (?,?,?,?,?,?,?,?,?,?)',
            (tid,eid,type_id,lead,str(start),str(end),outcome,compliance,frequency,role))
        if additional:
            other_specialty,other_role=additional;other=clinician(other_specialty,tid+1)
            if other==lead:other=clinician(other_specialty,tid+2)
            con.execute('INSERT INTO PhysicianTreatment VALUES (?,?,?)',(other,tid,other_role))
        return tid,lead

    def orders(treatment_id,lead,when,meds):
        nonlocal oid
        for mid,dose,frequency,route,indication in meds:
            oid+=1
            con.execute('INSERT INTO MedicationOrder VALUES (?,?,?,?,?,?,?,?,?)',(oid,treatment_id,mid,dose,frequency,lead,str(when),route,indication))

    adults=[p for p in patients.values() if '1945-01-01'<=p['DateOfBirth']<'1980-01-01'][:160]
    infected_ids=[i for i in range(1,161) if (i-1)%8 in (1,2,3)][:24]
    infection_index={eid:i for i,eid in enumerate(infected_ids)}
    for eid,p in enumerate(adults,1):
        profile=INPATIENT[(eid-1)%8];start=date(2023,1,2)+timedelta(days=(eid-1)%150)
        end=start+timedelta(days=max(profile['days'],12) if eid in infection_index else profile['days'])
        stays[eid]=(p,profile,start,end);latest[p['PatientID']]=(eid,profile,end)
        disposition='Inpatient rehabilitation' if profile['key']=='fracture' else 'Home with home-health support' if profile['key'] in ('cabg','joint') else 'Home'
        admission='unplanned' if profile['key'] in ('fracture','gallbladder','appendix','pacemaker') else 'planned'
        con.execute('INSERT INTO Encounter VALUES (?,?,?,?,?,?,?,?,?)',(eid,p['PatientID'],'inpatient',str(start),str(end),profile['reason'],admission,disposition,profile['followup']))
        fall=int(eid in [4,20,36,52,68,84]);mederror=int(profile['key']=='pci' and eid in [17,49,81]);adherent=int(eid%13!=0)
        isolation='Contact precautions pending infection-prevention review' if eid in infection_index else 'Standard precautions'
        con.execute('INSERT INTO Hospitalization VALUES (?,?,?,?,?,?,?,?,?)',(eid,profile['risk'],profile['adl'],fall,mederror,profile['diet'],adherent,profile['activity'],isolation))
        compliance='Teach-back completed; patient and designated contact understand the plan.' if adherent else 'Patient requested additional explanation; care team repeated education using teach-back.'
        procedure_day=start+timedelta(days=1)
        treatment(eid,profile['procedure'],procedure_day,procedure_day,profile['specialty'],profile['outcome'],compliance,additional=(profile['specialty'],'Assisting surgeon' if profile['anesthesia'] else 'Consulting physician'))
        if profile['anesthesia']:
            treatment(eid,profile['anesthesia'],procedure_day,procedure_day,'Anesthesiology','Anesthetic episode completed; recovery handoff documented.','Pre-procedure assessment and consent documented.',role='Anesthesiologist')
        assessment_note='Daily recovery review documented mobility, symptoms, and support needs; discharge goals reassessed.'
        if fall:assessment_note+=' Assisted fall during toileting without injury; supervision and transfer plan reassessed.'
        treatment(eid,profile['assessment'],procedure_day,end,profile['specialty'],assessment_note,compliance,'Daily while hospitalized',additional=(profile['specialty'],'Consulting physician'))
        reconciliation='Medication list reviewed with patient; discharge instructions reconciled.'
        if mederror:reconciliation+=' A delayed atorvastatin dose was recorded as a medication error; schedule clarified.'
        mt,lead=treatment(eid,32,end,end,profile['specialty'],reconciliation,compliance)
        orders(mt,lead,end,profile['meds'])
        treatment(eid,37,end,end,profile['specialty'],profile['followup'],compliance,additional=(profile['specialty'],'Discharging physician'))
        if eid in infection_index:
            index=infection_index[eid];kind=index%3+1;detected=start+timedelta(days=5);resolved=end-timedelta(days=1) if index%4 else None
            organism={1:'Methicillin-susceptible Staphylococcus aureus',2:'Escherichia coli',3:'Klebsiella pneumoniae'}[kind]
            note={1:'Incisional drainage and local erythema documented on day 6; wound specimen grew the recorded organism.',2:'Indwelling urinary catheter present on hospital days 1–5; urinary symptoms and a positive culture recorded on day 6.',3:'New cough, fever, and a new infiltrate recorded on day 6; respiratory specimen grew the recorded organism.'}[kind]
            note+=' Fictional infection-prevention review classified the episode as hospital acquired; full surveillance criteria are not encoded.'
            con.execute('INSERT INTO HospitalInfection VALUES (?,?,?,?,?,?,?,?)',(index+1,eid,kind,str(detected),1,str(resolved) if resolved else None,organism,note))
            treatment(eid,36,detected,end,profile['specialty'],'Infection reviewed; treatment and follow-up documented in the case narrative. '+('Symptoms improving before discharge.' if resolved else 'Follow-up needed to confirm resolution.'),'Patient participated in specimen collection and education.','Daily review')
        if eid<=8:case_log.append({'patient_id':p['PatientID'],'patient_name':p['FirstName']+' '+p['LastName'],'index_encounter':eid,'scenario':profile['key']})

    # Forty of 160 patients have a second inpatient encounter. Purpose and gaps are explicit.
    for original in range(1,41):
        eid=160+original;p,profile,old_start,old_end=stays[original]
        gap=[20,30,31,45,60,90,10,0][(original-1)%8];start=old_end+timedelta(days=gap);end=start+timedelta(days=2+original%3)
        planned=profile['key']=='pci' and original>8
        reason='Planned staged coronary intervention for a second lesion' if planned else profile['return_reason']
        outcome='Staged coronary intervention completed; maintenance regimen reviewed.' if planned else profile['return_outcome']
        con.execute('INSERT INTO Encounter VALUES (?,?,?,?,?,?,?,?,?)',(eid,p['PatientID'],'inpatient',str(start),str(end),reason,'planned' if planned else 'unplanned','Home with follow-up',profile['followup']))
        con.execute('INSERT INTO Hospitalization VALUES (?,?,?,?,?,?,?,?,?)',(eid,profile['risk'],min(profile['adl']+1,10),0,0,profile['diet'],1,profile['activity'],'Standard precautions'))
        compliance='Plan reviewed with patient; questions addressed before discharge.'
        treatment(eid,1 if planned else 39,start,end,profile['specialty'],outcome,compliance,additional=(profile['specialty'],'Consulting physician'))
        mt,lead=treatment(eid,32,end,end,profile['specialty'],'Prescriptions and access barriers reviewed with pharmacy.' if original==1 else 'Current medication list and recent changes reconciled.',compliance)
        orders(mt,lead,end,profile['meds'])
        treatment(eid,37,end,end,profile['specialty'],profile['followup'],compliance)
        latest[p['PatientID']]=(eid,profile,end)
        for case in case_log:
            if case['index_encounter']==original:case['return_encounter']=eid;case['gap_days']=gap

    # Follow-up care for the same 160 patients links the hospital story to outpatient care.
    for offset,p in enumerate(adults,201):
        _,profile,last_end=latest[p['PatientID']];when=last_end+timedelta(days=14);eid=offset
        ttype=4 if profile['key'] in ('pci','cabg') else 33 if profile['key'] in ('joint','fracture') else 35 if profile['key']=='pacemaker' else 34
        reason={4:'Cardiac rehabilitation intake after hospitalization',33:'Post-discharge mobility and rehabilitation review',35:'Device-clinic follow-up after pacemaker implantation',34:'Postoperative wound follow-up'}[ttype]
        out={4:'Baseline exercise tolerance documented; supervised rehabilitation schedule agreed.',33:'Walking distance and transfer needs reviewed; rehabilitation goals updated.',35:'Device interrogation satisfactory; next device-clinic visit scheduled.',34:'Incision reviewed; wound-care and activity instructions updated.'}[ttype]
        adherence='First rehabilitation appointment was rescheduled because transportation was unavailable; transport support arranged.' if p['PatientID']==adults[0]['PatientID'] else 'Patient attended the scheduled follow-up and demonstrated understanding of the plan.'
        con.execute('INSERT INTO Encounter VALUES (?,?,?,?,?,?,?,?,?)',(eid,p['PatientID'],'outpatient',str(when),str(when),reason,None,None,'Continue the agreed follow-up schedule; contact the care team for new symptoms.'))
        specialty='Cardiology' if ttype in [4,35] else profile['specialty']
        treatment(eid,ttype,when,when,specialty,out,adherence,'Initial assessment; subsequent visits scheduled')
        if p['PatientID']==adults[0]['PatientID']:
            treatment(eid,32,when,when,'Cardiology','Medication access confirmed with pharmacy; no gaps reported since readmission.',adherence)

    # Additional adult outpatient examples preserve chronic-care and procedural use cases.
    used={p['PatientID'] for p in adults};background=[p for p in patients.values() if p['PatientID'] not in used][:209]
    for offset,p in enumerate(background,361):
        when=date(2023,8,1)+timedelta(days=(offset-361)%90);eid=offset
        if offset%4==0:
            ttype=6;specialty='Endocrinology';reason='Hypothyroidism medication follow-up';out='Symptoms and medication timing reviewed; repeat thyroid laboratory testing arranged.';freq='Review after laboratory testing';meds=[(9,'25 mcg','Once daily on an empty stomach','Oral','Thyroid hormone replacement; individualized dose reviewed at follow-up')];follow='Repeat thyroid testing and review the prescribed dose with endocrinology.'
        elif offset%4==1:
            ttype=28;specialty='Dermatology';reason='Acne treatment follow-up';out='Inflammatory lesions improving; skin-care routine and tolerability reviewed.';freq='Follow-up in 8 weeks';meds=[];follow='Continue the agreed skin-care plan and attend dermatology follow-up.'
        elif offset%4==2:
            ttype=29;specialty='Psychiatry';reason='Follow-up for depressive symptoms';out='Sleep and daily functioning discussed; therapy goals and support plan updated.';freq='Weekly sessions';meds=[];follow='Continue scheduled psychotherapy; review symptoms with the treating clinician.'
        else:
            ttype=26;specialty='Dermatology';reason='Evaluation of a changing skin lesion';out='Biopsy obtained; wound-care instructions supplied; pathology review pending.';freq='Once';meds=[];follow='Return for pathology review and wound check.'
        con.execute('INSERT INTO Encounter VALUES (?,?,?,?,?,?,?,?,?)',(eid,p['PatientID'],'outpatient',str(when),str(when),reason,None,None,follow))
        pt,lead=treatment(eid,ttype,when,when,specialty,out,'Patient or caregiver participated in shared planning and teach-back.',freq)
        orders(pt,lead,when,meds)

    # Two additional patients make the pediatric capability concrete without rewriting source identities.
    for eid,p in enumerate(PEDIATRIC_PATIENTS,570):
        con.execute('INSERT INTO Patient VALUES (?,?,?,?,?,?,?,?,?,?,?)',
          (p['id'],p['first'],p['last'],p['dob'],f"patient{p['id']}@example.invalid",
           p['contact'],p['relationship'],p['phone'],p['phone'],'Fictional household address',p['gender']))
        when=date.fromisoformat(p['visit'])
        con.execute('INSERT INTO Encounter VALUES (?,?,?,?,?,?,?,?,?)',
          (eid,p['id'],'outpatient',p['visit'],p['visit'],'Routine well-child visit',None,None,
           'Continue scheduled preventive visits; caregiver to provide any missing immunization records.'))
        treatment(eid,20,when,when,'Pediatrics',
          'Growth, school participation, sleep, and immunization documentation reviewed with caregiver; follow-up plan recorded.',
          'Patient and caregiver participated in the visit and discussed the follow-up plan.',
          'Preventive visit; next appointment arranged',role='Pediatrician')

    con.commit()
    assert not con.execute('PRAGMA foreign_key_check').fetchall()
    assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    counts={r[0]:con.execute(f'SELECT COUNT(*) FROM "{r[0]}"').fetchone()[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()}
    total_assignments=con.execute('SELECT COUNT(*) FROM TreatmentCareTeam').fetchone()[0]
    con.close()
    manifest={'version':3,'provenance':'Authored synthetic scenarios authorized by Elias Brown; not recovered histories or population estimates.',
      'supplemental_patient_ids':[p['id'] for p in PEDIATRIC_PATIENTS],
      'row_counts':counts,'physician_assignments_total':total_assignments,'featured_cases':case_log,
      'preserved_catalogs':'All 31 original treatment entries and 20 original medication entries; two treatment-description typos corrected; original dose references restored.',
      'regeneration':'Visit dates, associations, outcomes, care metrics, roles, and selected medication orders rebuilt from scenario definitions. Counts are not forced to match the original.',
      'medication_scope':'Selected example orders, including maintenance therapy; not complete perioperative/anesthetic/antimicrobial prescribing or administration records.',
      'infection_scope':'Named episode categories and organisms; fictional adjudication rather than computed NHSN definitions.',
      'score_definitions':{'FallsRisk':'Project-specific 1–10 score: higher means greater risk; not Morse or another validated instrument.','ADLScore':'Project-specific 1–10 score: higher means more independence; not Katz/Barthel.'}}
    (ROOT/'docs/rebuild_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Built scenario dataset:',json.dumps(counts));return path


if __name__=='__main__':build()
