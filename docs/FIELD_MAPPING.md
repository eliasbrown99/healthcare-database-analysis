# What was preserved, moved, and changed

The original `.accdb` was not changed. `data/source/*.json` retains every exported original row, and the source snapshot reproduces its values. The editable scenario database is a new version, so preservation of a field's purpose must be distinguished from preservation of its old generated value.

| Original table/fields | Scenario version | Treatment of values |
|---|---|---|
| Patient: IDs, names, birth dates, gender, phone, address | Same fields | Retained; birth date stored as ISO date without a time component |
| Patient.Email | Email | Rewritten to reserved `example.invalid` addresses |
| Patient.EmergencyContact | EmergencyContactName, EmergencyContactRelationship, EmergencyContactPhone | Truncated placeholder replaced by separately queryable fictional contact details |
| Physician: ID, names, specialty | Same fields | Retained |
| Physician.Email | Email | Reserved fictional address |
| Treatment: ID, name, description | Same catalog | All 31 original entries retained; two missing initial letters in descriptions corrected; eight workflow types added |
| Medication: ID, name, StandardDosage | Same catalog | All 20 original entries retained verbatim; acetaminophen added |
| Medication/Treatment.SideEffects | SideEffect and two association tables | Original strings preserved in raw exports; labels split and deduplicated for queries; not independently clinically vetted |
| Hospitalization.PatientCareID | EncounterID and hospitalization subtype key | Same 1–200 numeric range now identifies newly authored visits; not a row-by-row historical repair |
| AdmitDate, DischargeDate | Encounter.StartDate, EndDate | Regenerated coherent dates |
| FallsRisk, ADLScore, Diet, FallsOccurred, MedicationErrors, CarePlanAdherence, ActivityLevel, IsolationType | Hospitalization fields | All concepts retained; values chosen to fit each case, not copied randomly |
| Readmit30Days | InpatientReadmission view and parameterized report | Derived from dates with an observation cutoff instead of copying the old flag |
| HospitalAcquiredInfection, Infection, InfectionResolved | HospitalInfection and InfectionType | New named episodes, detection/resolution dates, organism, and clinical note; original mixed labels preserved in source exports |
| PatientTreatment.PatientID and PatientCareID | EncounterID | Patient is determined by encounter; outpatient visits also have an encounter |
| PatientTreatment.InPatient | Encounter.EncounterType | Derived from encounter instead of duplicated |
| PatientTreatment.TreatmentID and dates | Same concepts | Regenerated to fit the visit and procedure/workflow |
| Outcome, Compliance, FrequencyTreatment | Same fields | Meaningful narrative outcomes, access/support notes, and case-appropriate frequencies replace generic text |
| PhysicianTreatment.Role | Additional Role plus ResponsibleRole | Clinician assignments regenerated; operating, assisting, consulting, anesthesia, treating, and discharge roles distinguished |
| PatientTreatmentMedication | MedicationOrder | Selected, explicitly indicated example orders replace arbitrary pairings; original 3,000 rows remain in source |
| Dosage, Frequency | MedicationOrder fields | Realistic example dose/frequency text rather than blank dose values; not automatic copies of a universal default |
| No original equivalents | Visit reason, planned/unplanned admission, disposition, follow-up, prescribing identity, order date, route, indication | Added to explain the cases and support reliable reporting |

## Changes from the first rebuild

The first rebuild preserved the source separately but simplified the working copy too aggressively: most treatment assignments changed, outcomes became generic text, roles became uniform, infection names became numbered categories, and the medication catalog lost its dose-reference field. Version 2 corrects those presentation losses while retaining the relationship fixes.

All original treatment and medication catalog names remain available. They need not all appear in the limited worked scenarios: a hospital's catalog can contain procedures and medications unused during a selected period. Original row counts and old query outputs are retained for the audit, not forced onto the new examples.

Original Access forms/reports remain evidence in the supplied Word document. The package supplies executable SQL reports and a GUI-editable SQLite database, but does not reproduce the original form layouts or turn the prototype into a complete clinical application.

## Independent-review revision (version 3)

All source JSON files and the source snapshot remain unchanged. Two additional fictional patients (501 and 502) provide actual pediatric examples; no original birth date was rewritten. Counts and scenario tables are generated from the rebuilt database. Contact components are now separate fields, outpatient admission/disposition values are NULL, and every responsible role must be explicit. EncounterPatientChange records whole-episode ownership corrections. RequiredHospitalizationID is a virtual enforcement column, not an independently stored clinical fact. See [REVIEW_FIXES.md](REVIEW_FIXES.md).
