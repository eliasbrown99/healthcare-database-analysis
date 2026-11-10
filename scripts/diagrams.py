"""Generate exact schema diagrams from metadata. Requires Graphviz's dot command."""
import argparse
import html
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/diagrams'
RENDER_IMAGES=True


def render(name,title,subtitle,tables,edges,color='#163A5F'):
    OUT.mkdir(exist_ok=True,parents=True)
    lines=['digraph G {','graph [rankdir=TB, bgcolor="white", pad="0.3", nodesep="0.4", ranksep="0.65", splines=polyline, fontname="DejaVu Sans", labelloc=t, fontsize=20, label='+json.dumps(title+'\n'+subtitle)+'];',
           'node [shape=plain, fontname="DejaVu Sans"];',
           'edge [color="#728397", arrowsize=0.65, fontname="DejaVu Sans", fontsize=10];']
    for table,cols in tables.items():
        label='<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="8" COLOR="#CBD5E1">'
        label+=f'<TR><TD BGCOLOR="{color}"><FONT COLOR="white"><B>{table}</B></FONT></TD></TR>'
        for col in cols:label+=f'<TR><TD ALIGN="LEFT" BGCOLOR="#F5F8FC"><FONT POINT-SIZE="11">{html.escape(col)}</FONT></TD></TR>'
        label+='</TABLE>'
        lines.append(f'"{table}" [label=<{label}>];')
    for parent,child,label in edges:
        lines.append(f'"{parent}" -> "{child}" [label={json.dumps(label)}];')
    lines.append('}')
    dot=OUT/(name+'.dot');dot.write_text('\n'.join(lines)+'\n')
    if not RENDER_IMAGES:return
    if not shutil.which('dot'):raise SystemExit('Install Graphviz to render diagrams; .dot source was saved.')
    for fmt in ['svg','png']:
        subprocess.run(['dot','-T'+fmt,'-Gdpi=135',str(dot),'-o',str(OUT/(name+'.'+fmt))],check=True)


def main():
    manifest=json.loads((ROOT/'data/source/manifest.json').read_text())
    selected={
      'Patient':['PK PatientID','Name and demographics'],
      'Hospitalization':['PK PatientCareID','Admission and discharge dates','No PatientID field'],
      'PatientTreatment':['PK PatientTreatmentID','FK PatientID','FK PatientCareID (optional)','FK TreatmentID','InPatient flag'],
      'Physician':['PK PhysicianID','Specialty'],
      'PhysicianTreatment':['PK/FK PhysicianID','PK/FK PatientTreatmentID','Role'],
      'Treatment':['PK TreatmentID','SideEffects text list'],
      'Medication':['PK MedicationID','SideEffects text list'],
      'PatientTreatmentMedication':['PK PatientTreatmentMedicationID','FK PatientTreatmentID','FK MedicationID','Dosage']}
    render('original_schema','Original Access relationships','Arrows run from referenced parent to child. All seven relationships are 1 to many.',selected,
           [(r['szReferencedObject'],r['szObject'],'1 : many') for r in manifest['relationships']],'#663E3E')
    core={
      'Patient':['PK PatientID','Name and demographics','Separate contact name / relationship / phone'],
      'Physician':['PK PhysicianID','Specialty'],
      'Treatment':['PK TreatmentID','Name and description'],
      'Encounter':['PK EncounterID','FK PatientID','Type, dates, visit reason','Generated required-subtype reference','Disposition and follow-up'],
      'Hospitalization':['PK/FK EncounterID','Falls and care metrics'],
      'PatientTreatment':['PK PatientTreatmentID','FK EncounterID','FK TreatmentID','FK ResponsiblePhysicianID','Treatment dates'],
      'PhysicianTreatment':['PK/FK PhysicianID','PK/FK PatientTreatmentID','Additional clinician role'],
      'Medication':['PK MedicationID','MedicationName','StandardDosage reference text'],
      'MedicationOrder':['PK MedicationOrderID','FK PatientTreatmentID','FK MedicationID','FK PrescribingPhysicianID','Dose, frequency, date, indication']}
    render('revised_core','Revised care and medication model','One patient per encounter. Responsibility is mandatory; additional clinicians are optional.',core,[
      ('Patient','Encounter','1 : many'),('Encounter','Hospitalization','inpatient: exactly 1 at commit'),
      ('Encounter','PatientTreatment','1 : many'),('Treatment','PatientTreatment','1 : many'),
      ('Physician','PatientTreatment','responsible / 1 : many'),('Physician','PhysicianTreatment','1 : many'),
      ('PatientTreatment','PhysicianTreatment','1 : many'),('PatientTreatment','MedicationOrder','1 : many'),
      ('Medication','MedicationOrder','1 : many'),('Physician','MedicationOrder','prescriber / 1 : many')])
    render('revised_details','Queryable effects and infection episodes','Extensions to the core model; multiple values are stored as separate rows.',{
      'Medication':['PK MedicationID'],'Treatment':['PK TreatmentID'],
      'SideEffect':['PK SideEffectID','Unique EffectName'],
      'MedicationSideEffect':['PK/FK MedicationID','PK/FK SideEffectID'],
      'TreatmentSideEffect':['PK/FK TreatmentID','PK/FK SideEffectID'],
      'Hospitalization':['PK/FK EncounterID'],
      'HospitalInfection':['PK HospitalInfectionID','FK EncounterID','FK InfectionTypeID','DetectedDate, HospitalAcquired','ResolvedDate (optional)','Organism and clinical note'],
      'InfectionType':['PK InfectionTypeID','Unique TypeName']},[
      ('Medication','MedicationSideEffect','1 : many'),('SideEffect','MedicationSideEffect','1 : many'),
      ('Treatment','TreatmentSideEffect','1 : many'),('SideEffect','TreatmentSideEffect','1 : many'),
      ('Hospitalization','HospitalInfection','1 : many'),('InfectionType','HospitalInfection','1 : many')])
    print('Wrote three diagrams.' if RENDER_IMAGES else 'Wrote three diagram sources.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-only',action='store_true')
    args=parser.parse_args();RENDER_IMAGES=not args.source_only;main()
