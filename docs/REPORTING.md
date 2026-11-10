# Reporting dates and missing values

`run_queries.py --as-of YYYY-MM-DD --patient-id N` binds one inclusive event-date cutoff. These reports query the current database filtered by recorded event dates. They cannot reconstruct exactly what a clinician knew at an earlier time: narrative edits and care-team changes are not versioned. They are retrospective educational reports, not live clinical decision support.

| Query | Included records and cutoff |
|---|---|
| 01 Patient medications | Selected patient's orders with known OrderDate on/before cutoff; distinct medication/catalog-effect pairs, not a count of administered doses |
| 02 Average stay | Completed inpatient encounters with EndDate on/before cutoff; calendar-day difference, counted once per stay |
| 03 Infection distribution | HospitalAcquired=1 episodes detected on/before cutoff; denominator is episodes, not patients or stays; percentages may have rounding differences |
| 04 Medication order counts | Dated orders on/before cutoff; all catalog medications remain visible, including zero counts |
| 05 Readmission flag | Discharges with a full 30-day observation window; subsequent observed inpatient admission within 0–30 days; includes planned returns |
| 06 High-falls-risk review | Completed inpatient discharge snapshots by cutoff with FallsRisk >=7; not a list of currently admitted patients |
| 07 Patient timeline | Treatments started by cutoff; future treatment completion dates/outcomes and future discharge fields hidden; medication lists use only dated orders by cutoff |
| 08 Orders by prescriber | Dated orders by cutoff with known PrescribingPhysicianID; responsibility for treatment does not imply prescribing |
| 09 Return review | Same follow-up window as 05, returning only 0–30-day returns; planned/unplanned status comes from the return encounter; unknown remains NULL |
| 10 Infection follow-up | Episodes detected by cutoff; resolution later than cutoff is hidden and treated as not yet documented; unresolved cases sort first |

Unknown OrderDate remains permitted for incomplete imports. Queries 01, 04, 07, and 08 exclude it because an unknown date cannot be assigned to a reporting period. `results/report_context.json` states the cutoff, selected patient, total undated orders excluded across the database, and dated orders excluded from query 08 because the prescriber is unknown. The current scenarios have no such exclusions; tests explicitly cover both. These counters describe the current registry, not an independently dated event cohort.

NULL end dates represent open episodes. Unknown care metrics are not silently changed to zero. Missing resolution documentation does not establish active infection. Infection resolution may legitimately be recorded after discharge; infection detection must occur during the recorded stay in this prototype. Post-discharge detection would need a broader surveillance model.

Current narrative notes may mention later follow-up even when an earlier event-date cutoff is selected. The timeline masks completion-dependent fields, but no full historical chart reconstruction is claimed. Care metrics and isolation are discharge snapshots, which is why query 06 waits for a completed stay.
