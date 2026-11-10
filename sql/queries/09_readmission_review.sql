-- A review worklist, not a standardized performance measure or a causal model.
SELECT r.PatientID,p.FirstName,p.LastName,r.EncounterID AS IndexEncounter,
       r.DischargeDate,r.NextEncounterID,r.NextAdmitDate,r.DaysToNextAdmission,
       e.VisitReason AS ReturnReason,e.AdmissionType AS ReturnAdmissionType
FROM InpatientReadmission r JOIN Patient p USING(PatientID)
JOIN Encounter e ON e.EncounterID=r.NextEncounterID
WHERE date(r.DischargeDate,'+30 days')<=:as_of
  AND r.NextAdmitDate<=:as_of AND r.DaysToNextAdmission BETWEEN 0 AND 30
ORDER BY r.DischargeDate,r.PatientID;
