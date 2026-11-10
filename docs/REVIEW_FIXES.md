# Independent-review fixes (version 3)

The review confirmed the original audit totals and core relationship redesign, then identified one false scenario claim and gaps in enforcement, reporting, tests, and reproducibility. This revision addresses each finding without changing the original source exports.

| Review finding | Resolution | Verification |
|---|---|---|
| Well-child examples claimed but absent | Added two explicitly supplemental fictional pediatric patients and visits; preserved all original birth dates | Independent age, specialty, identity-preservation, and scenario-coverage tests; documentation generation refuses an absent capability |
| Inpatient details could be deleted | Generated conditional reference with a deferred FK requires details at commit | Missing-details failures and successful creation, type correction, and complete deletion tests |
| Infection dates could fall outside the stay | Triggers protect inserts, updates, and parent-date changes; resolution may follow discharge | Invalid insert/update/parent edits fail; valid later resolution passes |
| Overlapping stays and pre-birth encounters accepted | SQL triggers protect inserts, dates, patient reassignment, and DOB changes | Rejection tests plus independent corruption-detection tests |
| Foreign keys off on a new connection | Shared project helper enables/verifies FKs; GUI instructions remain explicit | Helper and orphan tests; defensive subtype trigger also rejects missing parents with FK off |
| Whole episode could be reassigned silently | Valid identity correction remains possible; old/new IDs and UTC timestamp recorded in EncounterPatientChange; birth/overlap rules still apply | Correction-history and consistent ownership tests; local history is explicitly not an authenticated clinical audit trail |
| CI regenerated files without detecting stale committed artifacts | CI tests committed artifacts, rebuilds in a disposable directory, compares text/schema/rows, and checks the working tree stayed clean | Artifact checker and drift regression tests; docs generation runs inside the clean rebuild |
| Validator failure paths and reports lacked tests | Every business-validator key is tested against an isolated corrupt fixture; treatment moves and reports 03/06/09/10 tested | Independent fixture expectations plus worked-scenario acceptance totals |
| Date cutoff and NULL order-date behavior differed | All ten reports have explicit cutoff policies; unknown-date/prescriber exclusions counted; future resolution dates hidden | Boundary, NULL, known/unknown prescriber, and timeline tests; REPORTING.md |
| Medication orders require a treatment workflow | Retained intentionally; workflow context is distinct from clinical indication | DESIGN.md explains the choice and limits; actual prescribing identity remains separate |
| Admission/disposition populated for outpatient visits | Outpatient values now NULL, enforced by CHECK | Rejection and validator tests |
| Contact information packed into display text | Name, relationship, and phone now separately queryable | Schema dictionary and rebuilt contact fields; original truncated values remain in source |
| Default responsible role could mislabel a physician | Removed default; every writer/fixture supplies an explicit role | Missing-role rejection test |
| Repeated synthetic patterns and unclear isolation timing | Patterns explicitly disclosed; care metrics/isolation defined as discharge snapshots; repeated procedure/assessment wording separated | Generated scenario documentation; completed-stay cutoff test |

The model remains a coursework/portfolio prototype. It does not implement authentication, clinical terminology validation, complete prescribing, serial assessments, post-discharge infection surveillance, or a versioned medical chart. No claim is made that its synthetic event frequencies represent real hospital performance.
