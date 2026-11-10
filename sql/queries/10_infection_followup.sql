-- NULL resolution means resolution has not been documented, not proof of active infection.
SELECT e.PatientID,p.FirstName,p.LastName,h.EncounterID,i.TypeName,
       h.Organism,h.DetectedDate,
       CASE WHEN h.ResolvedDate<=:as_of THEN h.ResolvedDate END AS ResolvedDate,
       h.ClinicalNote,CASE WHEN e.EndDate<=:as_of THEN e.FollowUpPlan END AS FollowUpPlan,
       CASE WHEN h.ResolvedDate IS NULL OR h.ResolvedDate>:as_of
            THEN 'Resolution not documented by reporting date' ELSE 'Resolution documented' END AS FollowUpStatus
FROM HospitalInfection h JOIN InfectionType i USING(InfectionTypeID)
JOIN Encounter e USING(EncounterID) JOIN Patient p USING(PatientID)
WHERE h.DetectedDate<=:as_of
ORDER BY CASE WHEN h.ResolvedDate<=:as_of THEN 1 ELSE 0 END,h.DetectedDate,h.HospitalInfectionID;
