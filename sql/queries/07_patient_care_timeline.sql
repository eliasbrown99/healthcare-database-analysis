-- One row per treatment occurrence. Pre-aggregate child tables to avoid multiplication.
WITH orders AS (
 SELECT PatientTreatmentID,group_concat(OrderText,'; ') AS SelectedMedicationOrders FROM (
  SELECT o.PatientTreatmentID,m.MedicationName || ' ' || o.Dosage || ' / ' || o.Frequency AS OrderText
  FROM MedicationOrder o JOIN Medication m USING(MedicationID)
  WHERE o.OrderDate<=:as_of ORDER BY o.MedicationOrderID
 ) GROUP BY PatientTreatmentID
), teams AS (
 SELECT PatientTreatmentID,group_concat(TeamText,'; ') AS CareTeam FROM (
  SELECT c.PatientTreatmentID,p.FirstName || ' ' || p.LastName || ' (' || c.Role || ')' AS TeamText
  FROM TreatmentCareTeam c JOIN Physician p USING(PhysicianID)
  ORDER BY c.PatientTreatmentID,c.Responsible DESC,c.PhysicianID
 ) GROUP BY PatientTreatmentID
)
SELECT e.PatientID,e.EncounterID,e.EncounterType,e.VisitReason,
       p.StartDate,CASE WHEN p.EndDate<=:as_of THEN p.EndDate END AS EndDate,t.TreatmentName,
       CASE WHEN p.EndDate<=:as_of THEN p.Outcome END AS Outcome,
       CASE WHEN p.EndDate<=:as_of THEN p.Compliance END AS Compliance,p.FrequencyTreatment,
       teams.CareTeam,orders.SelectedMedicationOrders,
       CASE WHEN e.EndDate<=:as_of THEN e.DischargeDisposition END AS DischargeDisposition,
       CASE WHEN e.EndDate<=:as_of THEN e.FollowUpPlan END AS FollowUpPlan
FROM Encounter e JOIN PatientTreatment p USING(EncounterID) JOIN Treatment t USING(TreatmentID)
LEFT JOIN teams USING(PatientTreatmentID) LEFT JOIN orders USING(PatientTreatmentID)
WHERE e.PatientID=:patient_id AND p.StartDate<=:as_of
ORDER BY p.StartDate,e.EncounterID,p.PatientTreatmentID;
