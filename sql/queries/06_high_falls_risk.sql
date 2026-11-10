-- Retrospective discharge snapshots for completed stays by :as_of.
SELECT e.EncounterID,p.PatientID,p.FirstName,p.LastName,e.StartDate AS AdmitDate,
       h.FallsRisk,h.FallsOccurred,h.ADLScore,h.ActivityLevel,h.Diet,
       h.CarePlanAdherence,e.VisitReason,e.DischargeDisposition,e.FollowUpPlan
FROM Hospitalization h JOIN Encounter e USING(EncounterID) JOIN Patient p USING(PatientID)
WHERE h.FallsRisk>=7 AND e.EndDate<=:as_of ORDER BY e.EncounterID;
