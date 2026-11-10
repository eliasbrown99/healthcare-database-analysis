# Where to see the validation rules

SQLite stores enforcement rules in SQL definitions. A database explorer may display columns without displaying all their constraints. The absence of a visible Access-style Validation Rule box does not mean the rules are absent.

## Inspect the open database

Run [inspect_validation.sql](../sql/inspect_validation.sql), one statement at a time if needed. Its main query is:

```sql
SELECT type, name, tbl_name, sql
FROM sqlite_schema
WHERE type IN ('table', 'trigger') AND name NOT LIKE 'sqlite_%'
ORDER BY tbl_name, type, name;
```

Expand the SQL result cell. Table definitions contain CHECK, NOT NULL, UNIQUE, PRIMARY KEY, and REFERENCES. Trigger definitions contain checks that compare related rows. To inspect just the hospitalization table:

```sql
SELECT sql FROM sqlite_schema
WHERE type='table' AND name='Hospitalization';
```

The same definitions are readable in [schema.sql](../sql/schema.sql), which is used to build the database. The source file and database definitions agree when you rebuild from that file. Editing the SQL file alone does not change a database already open in VS Code.

## Access-to-SQLite examples

| Original intent | SQLite implementation | Meaning |
|---|---|---|
| FallsRisk and ADLScore between 1 and 10 | CHECK with integer-type and range tests | NULL allowed; fractional and out-of-range scores rejected |
| Required treatment type | NOT NULL REFERENCES Treatment | A valid treatment type must be supplied |
| Required dosage | NOT NULL plus trimmed-length CHECK | Null, empty, and space-only strings rejected |
| Referenced patient must exist | REFERENCES Patient | Checked when foreign keys are enabled on the connection |
| At least one physician per treatment | Required ResponsiblePhysicianID | One responsible physician always exists; additional physicians are optional |
| Treatment dates fit the visit | Treatment and encounter insert/update triggers | Invalid child edits and parent-date edits rejected |
| Medication order date fits its visit | Order, treatment-move, and encounter-date triggers | A recorded order date cannot move outside the associated encounter |
| Medication errors represent a count | Nonnegative integer CHECK | Unknown may be NULL; negative/fractional counts rejected |

For example:

```sql
FallsRisk INTEGER CHECK(
  FallsRisk IS NULL OR
  (typeof(FallsRisk)='integer' AND FallsRisk BETWEEN 1 AND 10)
)
```

A null value means unknown, not zero. The 1–10 scores preserve the project's scale; they are not labeled as a recognized clinical assessment instrument.

## Connection-level foreign keys

Run `PRAGMA foreign_keys;` on the actual connection used for editing. `1` means enabled; `0` means disabled. Use `PRAGMA foreign_keys=ON;` outside an active transaction and verify again. An extension may use separate connections for its SQL runner and table editor, so verify its connection settings rather than assuming one tab controls every editing surface.

`PRAGMA foreign_key_check;` lists existing violations even when enforcement was disabled. An empty result means none were found. `PRAGMA integrity_check;` should return `ok` but does not substitute for business-rule checks.

## Python checks are a separate layer

`python3 scripts/validate_demo.py` checks encounters before birth, overlapping inpatient stays, missing inpatient subtype records, infection detection dates outside a stay, redundant lead/additional physician assignments, treatment/order dates, foreign keys, and database integrity.

Birth-date changes, inpatient overlaps, infection dates, and duplicate responsible/additional assignments now have SQL triggers as well as independent validator checks. Required inpatient details are checked at transaction commit. Validator failure tests deliberately disable enforcement only in disposable fixtures to prove the second layer detects corrupted imports. [DESIGN.md](DESIGN.md) lists the enforcement layer for each rule.

## Safely demonstrate a rejected edit

Use a disposable copy of the database. In a transaction, try `UPDATE Hospitalization SET FallsRisk=11 WHERE EncounterID=1;`. SQLite should reject it with a CHECK constraint error. Roll back afterward. The automated tests use temporary databases and deliberately attempt invalid values, orphan references, and invalid date edits without touching the portfolio database.

## Required hospitalization details and valid corrections

In SQLite 3.31+, `Encounter.RequiredHospitalizationID` is generated automatically. Do not enter or edit it. It points to Hospitalization only for inpatient encounters, using a deferred foreign key. Both rows must exist when the transaction commits. A table editor that commits each row separately cannot insert an inpatient encounter and its details in two independent saves; use its SQL runner with one transaction.

Run this self-contained demonstration only on a disposable copy. The unused ID 900001 illustrates insertion, type correction, and cleanup:

```sql
PRAGMA foreign_keys=ON;
BEGIN;
INSERT INTO Encounter(EncounterID,PatientID,EncounterType,StartDate,EndDate)
VALUES(900001,501,'inpatient','2024-01-10','2024-01-11');
INSERT INTO Hospitalization(EncounterID) VALUES(900001);
COMMIT;

BEGIN;
DELETE FROM Hospitalization WHERE EncounterID=900001;
UPDATE Encounter SET EncounterType='outpatient',AdmissionType=NULL,DischargeDisposition=NULL
WHERE EncounterID=900001;
COMMIT;

DELETE FROM Encounter WHERE EncounterID=900001;
```

Deleting just the detail row and committing while the encounter remains inpatient fails. On any failed commit, use `ROLLBACK` or repair the transaction before retrying. A full deletion of both rows succeeds after other referencing rows have been explicitly removed. Tests cover failed partial deletion, both directions of type correction, and complete deletion.

`PRAGMA table_xinfo('Encounter');` exposes the generated column; `table_info` omits it. All project write scripts use `scripts/database.py`, which enables and verifies foreign keys. GUI applications must configure their own connections. The defensive hospitalization-type trigger also rejects a missing encounter when FK enforcement is off, but this does not replace foreign keys for the rest of the schema.
