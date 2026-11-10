-- Dated orders on/before :as_of; unknown dates are excluded and reported separately.
-- Count orders, not administrations; retain catalog items with zero eligible orders.
SELECT m.MedicationName,COUNT(o.MedicationOrderID) AS OrderCount
FROM Medication m LEFT JOIN MedicationOrder o ON o.MedicationID=m.MedicationID AND o.OrderDate<=:as_of
GROUP BY m.MedicationID,m.MedicationName ORDER BY OrderCount DESC,m.MedicationName;
