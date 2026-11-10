-- Require a full 30-day observation window after discharge.
-- Same-day return counts. Planned returns are included; query 09 labels them. Transfers are not modeled.
-- This is an educational definition, not a CMS/HEDIS measure.
SELECT r.EncounterID,r.PatientID,p.FirstName,p.LastName,r.DischargeDate,
       CASE WHEN r.NextAdmitDate<=:as_of THEN r.NextAdmitDate END AS NextObservedAdmission,
       CASE WHEN r.NextAdmitDate<=:as_of THEN r.DaysToNextAdmission END AS DaysToNextAdmission,
       CASE WHEN r.NextAdmitDate<=:as_of AND r.DaysToNextAdmission BETWEEN 0 AND 30 THEN 1 ELSE 0 END AS Readmitted30Days
FROM InpatientReadmission r JOIN Patient p USING(PatientID)
WHERE r.DischargeDate IS NOT NULL AND date(r.DischargeDate,'+30 days')<=:as_of
ORDER BY r.PatientID,r.AdmitDate;
