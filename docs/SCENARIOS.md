# Worked care scenarios

These cases show what the database can accomplish: follow a person's care across visits, distinguish the people responsible for different actions, and produce review worklists with explicit definitions. All cases are fictional. Counts are designed to exercise reports and must not be interpreted as real hospital performance.

## Eight linked examples

The initial visit IDs 1–8 have return visits 161–168 and outpatient follow-up 201–208. Patient IDs are separate identities; they do not equal hospitalization IDs by assumption.

| Patient | PatientID | Index visit | Reason | Discharge | Next admission | Gap days | Within 30 days? |
|---|---|---|---|---|---|---|---|
| Robert Perez | 2 | 1 | Coronary artery disease with persistent angina; coronary stent placement | 2023-01-05 | 2023-01-25 | 20 | Yes |
| Elizabeth Gonzalez | 4 | 2 | Multivessel coronary artery disease; planned coronary bypass surgery | 2023-01-15 | 2023-02-14 | 30 | Yes |
| Barbara Wilson | 5 | 3 | Advanced knee osteoarthritis; elective joint replacement | 2023-01-16 | 2023-02-16 | 31 | No |
| Richard Taylor | 6 | 4 | Displaced hip fracture after a fall at home; operative fixation | 2023-01-17 | 2023-03-03 | 45 | No |
| Paul Jackson | 8 | 5 | Symptomatic bradycardia; permanent pacemaker implantation | 2023-01-08 | 2023-03-09 | 60 | No |
| Paul Davis | 10 | 6 | Acute cholecystitis; laparoscopic cholecystectomy | 2023-01-10 | 2023-04-10 | 90 | No |
| James Wilson | 11 | 7 | Acute appendicitis; laparoscopic appendectomy | 2023-01-10 | 2023-01-20 | 10 | Yes |
| John White | 14 | 8 | Symptomatic abdominal-wall hernia; elective repair | 2023-01-11 | 2023-01-11 | 0 | Yes |

A 30-day return is a review flag, not proof of an avoidable admission or poor care. Planned returns are identified separately. Same-day returns are included in this project's definition; an operational measure would need transfer and exclusion rules.

## Robert Perez: continuity of care

Run `python3 scripts/run_queries.py --patient-id 2 --as-of 2023-12-31`, or run query 07 with those parameters. Robert has a coronary-stent encounter, a return 20 days later, and outpatient rehabilitation. The timeline preserves one row per treatment even when several physicians or medication orders are attached.

| Visit | Setting | Date | Treatment/workflow | Recorded outcome |
|---|---|---|---|---|
| 1 | inpatient | 2023-01-03 | Angioplasty | No recurrent chest discomfort before discharge; access site remained dry. |
| 1 | inpatient | 2023-01-03 | Symptom reassessment | Daily recovery review documented mobility, symptoms, and support needs; discharge goals reassessed. |
| 1 | inpatient | 2023-01-05 | Medication reconciliation | Medication list reviewed with patient; discharge instructions reconciled. |
| 1 | inpatient | 2023-01-05 | Discharge planning | Cardiology review in 2 weeks; cardiac rehabilitation referral; review access to antiplatelet medicines. |
| 161 | inpatient | 2023-01-25 | Symptom reassessment | Evaluation completed without repeat intervention; pharmacy arranged access to prescribed medicines. |
| 161 | inpatient | 2023-01-28 | Medication reconciliation | Prescriptions and access barriers reviewed with pharmacy. |
| 161 | inpatient | 2023-01-28 | Discharge planning | Cardiology review in 2 weeks; cardiac rehabilitation referral; review access to antiplatelet medicines. |
| 201 | outpatient | 2023-02-11 | Cardiac Rehabilitation | Baseline exercise tolerance documented; supervised rehabilitation schedule agreed. |
| 201 | outpatient | 2023-02-11 | Medication reconciliation | Medication access confirmed with pharmacy; no gaps reported since readmission. |

The rehabilitation record documents transportation difficulty and the support arranged. Medication reconciliation records review of access to medicines. These narratives create an actionable review example; they do not establish that a medication gap caused the return admission.

## Selected medication records and the actual prescriber

The following are the selected orders from Robert's first stay. The database does not claim to contain every medication needed during that admission. Query 08 groups by the physician explicitly recorded as the prescriber, rather than all physicians attached to the treatment.

| Medication | Example dose | Frequency | Route | Recorded indication | Prescriber |
|---|---|---|---|---|---|
| Aspirin | 81 mg | Once daily | Oral | Antiplatelet therapy for coronary artery disease | Karen Edwards |
| Atorvastatin | 40 mg | Once daily | Oral | Lipid lowering for coronary artery disease | Karen Edwards |
| Clopidogrel | 75 mg | Once daily | Oral | Maintenance antiplatelet therapy after coronary stenting | Karen Edwards |

## Falls, mobility, and discharge support

Richard Taylor's fracture admission (visit 4) illustrates a high-risk care-planning snapshot, assistance needs, a recorded fall, and a rehabilitation discharge plan. Query 06 exposes these together; a score alone would not explain the support the patient needs. The 1–10 scales are project-specific, with higher ADL meaning more independence.

| Falls risk | ADL | Fall recorded | Assistance | Diet | Disposition | Follow-up |
|---|---|---|---|---|---|---|
| 9 | 3 | 1 | Assist x 2 for transfers | Regular | Inpatient rehabilitation | Transfer to inpatient rehabilitation; orthopedic follow-up in 2 weeks. |

## Named infection episodes

Type and organism are separate facts. A surgical site infection is an episode category; the organism is a laboratory finding within its fictional narrative. Query 10 distinguishes documented resolution from missing resolution documentation.

| Visit | Episode type | Organism | Detected | Resolution date |
|---|---|---|---|---|
| 2 | Surgical site infection | Methicillin-susceptible Staphylococcus aureus | 2023-01-08 | — |
| 3 | Catheter-associated urinary tract infection | Escherichia coli | 2023-01-09 | 2023-01-15 |
| 4 | Hospital-acquired pneumonia | Klebsiella pneumoniae | 2023-01-10 | 2023-01-16 |

The examples contain limited signs, dates, and device history to make the cases recognizable. Hospital-acquired classification is fictional input; these rows do not contain the complete evidence required to compute NHSN definitions.

## What the reports currently return

At a reporting date of 2023-12-31:

| Result | Value | Interpretation |
|---|---|---|
| Completed inpatient stays | 200 | Each stay is counted once, regardless of the number of treatments. |
| Mean elapsed stay | 4.14 | Calendar-day difference; synthetic and not benchmarkable. |
| Returns within 30 days | 20 | Includes planned and unplanned returns. |
| Planned among those returns | 4 | Visible separately; not silently described as preventable. |
| High-falls-risk stays | 75 | A care-review worklist, not an adverse-outcome rate. |
| Infection episodes lacking a resolution date | 6 | Missing documentation does not prove an active infection. |

## Additional capabilities and limits

These capabilities are counted from actual outpatient treatment rows. Documentation generation fails if any advertised capability has no example. No medication order is forced onto a treatment that does not need one in the recorded subset.

The original catalogs remain available, including treatment types unused in these cases. This preserves the project's breadth while keeping the worked scenarios coherent. [FIELD_MAPPING.md](FIELD_MAPPING.md) records preservation and changes; [CLINICAL_CONTEXT.md](CLINICAL_CONTEXT.md) identifies the sources and interpretation limits.

| Outpatient capability | Treatment occurrences |
|---|---|
| Thyroid replacement follow-up | 52 |
| Well-child visits | 2 |
| Acne care | 53 |
| Psychotherapy | 52 |
| Skin-biopsy evaluation | 52 |

## Supplemental pediatric cases

Patients 501 and 502 are newly authored fictional identities. All 500 source patients retain their original birth dates. These visits illustrate caregiver involvement and preventive documentation; they do not assert a complete pediatric chart or vaccination schedule.

| PatientID | Patient | Birth date | Visit | Visit date | Contact | Relationship | Recorded outcome |
|---|---|---|---|---|---|---|---|
| 501 | Ava Morgan | 2015-05-14 | 570 | 2023-09-12 | Leah Morgan | Parent | Growth, school participation, sleep, and immunization documentation reviewed with caregiver; follow-up plan recorded. |
| 502 | Noah Rivera | 2010-02-23 | 571 | 2023-09-19 | Mateo Rivera | Parent | Growth, school participation, sleep, and immunization documentation reviewed with caregiver; follow-up plan recorded. |

## Synthetic patterns and snapshot timing

All 24 infected stays last 12 days, detection is on day 6, return gaps cycle through selected boundary values, and some outcomes repeat. These deliberate patterns make checks reproducible; they are not estimates of clinical frequencies or recovery times. Falls cases cover adults of different ages, without claiming a typical geriatric case mix. Hospitalization care metrics and IsolationType are discharge-time snapshots, not admission assessments or a time series. Query 06 includes only completed stays by the cutoff. See [REPORTING.md](REPORTING.md) for date and missing-value policies.
