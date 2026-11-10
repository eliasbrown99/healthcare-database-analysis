-- Unit = recorded hospital-acquired infection episodes, not unique patients.
WITH counts AS (
 SELECT it.TypeName,COUNT(*) AS Episodes FROM HospitalInfection hi
 JOIN InfectionType it USING(InfectionTypeID)
 WHERE hi.HospitalAcquired=1 AND hi.DetectedDate<=:as_of GROUP BY it.TypeName
)
SELECT TypeName,Episodes,ROUND(100.0*Episodes/NULLIF(SUM(Episodes) OVER(),0),2) AS Percent
FROM counts ORDER BY TypeName;
