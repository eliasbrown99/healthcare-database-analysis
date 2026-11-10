-- Run statements separately if your editor only displays one result set.
-- A result of 1 means this connection enforces foreign keys. Enable outside a transaction.
PRAGMA foreign_keys;

-- CHECK, NOT NULL, UNIQUE, PRIMARY KEY, and REFERENCES appear in the table SQL.
-- Triggers implement rules involving more than one row/table.
SELECT type,name,tbl_name,sql
FROM sqlite_schema
WHERE type IN ('table','trigger') AND name NOT LIKE 'sqlite_%'
ORDER BY tbl_name,type,name;

PRAGMA foreign_key_list('PatientTreatment');
PRAGMA foreign_key_list('MedicationOrder');
PRAGMA foreign_key_check;
PRAGMA integrity_check;

-- Generated enforcement columns are visible here (not in table_info).
PRAGMA table_xinfo('Encounter');
