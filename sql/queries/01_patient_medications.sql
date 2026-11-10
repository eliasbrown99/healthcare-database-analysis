-- Distinct medication/effect pairs from dated orders on/before :as_of.
-- Unknown order dates are excluded; run_queries.py reports the excluded count.
SELECT DISTINCT p.PatientID,m.MedicationName,s.EffectName
FROM Patient p JOIN Encounter e USING(PatientID)
JOIN PatientTreatment t USING(EncounterID)
JOIN MedicationOrder o USING(PatientTreatmentID)
JOIN Medication m USING(MedicationID)
LEFT JOIN MedicationSideEffect ms USING(MedicationID)
LEFT JOIN SideEffect s USING(SideEffectID)
WHERE p.PatientID=:patient_id AND o.OrderDate<=:as_of
ORDER BY m.MedicationName,s.EffectName;
