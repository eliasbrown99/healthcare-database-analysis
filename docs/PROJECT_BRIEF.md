# From a database relationship to a reporting rule

Healthcare database project · Elias Brown

## Why the patient–encounter relationship matters

A hospital stay should belong to one patient even if no treatment has been recorded yet. In the original Access database, ownership had to be inferred through treatment rows. That produced two problems: 159 of 200 stays were linked to multiple patients, and seven had no treatment from which to infer an owner.

The revised schema stores the patient on the encounter itself. Treatment records refer to that encounter, so they do not carry a second, potentially conflicting patient assignment. Inpatient-specific details are stored separately from the information shared by all visits.

## What changed in the reports

| Reporting problem | Revised approach |
|---|---|
| Joining several treatments to one stay can multiply the stay count. | Count completed encounters once when calculating average stay. |
| Several physicians can be associated with the same treatment. | Record the medication prescriber separately from treatment participation. |
| A return admission can fall just inside or outside a reporting window. | Apply a defined 0–30-day interval after discharge and require sufficient follow-up. |

The worked cases include a same-day return, a return at exactly 30 days, and one at 31 days. The first two qualify under this project's definition; the third does not. Planned returns are identified in the worklist so that an included return is not automatically described as avoidable.

[Inspect the worked cases and outputs](SCENARIOS.md)

## How the design can be checked

The schema contains ownership and date constraints. The validation tests exercise invalid inserts and updates as well as legitimate corrections. The patient timeline is checked for duplicate rows caused by multiple physician or medication associations. A clean rebuild compares the generated database and reporting artifacts with the saved version.

These checks establish specific behavior. They do not establish completeness for a production clinical system. The reporting date filters recorded events, but the database does not version all narrative edits and therefore cannot reconstruct everything that was known on a past date.

## Original work and later extensions

Elias designed the original healthcare database. The original coursework included Brandon Weis, whose primary documented contribution was query work; Elias's primary documented implementation contribution was synthetic data generation. The later audit, Python/SQLite rebuild, scenarios, and checks are AI-assisted extensions of that work.

The revised scenarios are newly authored fictional events, not recovered histories from the original inconsistent relationships. Original source records remain separately preserved. The project supports review of database design and SQL behavior, not a claim about patient outcomes.

[Design and dictionary](DESIGN.md) · [Validation rules](VALIDATION.md) · [Reporting definitions](REPORTING.md) · [Run the project](../PROJECT_GUIDE.md#run-or-edit-it-without-access)
