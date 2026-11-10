-- Mean completed-stay length, measured in calendar days; no treatment join.
SELECT COUNT(*) AS CompletedStays,
       ROUND(AVG(julianday(e.EndDate)-julianday(e.StartDate)),3) AS MeanDays
FROM Encounter e JOIN Hospitalization h USING(EncounterID)
WHERE e.EndDate IS NOT NULL AND e.EndDate<=:as_of;
