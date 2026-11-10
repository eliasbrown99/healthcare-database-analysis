"""Explicit educational scenarios. These are authored cases, not sampled clinical data."""
# Medication tuples: catalog ID, dose, frequency, route, recorded indication.
CARDIAC_ORDERS = [(5,'81 mg','Once daily','Oral','Antiplatelet therapy for coronary artery disease'),
 (16,'75 mg','Once daily','Oral','Maintenance antiplatelet therapy after coronary stenting'),
 (1,'40 mg','Once daily','Oral','Lipid lowering for coronary artery disease')]
PAIN_ORDER = [(21,'650 mg','Every 6 hours as needed for pain; maximum 2600 mg in 24 hours in this case','Oral','Postoperative pain')]
INPATIENT = [
 dict(key='pci',reason='Coronary artery disease with persistent angina; coronary stent placement',specialty='Cardiology',procedure=1,anesthesia=None,days=3,risk=4,adl=8,diet='Cardiac',activity='Independent after access-site precautions',assessment=39,outcome='No recurrent chest discomfort before discharge; access site remained dry.',followup='Cardiology review in 2 weeks; cardiac rehabilitation referral; review access to antiplatelet medicines.',meds=CARDIAC_ORDERS,return_reason='Recurrent chest discomfort after recent PCI; medication access review',return_outcome='Evaluation completed without repeat intervention; pharmacy arranged access to prescribed medicines.'),
 dict(key='cabg',reason='Multivessel coronary artery disease; planned coronary bypass surgery',specialty='Surgery',procedure=2,anesthesia=11,days=7,risk=7,adl=5,diet='Cardiac',activity='Assist x 1 with ambulation',assessment=34,outcome='Ambulating with assistance; incision reviewed; sternal precautions understood.',followup='Cardiothoracic surgery review in 2 weeks; home-health support; cardiac rehabilitation referral.',meds=[CARDIAC_ORDERS[0],CARDIAC_ORDERS[2]],return_reason='Incisional discomfort and drainage after coronary bypass surgery',return_outcome='Wound assessment completed; dressing plan and early surgical follow-up arranged.'),
 dict(key='joint',reason='Advanced knee osteoarthritis; elective joint replacement',specialty='Orthopedics',procedure=17,anesthesia=12,days=3,risk=8,adl=4,diet='Regular',activity='Assist x 1 with walker',assessment=33,outcome='Walked 60 metres with a walker; needs help with transfers and stairs.',followup='Orthopedic review in 2 weeks; outpatient rehabilitation; caregiver to assist on stairs.',meds=PAIN_ORDER,return_reason='Persistent pain and difficulty mobilizing after knee replacement',return_outcome='Pain and mobility reassessed; equipment and rehabilitation plan adjusted.'),
 dict(key='fracture',reason='Displaced hip fracture after a fall at home; operative fixation',specialty='Orthopedics',procedure=19,anesthesia=11,days=5,risk=9,adl=3,diet='Regular',activity='Assist x 2 for transfers',assessment=33,outcome='Transfer practice completed with two-person assistance; rehabilitation placement arranged.',followup='Transfer to inpatient rehabilitation; orthopedic follow-up in 2 weeks.',meds=PAIN_ORDER,return_reason='Functional decline and uncontrolled pain during fracture recovery',return_outcome='Orthopedic review found no new injury; rehabilitation intensity and support needs reassessed.'),
 dict(key='pacemaker',reason='Symptomatic bradycardia; permanent pacemaker implantation',specialty='Cardiology',procedure=3,anesthesia=None,days=2,risk=6,adl=7,diet='Cardiac',activity='Assist x 1 until dizziness resolves',assessment=35,outcome='Device check satisfactory; no further presyncope recorded before discharge.',followup='Device-clinic check in 1 week; wound precautions reviewed.',meds=[],return_reason='Dizziness after pacemaker implantation; device and medication review',return_outcome='Device interrogation satisfactory; symptoms reassessed and follow-up arranged.'),
 dict(key='gallbladder',reason='Acute cholecystitis; laparoscopic cholecystectomy',specialty='Surgery',procedure=9,anesthesia=11,days=3,risk=5,adl=7,diet='Regular as tolerated',activity='Independent ambulation as tolerated',assessment=34,outcome='Tolerating oral intake; incisions dry; pain controlled before discharge.',followup='Surgical clinic in 2 weeks; review wound care and return precautions.',meds=PAIN_ORDER,return_reason='Persistent nausea and reduced intake after cholecystectomy',return_outcome='Oral intake improved during observation and supportive care; discharge instructions reviewed.'),
 dict(key='appendix',reason='Acute appendicitis; laparoscopic appendectomy',specialty='Surgery',procedure=8,anesthesia=11,days=2,risk=4,adl=8,diet='Regular as tolerated',activity='Independent ambulation as tolerated',assessment=34,outcome='Abdominal discomfort improving; tolerating diet; wounds reviewed before discharge.',followup='Surgical clinic in 2 weeks; wound care and activity instructions supplied.',meds=PAIN_ORDER,return_reason='Abdominal pain after appendectomy requiring reassessment',return_outcome='Surgical reassessment completed; symptoms improved and follow-up arranged.'),
 dict(key='hernia',reason='Symptomatic abdominal-wall hernia; elective repair',specialty='Surgery',procedure=10,anesthesia=11,days=2,risk=4,adl=8,diet='Regular',activity='Independent with temporary lifting restrictions',assessment=34,outcome='Incision dry; mobilizing independently; lifting restrictions understood.',followup='Surgical clinic in 2 weeks; avoid lifting until cleared by the treating team.',meds=PAIN_ORDER,return_reason='Postoperative pain and reduced mobility after hernia repair',return_outcome='Wound and mobility reviewed; pain-management instructions clarified.')]
ADDED_TREATMENTS = [
 (32,'Medication reconciliation','Compare the reported medication list with the intended plan and resolve discrepancies'),
 (33,'Mobility assessment','Assess transfers, walking, equipment, and assistance needs'),
 (34,'Wound assessment','Review the wound and document healing, drainage, and care needs'),
 (35,'Pacemaker interrogation','Review recorded device function and arrange device-clinic follow-up'),
 (36,'Infection evaluation','Review a suspected or documented infection and its follow-up plan'),
 (37,'Discharge planning','Coordinate follow-up, education, equipment, and care setting'),
 (38,'Nutrition counseling','Discuss a condition-appropriate eating plan and barriers to following it'),
 (39,'Symptom reassessment','Document symptom progression and the need for further evaluation')]

# Supplemental fictional identities; none replaces an original patient's birth date.
PEDIATRIC_PATIENTS = [
    dict(id=501, first='Ava', last='Morgan', dob='2015-05-14', gender='Female',
         contact='Leah Morgan', relationship='Parent', phone='202-555-0198', visit='2023-09-12'),
    dict(id=502, first='Noah', last='Rivera', dob='2010-02-23', gender='Male',
         contact='Mateo Rivera', relationship='Parent', phone='202-555-0199', visit='2023-09-19'),
]
# Each advertised outpatient capability must have real treatment rows.
OUTPATIENT_CAPABILITIES = {
    'Thyroid replacement follow-up': 6,
    'Well-child visits': 20,
    'Acne care': 28,
    'Psychotherapy': 29,
    'Skin-biopsy evaluation': 26,
}
