# Revised design

## Grain, keys, and dependencies

The grain states what one row means. A field belongs in a table when it describes that row's fact. IDs distinguish occurrences; unique catalog names are additional candidate keys under this prototype's naming assumptions.

| Table | One row represents | Key and dependency reasoning |
|---|---|---|
| Patient | One synthetic person | PatientID determines stored demographics; names and emails are not assumed unique |
| Physician | One synthetic physician | PhysicianID determines name, email, and one specialty; multiple specialties would require an association table |
| Encounter | One patient's care episode | EncounterID determines PatientID, type, and dates; a patient can have many episodes |
| EncounterPatientChange | One recorded reassignment of an encounter | ChangeID determines encounter, previous/new patient, and UTC change timestamp |
| Hospitalization | Inpatient-specific details for an encounter | EncounterID is both PK and FK; admission/discharge dates are obtained from Encounter |
| Treatment | One catalog treatment type | TreatmentID and unique TreatmentName identify its description |
| PatientTreatment | One occurrence of a treatment in an encounter | PatientTreatmentID determines encounter, treatment type, lead physician, dates, and occurrence attributes |
| PhysicianTreatment | An additional physician's participation in a treatment | Composite (PhysicianID, PatientTreatmentID) determines Role |
| Medication | One catalog medication | MedicationID and unique MedicationName identify the item |
| MedicationOrder | One recorded medication order for a treatment occurrence | MedicationOrderID determines treatment, medication, dose, frequency, prescriber, date, route, and indication; repeated orders are permitted |
| SideEffect | One effect label | SideEffectID and unique EffectName identify the label |
| MedicationSideEffect | One catalog medication/effect association | Composite key; no non-key attributes |
| TreatmentSideEffect | One catalog treatment/effect association | Composite key; no non-key attributes |
| InfectionType | One synthetic infection category | InfectionTypeID and unique TypeName identify the category |
| HospitalInfection | One recorded infection episode during a hospitalization | HospitalInfectionID determines stay, category, detection date, hospital-acquired flag, and optional resolution date |

PatientTreatment does not repeat PatientID. The encounter already determines the patient. Catalog side effects describe possible effects, not adverse events observed in a specific patient. One patient's actual adverse events would need a separate event table.

StandardDosage is retained as the source catalog's reference text, not a clinical rule. MedicationID determines that reference text; a particular order determines its own dose, frequency, route, indication, date, and prescriber. The two are distinct facts. No constraint requires an order to copy the catalog reference.

## Cardinalities and optionality

Every encounter belongs to exactly one patient. A patient can have zero or many encounters. An inpatient encounter must have one Hospitalization row; an outpatient encounter must have none. The subtype key enforces at most one detail row. Encounter.RequiredHospitalizationID is a virtual generated column: it equals EncounterID for inpatient visits and NULL for outpatient visits. Its deferred foreign key requires the detail row at transaction commit, without storing a second independent fact. Insert the encounter and its details in one transaction. The validator independently checks saved rows.

Every treatment occurrence belongs to exactly one encounter, one treatment type, and one responsible physician. Each of those parent records can have zero or many treatment occurrences. Additional physicians and medication orders are optional and can be numerous. TreatmentCareTeam combines the responsible physician and additional assignments without inferring prescribing identity. MedicationOrder.PrescribingPhysicianID is a separate optional FK; every worked order supplies it. Unknown prescribing identity remains possible for other imports. No medication-order minimum is assumed: many treatments legitimately require no medication.

Each medication/effect and treatment/effect pair can occur once in its catalog association table. A hospitalization can have zero or many infection episodes. An infection episode has exactly one category; multiple concurrent episodes are supported. The current Organism field is a single descriptive result for an episode. Multiple organisms per episode would need a separate association. Care metrics and IsolationType are discharge-time snapshots, not admission values or a series of assessments. Query 06 waits until discharge before presenting them.

The diagrams show selected columns and maximum relationship cardinalities. They are explanatory views of the schema, not complete attribute dictionaries.

## Enforcement strategy

| Rule | Enforcement |
|---|---|
| Referenced patient, encounter, physician, treatment, medication, or category exists | Foreign keys; enable `PRAGMA foreign_keys=ON` for every write connection |
| Each row has its defined identity; catalog labels/pairs are unique | Primary and unique keys |
| Required names, role, dosage, and frequency are not blank | NOT NULL and trimmed-length checks |
| Dates are valid ISO calendar dates; end is not before start | CHECK constraints |
| FallsRisk and ADLScore are integers from 1 through 10 when supplied | Type/range CHECK constraints |
| MedicationErrors is a nonnegative integer when known | Type/range CHECK constraint; NULL means unknown |
| Flags are 0 or 1 when supplied | CHECK constraints |
| Hospitalization refers to an inpatient; type updates cannot strand the subtype | Insert/update triggers plus FK |
| Treatment dates fit the encounter, including later edits of either row | Insert/update triggers |
| Medication order dates fit the encounter, including later order, treatment-link, and parent-date edits | Insert/update triggers; validation also checks stored rows |
| Every inpatient has its subtype | Deferred FK on generated RequiredHospitalizationID; checked at COMMIT, plus independent validation |
| Encounter is not before birth, including patient reassignment or DOB changes | Encounter and patient triggers, plus validation |
| Inpatient stays do not overlap; same-day discharge/admission boundary is allowed | Encounter insert/update triggers, plus validation |
| Infection detection is within the stay, including parent-date changes | Infection/encounter triggers, plus validation |
| Lead is not repeated as an additional physician | Assignment and lead-update triggers, plus validation |
| Outpatient encounters have no inpatient admission/disposition values | CHECK constraint, plus validation |
| ResponsibleRole has an explicit value | NOT NULL/nonblank CHECK; no inferred default |
| Full database has no FK violations or structural corruption | Validation script with foreign_key_check and integrity_check |

The schema permits an infection's resolution after discharge, which may represent follow-up. The checks require resolution on/after detection. They do not infer whether an infection is truly hospital acquired; that flag is synthetic input. The worked cases record resolution for some episodes and leave others without a documented resolution date.

The database is deliberately not claimed to prevent every cross-table error during arbitrary manual editing. Run the validation script after edits. Deletions do not cascade: foreign keys restrict deletion of referenced rows when enforcement is enabled. There is no automatic renumbering of identities.

Dates use day precision. Same-day stays have zero elapsed calendar days; these are not inclusive bed-day counts. Null encounter/treatment end dates represent open episodes. A closed encounter cannot contain an open-ended treatment. The prototype has one hospital and no time-zone or transfer model.

## Modeling choices and correction workflows

MedicationOrder belongs to a treatment occurrence, including a medication-review workflow. This preserves the original association's purpose and provides a recorded workflow context; the order's Indication states the clinical purpose. It does not mean that reconciliation itself caused a prescription. An operational prescribing system might attach orders directly to encounters and optionally link them to procedures or diagnoses; that broader workflow is not implemented here.

AdmissionType and DischargeDisposition apply only to inpatient encounters. They are NULL for outpatient visits, enforced by CHECK. VisitReason and FollowUpPlan still describe outpatient care. Keeping the nullable inpatient fields on Encounter is a documented convenience, not a non-key dependency.

Emergency contacts have separate name, relationship, and phone fields. Each patient currently has at most one contact; multiple contacts and independent contact identities would need an association table. Addresses remain display text rather than independently searchable address components.

Changing Encounter.PatientID is an explicit whole-episode identity correction: treatments, orders, and infection episodes continue to resolve to exactly one patient. DOB and overlap constraints apply to the new owner. An AFTER UPDATE trigger records old/new patient IDs and the UTC timestamp in EncounterPatientChange. That local history is not authenticated, tamper-proof, or a complete audit trail: it has no actor/reason field, and privileged database editors can change it. Real patient-data use would require authenticated permissions and a durable audit trail. Foreign keys preserve referenced history rows until explicitly removed; ordinary patient deletion cannot silently erase them.

Subtype corrections use one transaction: delete Hospitalization first (after any infection children), clear inpatient-only fields while changing EncounterType, then commit. For a full episode deletion, remove referencing orders, care-team rows, treatments, infection/history rows, the subtype, and finally the encounter in one transaction. A commit fails if an inpatient is left without details. No always-blocking subtype DELETE trigger is needed. [VALIDATION.md](VALIDATION.md) contains a runnable example.

SQLite 3.31+ is required for [generated columns](https://www.sqlite.org/gencol.html). [Deferred foreign keys](https://www.sqlite.org/foreignkeys.html#fk_deferred) check completed transactions. Every external write connection still needs foreign keys enabled; the project connection helper enables and verifies them. Constraints protect ordinary edits, not an administrator who disables enforcement or alters the schema.

## Indexes

Primary/unique keys index identities and catalog names. Additional indexes support encounters by patient/date, treatments by encounter, medication orders by treatment and prescriber, additional physicians by treatment, and infections by encounter. They target the demonstrated joins and reports; no performance claim is made from this small dataset.

## Implementation dictionary

The following dictionary is generated from `PRAGMA table_xinfo` (including generated columns) and `PRAGMA foreign_key_list`. `Required` includes primary-key identity requirements even where SQLite reports an INTEGER PRIMARY KEY's notnull flag as zero. The full CHECK constraints, indexes, and triggers are in [schema.sql](../sql/schema.sql).

<!-- GENERATED DICTIONARY -->

### Encounter

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| EncounterID | INTEGER | Yes | PK position 1 |
| PatientID | INTEGER | Yes | FK → Patient.PatientID |
| EncounterType | TEXT | Yes | — |
| StartDate | TEXT | Yes | — |
| EndDate | TEXT | No | — |
| VisitReason | TEXT | No | — |
| AdmissionType | TEXT | No | — |
| DischargeDisposition | TEXT | No | — |
| FollowUpPlan | TEXT | No | — |
| RequiredHospitalizationID | INTEGER | No | FK → Hospitalization.EncounterID; Generated; do not edit |

### EncounterPatientChange

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| ChangeID | INTEGER | Yes | PK position 1 |
| EncounterID | INTEGER | Yes | FK → Encounter.EncounterID |
| PreviousPatientID | INTEGER | Yes | FK → Patient.PatientID |
| NewPatientID | INTEGER | Yes | FK → Patient.PatientID |
| ChangedAt | TEXT | Yes | — |

### HospitalInfection

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| HospitalInfectionID | INTEGER | Yes | PK position 1 |
| EncounterID | INTEGER | Yes | FK → Hospitalization.EncounterID |
| InfectionTypeID | INTEGER | Yes | FK → InfectionType.InfectionTypeID |
| DetectedDate | TEXT | Yes | — |
| HospitalAcquired | INTEGER | Yes | — |
| ResolvedDate | TEXT | No | — |
| Organism | TEXT | No | — |
| ClinicalNote | TEXT | No | — |

### Hospitalization

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| EncounterID | INTEGER | Yes | PK position 1; FK → Encounter.EncounterID |
| FallsRisk | INTEGER | No | — |
| ADLScore | INTEGER | No | — |
| FallsOccurred | INTEGER | No | — |
| MedicationErrors | INTEGER | No | — |
| Diet | TEXT | No | — |
| CarePlanAdherence | INTEGER | No | — |
| ActivityLevel | TEXT | No | — |
| IsolationType | TEXT | No | — |

### InfectionType

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| InfectionTypeID | INTEGER | Yes | PK position 1 |
| TypeName | TEXT | Yes | — |

### Medication

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| MedicationID | INTEGER | Yes | PK position 1 |
| MedicationName | TEXT | Yes | — |
| StandardDosage | TEXT | No | — |

### MedicationOrder

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| MedicationOrderID | INTEGER | Yes | PK position 1 |
| PatientTreatmentID | INTEGER | Yes | FK → PatientTreatment.PatientTreatmentID |
| MedicationID | INTEGER | Yes | FK → Medication.MedicationID |
| Dosage | TEXT | Yes | — |
| Frequency | TEXT | Yes | — |
| PrescribingPhysicianID | INTEGER | No | FK → Physician.PhysicianID |
| OrderDate | TEXT | No | — |
| Route | TEXT | No | — |
| Indication | TEXT | No | — |

### MedicationSideEffect

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| MedicationID | INTEGER | Yes | PK position 1; FK → Medication.MedicationID |
| SideEffectID | INTEGER | Yes | PK position 2; FK → SideEffect.SideEffectID |

### Patient

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| PatientID | INTEGER | Yes | PK position 1 |
| FirstName | TEXT | Yes | — |
| LastName | TEXT | Yes | — |
| DateOfBirth | TEXT | Yes | — |
| Email | TEXT | No | — |
| EmergencyContactName | TEXT | No | — |
| EmergencyContactRelationship | TEXT | No | — |
| EmergencyContactPhone | TEXT | No | — |
| PhoneNumber | TEXT | No | — |
| Address | TEXT | No | — |
| Gender | TEXT | No | — |

### PatientTreatment

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| PatientTreatmentID | INTEGER | Yes | PK position 1 |
| EncounterID | INTEGER | Yes | FK → Encounter.EncounterID |
| TreatmentID | INTEGER | Yes | FK → Treatment.TreatmentID |
| ResponsiblePhysicianID | INTEGER | Yes | FK → Physician.PhysicianID |
| StartDate | TEXT | Yes | — |
| EndDate | TEXT | No | — |
| Outcome | TEXT | No | — |
| Compliance | TEXT | No | — |
| FrequencyTreatment | TEXT | No | — |
| ResponsibleRole | TEXT | Yes | — |

### Physician

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| PhysicianID | INTEGER | Yes | PK position 1 |
| FirstName | TEXT | Yes | — |
| LastName | TEXT | Yes | — |
| Specialty | TEXT | Yes | — |
| Email | TEXT | No | — |

### PhysicianTreatment

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| PhysicianID | INTEGER | Yes | PK position 1; FK → Physician.PhysicianID |
| PatientTreatmentID | INTEGER | Yes | PK position 2; FK → PatientTreatment.PatientTreatmentID |
| Role | TEXT | Yes | — |

### SideEffect

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| SideEffectID | INTEGER | Yes | PK position 1 |
| EffectName | TEXT | Yes | — |

### Treatment

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| TreatmentID | INTEGER | Yes | PK position 1 |
| TreatmentName | TEXT | Yes | — |
| Description | TEXT | Yes | — |

### TreatmentSideEffect

| Column | SQLite type | Required | Key/reference |
|---|---|---|---|
| TreatmentID | INTEGER | Yes | PK position 1; FK → Treatment.TreatmentID |
| SideEffectID | INTEGER | Yes | PK position 2; FK → SideEffect.SideEffectID |

