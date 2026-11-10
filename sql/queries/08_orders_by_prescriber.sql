-- Only dated orders by :as_of with a known prescriber; exclusions appear in report_context.json.
-- These records explicitly identify the prescriber; care-team membership is not a proxy.
SELECT p.PhysicianID,p.FirstName,p.LastName,p.Specialty,m.MedicationName,
       COUNT(*) AS SelectedOrderCount,COUNT(DISTINCT e.PatientID) AS DistinctPatients
FROM MedicationOrder o JOIN Physician p ON p.PhysicianID=o.PrescribingPhysicianID
JOIN Medication m USING(MedicationID)
JOIN PatientTreatment pt USING(PatientTreatmentID) JOIN Encounter e USING(EncounterID)
WHERE o.OrderDate<=:as_of
GROUP BY p.PhysicianID,p.FirstName,p.LastName,p.Specialty,m.MedicationID,m.MedicationName
ORDER BY SelectedOrderCount DESC,p.PhysicianID,m.MedicationName;
