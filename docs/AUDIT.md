# Audit of the original healthcare database

## Scope and evidence

This review compares `FinalProject1(1).accdb`, `INSC Final(1).docx`, and `project.docx`. The supplied Word report is the evidence for the intended outcomes and individually completed queries/forms/reports. The database was read without modifying it. Table data, catalog metadata, relationships, and field properties were exported using a Python Access reader, then inspected and queried in SQLite.

The assignment asks students to "Try to stay with 3NF" and justify deliberate denormalization. It also calls for a needs assessment, documented business rules, ER modeling, relational conversion, domains and integrity constraints, an Access prototype, illustrative test cases, forms/reports, and project participation records. The score of 25/30 does not identify which shortcomings caused deductions; this review cannot reconstruct the instructor's grading rationale.

All data was generated, and Elias authorized regenerating relationships and dates to make the demonstration consistent. Original rows remain in `data/source/`; new scenarios are isolated in the revised database.

## What was already working

The original design separated patients, physicians, treatments, and medications and used association tables for many-to-many relationships. It contained eight user tables and seven enforced relationships. In the supplied records, all seven relationships have zero foreign-key orphans and all eight tables have zero duplicate primary keys. The physician/treatment association has a composite key, preventing the same pair from being inserted twice.

The falls-risk and ADL fields actually have `>=1 And <=10` validation rules. The 631 linked inpatient treatments and 369 outpatient treatments are consistent with the stored InPatient flags. Admission/discharge pairs and treatment start/end pairs are internally ordered, even though many treatment intervals disagree with their associated stay.

These are meaningful accomplishments. The principal weakness is that the database enforces some local relationships without fully expressing the business rules across those relationships.

## Findings and consequences

### 1. A hospitalization has no patient owner

`Hospitalization.PatientCareID` identifies a hospital stay. There is no PatientID in that table. Patient identity can only be inferred by following the stay to PatientTreatment and then Patient.

This fails in two ways: 159 of 200 stays lead to more than one distinct patient, and seven stays have no treatment from which to infer any patient. Stay 162, for example, connects to patients 213, 346, and 460. The remaining 34 stays lead to exactly one patient.

Every referenced ID can exist and still represent the wrong relationship. A foreign key proves that a record exists, not that two valid records describe the same person's care. Generated data made this weakness visible; the model permitted it.

**Revision:** Encounter has a required PatientID. Hospitalization is an inpatient subtype of Encounter. Every PatientTreatment refers to an Encounter and obtains its patient through that encounter. It cannot independently name a contradictory patient.

### 2. Two queries join IDs with different meanings

The readmission and falls-risk queries use a join equivalent to:

```sql
Patient.PatientID = Hospitalization.PatientCareID
```

Those are two independent numbering sequences. Patient 42 is not automatically the patient in hospital stay 42. The query can produce plausible names and row counts while pairing them incorrectly. This is a semantic SQL error, even though the syntax executes successfully.

**Revision:** Join Patient to Encounter on PatientID and Hospitalization to Encounter on EncounterID. A chart based on the wrong join would merely present the error more attractively.

### 3. Treatment dates are independent of stay dates

Of 631 treatment records with a stay link, 555 start before, end after, or otherwise fall outside that stay's interval. Zero reversed intervals does not resolve this: a treatment can have an internally valid start/end pair and still occur outside the correct episode.

**Revision:** Generate coherent encounters first, then treatments inside their bounds. SQLite triggers reject invalid treatment inserts/updates and reject encounter-date changes that would invalidate existing treatments. Date checks reject impossible calendar dates as well as reversed intervals.

### 4. A many-to-many bridge does not guarantee participation

The business rules require every treatment to involve at least one physician. In the original data, 144 of 1,000 treatments have no PhysicianTreatment row. Foreign keys in the bridge only validate rows that exist; they do not force every treatment to have a child row.

**Revision:** Every treatment has one required ResponsiblePhysicianID. Additional clinicians use PhysicianTreatment. This is an explicit design assumption that one physician owns responsibility for an event. A system allowing several equally responsible physicians would need a different assignment model and transaction-level participation enforcement.

### 5. Required text still allowed empty strings

All 3,000 medication associations contain an empty Dosage string. The actual Access field has both Required=True and AllowZeroLength=True. These settings permit an empty string while forbidding a null value.

**Revision:** Dosage and Frequency require `NOT NULL` and `length(trim(value)) > 0`. Version 2 supplies explicitly indicated example orders with their own dose text and a recorded prescriber. The original source still does not support analyses of doses administered or individual prescribers; the new prescriber identity is authored scenario data.

### 6. Metadata documentation differs from implementation

| Field | Report description | Actual Access metadata / data | Implication |
|---|---|---|---|
| Patient.EmergencyContact | Text length 50 | Length 15; all 500 values are `Emergency Conta` | Data was truncated; increasing length cannot recover the missing content |
| PatientTreatment.TreatmentID | Required | Required=False | Database permits an unspecified treatment type |
| HospitalAcquiredInfection | Text in the attribute documentation | Boolean | Data dictionary does not describe the implemented domain |
| Infection | Text length 5 | Length 50 | Documentation understates accepted values |
| MedicationErrors | Numeric count concept | Floating-point storage | A count should disallow fractional and negative values |

Other length/name discrepancies exist in the original report; the executable revised schema is the authority for the new model. MedicationErrors becomes a nullable nonnegative integer. Unknown values remain null rather than being silently relabeled as zero.

### 7. Infection and side-effect fields limit analysis

One Infection field per hospitalization can represent only one recorded infection type. It cannot naturally store multiple episodes, each with its own detection/resolution dates. The original labels also mix organisms, syndromes, and surveillance-style categories, so they do not form a consistent clinical taxonomy.

**Revision:** HospitalInfection stores one episode per row. Version 2 uses named episode categories and records the organism separately. These are authored cases with fictional adjudication, not inferred classifications of the original mixed labels. Original labels remain in the source exports.

SideEffects contains comma-separated descriptions. If those are opaque narrative notes, a comma alone does not make a field non-atomic. If effects are intended to be independently searched, counted, and linked—as in this portfolio—separate effect rows and association tables are clearer. The rebuild splits the source strings and deduplicates labels case-insensitively; this is a lexical transformation, not clinical terminology validation.

## What third normal form means here

Normalization concerns dependencies between facts. It does not establish clinical plausibility, complete documentation, or correct SQL.

1. **First normal form:** Give each field one value at the intended level of analysis, with no repeating groups. Separate independently queryable side effects into rows.
2. **Second normal form:** Non-key attributes must depend on the whole candidate key, not just one component of a composite key. In PhysicianTreatment, Role describes the physician's role for that particular treatment, not a permanent attribute of the physician.
3. **Third normal form:** Avoid non-key attributes depending on other non-key determinants. More formally, for every nontrivial functional dependency X → A, X should be a superkey or A a prime attribute. Under the intended rule that one stay has one patient, PatientCareID → PatientID. Keeping both as independent attributes in every treatment invites inconsistent copies of the same fact.

The original data violates the intended one-patient-per-stay rule, so that dependency is a business rule rather than a pattern that happens to hold in the rows. The revised design records it once in Encounter. PatientTreatmentID → EncounterID → PatientID is resolved across tables by omitting PatientID from PatientTreatment.

The original InPatient flag is also derivable from encounter/stay membership. Storing it creates an opportunity for disagreement, even though no disagreement occurred in this dataset. A stored Readmission boolean is not automatically a 3NF violation, but without a defined window and reliable derivation it is hard to defend or update. The rebuild derives both concepts.

A surrogate ID does not by itself prove 3NF. The revised model is designed for 3NF under its documented dependencies, including one specialty per physician, one encounter per treatment occurrence, and separate contact components and addresses treated as display values. More demanding business requirements could require additional tables.

The Treatment catalog is a regular entity, not an associative entity merely because it participates in several relationships. PatientTreatment represents an occurrence; PhysicianTreatment and the side-effect bridges are associations. Precise entity labels help explain the model, though a mislabeled box alone does not corrupt data.

## Review of the original report queries

| Report query | Reproduced result | Assessment |
|---|---|---|
| Q1: medications for patient 212 | 10 distinct medications, matching the report | Valid historical medication lookup through treatment associations. Does not establish current use. |
| Q2: average length of stay | 58.635 days | Arithmetic matches. It is a mean per stay, not per patient. The long synthetic stays do not establish a realistic hospital benchmark. |
| Q3: hospital-acquired infection distribution | 24 positive stays with known labels across eight categories | Counts those stay rows, not unique patients or multiple infection episodes. A distribution among infections is different from an infection rate among all stays. |
| Q4: medication popularity | 3,000 order associations; Warfarin 168, Furosemide 164, Albuterol 160 lead | Counts associations/orders. Cannot identify medication administrations or individual prescribers. |
| Second Q4: readmissions | Eight stored flags | Invalid patient join; stored flag does not calculate a 30-day interval. |
| Q5: falls risk ≥7 | 84 hospitalizations | Risk threshold count matches, but patient identity is assigned through the invalid join. |

The duplicate Q4 label is a documentation issue. The full medication list, infection distribution, and counts are in `source_audit_results.json`. The source SQL was interpreted and its logic reproduced against exported rows; this is not a claim that the original Access GUI was executed.

The new readmission query sequences inpatient encounters per patient, computes the time from discharge to the next admission, and requires 30 days of follow-up by an explicit reporting date. Same-day returns count; outpatient visits do not. A visit at 30 days counts, one at 31 does not. The dataset assumes complete observation within its synthetic world; real external-hospital encounters and measure-specific exclusions would require additional data.

## Assignment coverage and evidence limits

| Requirement area | Evidence and conclusion |
|---|---|
| Mini-world and business rules | Present in the final report; several rules were incompletely enforced |
| ER and relational design | Present; major gap is the missing patient/stay ownership relationship |
| Entities, attributes, domains, keys | Documented; some entity classifications and field specifications need correction |
| Normalization | Claimed in the report; dependency-based justification needs strengthening |
| Access prototype and integrity | Eight tables, keys, and enforced relationships are present; cross-table rules are incomplete |
| Queries, forms, reports | Elias confirms these were completed individually and compiled into the Word submission; the report is the supplied evidence |
| Saved executable Access objects | This supplied database contains no saved query/form/report objects. That limits reproduction from this file alone; it does not show the work was never done |
| Testing | Final report contains query results; systematic negative and boundary tests strengthen the portfolio |
| Participation and instructor meeting | Report describes contributions; actual meeting attendance and grading cannot be established by this technical audit |

## Revised scenario versions (November 2026)

The original source findings above are unchanged. The first working rebuild simplified clinical examples more than necessary. Version 2 retains all original treatment and medication catalog entries, restores StandardDosage as catalog reference text, and replaces generic outcomes, numbered infection categories, and uniform roles with explicit worked cases.

Version 3 has 502 patients (500 preserved plus two pediatric examples), 100 physicians, 200 inpatient stays, 371 outpatient visits, 1,276 treatment occurrences, and 302 selected medication orders. One hundred sixty patients have an initial inpatient stay; 40 have a second. All 160 have outpatient follow-up, and 209 other original patients have outpatient chronic-care or procedural examples. Two supplemental patients have preventive pediatric visits. The other registry patients have no encounters in the selected scenario period.

The new cases preserve the concepts of falls risk, ADL, diet, activity assistance, care-plan adherence, medication errors, isolation, treatment outcomes, treatment frequency, physician roles, and infections. Values are authored to fit scenarios rather than transferred arbitrarily. Medication orders now explicitly identify a prescriber and indication. All original rows remain in the source export and snapshot. See [FIELD_MAPPING.md](FIELD_MAPPING.md) for the full comparison and [SCENARIOS.md](SCENARIOS.md) for actual worked results.

The original aggregate results in this audit are not the expected outputs of the new scenario database. The original and scenario versions answer the same types of questions over different synthetic events.

## Validation and remaining scope

The revised database passes SQLite foreign-key and integrity checks, cross-table validation, and the expanded behavior/acceptance test suite recorded in [verification_log.json](verification_log.json). These cover blank doses, score ranges, required physicians, unknown prescribers, treatment/order chronology, parent edits, readmission boundaries, and avoiding duplicate counts when joining child records. Worked-case checks verify that the original catalog names remain and that narrative timelines retain one row per treatment.

SQL constraints/triggers enforce the modeled relationships and chronology, with required inpatient details checked at commit. Independent Python checks detect violations in stored data, including imports made with enforcement disabled. [VALIDATION.md](VALIDATION.md) shows how to inspect the actual definitions in a SQL editor. [DESIGN.md](DESIGN.md) distinguishes the enforcement layers.

This remains an educational prototype. It has selected example medication orders and abbreviated clinical narratives, not a complete clinical chart, independently validated prescribing decisions, or formal surveillance/quality-measure implementation. [CLINICAL_CONTEXT.md](CLINICAL_CONTEXT.md) documents the clinical grounding and limits.

The strongest portfolio story is the ability to identify a silent reporting error, fix its underlying model, and demonstrate the consequences with coherent cases and reproducible tests.
