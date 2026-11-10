PRAGMA foreign_keys = ON;

CREATE TABLE Patient (
    PatientID INTEGER PRIMARY KEY,
    FirstName TEXT NOT NULL CHECK(length(trim(FirstName))>0),
    LastName TEXT NOT NULL CHECK(length(trim(LastName))>0),
    DateOfBirth TEXT NOT NULL CHECK(date(DateOfBirth,'+0 days') IS NOT NULL AND date(DateOfBirth,'+0 days')=DateOfBirth),
    Email TEXT,
    EmergencyContactName TEXT,
    EmergencyContactRelationship TEXT,
    EmergencyContactPhone TEXT,
    PhoneNumber TEXT,
    Address TEXT,
    Gender TEXT
);
CREATE TABLE Physician (
    PhysicianID INTEGER PRIMARY KEY,
    FirstName TEXT NOT NULL CHECK(length(trim(FirstName))>0),
    LastName TEXT NOT NULL CHECK(length(trim(LastName))>0),
    Specialty TEXT NOT NULL CHECK(length(trim(Specialty))>0),
    Email TEXT
);
-- An encounter has exactly one patient, including outpatient encounters.
CREATE TABLE Encounter (
    EncounterID INTEGER PRIMARY KEY,
    PatientID INTEGER NOT NULL REFERENCES Patient(PatientID),
    EncounterType TEXT NOT NULL CHECK(EncounterType IN ('inpatient','outpatient')),
    StartDate TEXT NOT NULL CHECK(date(StartDate,'+0 days') IS NOT NULL AND date(StartDate,'+0 days')=StartDate),
    EndDate TEXT CHECK(EndDate IS NULL OR (date(EndDate,'+0 days') IS NOT NULL AND date(EndDate,'+0 days')=EndDate AND EndDate>=StartDate)),
    VisitReason TEXT,
    AdmissionType TEXT CHECK(AdmissionType IN ('planned','unplanned')),
    DischargeDisposition TEXT,
    FollowUpPlan TEXT,
    -- A computed reference enforces required inpatient details at transaction commit.
    RequiredHospitalizationID INTEGER GENERATED ALWAYS AS (
        CASE WHEN EncounterType='inpatient' THEN EncounterID END
    ) VIRTUAL REFERENCES Hospitalization(EncounterID) DEFERRABLE INITIALLY DEFERRED,
    CHECK(EncounterType='inpatient' OR (AdmissionType IS NULL AND DischargeDisposition IS NULL))
);
-- Subtype: admission/discharge dates remain in Encounter to avoid duplication.
CREATE TABLE Hospitalization (
    EncounterID INTEGER PRIMARY KEY REFERENCES Encounter(EncounterID),
    FallsRisk INTEGER CHECK(FallsRisk IS NULL OR (typeof(FallsRisk)='integer' AND FallsRisk BETWEEN 1 AND 10)),
    ADLScore INTEGER CHECK(ADLScore IS NULL OR (typeof(ADLScore)='integer' AND ADLScore BETWEEN 1 AND 10)),
    FallsOccurred INTEGER CHECK(FallsOccurred IN (0,1)),
    MedicationErrors INTEGER CHECK(MedicationErrors IS NULL OR (typeof(MedicationErrors)='integer' AND MedicationErrors>=0)),
    Diet TEXT,
    CarePlanAdherence INTEGER CHECK(CarePlanAdherence IN (0,1)),
    ActivityLevel TEXT,
    IsolationType TEXT
);
CREATE TABLE Treatment (
    TreatmentID INTEGER PRIMARY KEY,
    TreatmentName TEXT NOT NULL UNIQUE CHECK(length(trim(TreatmentName))>0),
    Description TEXT NOT NULL CHECK(length(trim(Description))>0)
);
CREATE TABLE PatientTreatment (
    PatientTreatmentID INTEGER PRIMARY KEY,
    EncounterID INTEGER NOT NULL REFERENCES Encounter(EncounterID),
    TreatmentID INTEGER NOT NULL REFERENCES Treatment(TreatmentID),
    ResponsiblePhysicianID INTEGER NOT NULL REFERENCES Physician(PhysicianID),
    StartDate TEXT NOT NULL CHECK(date(StartDate,'+0 days') IS NOT NULL AND date(StartDate,'+0 days')=StartDate),
    EndDate TEXT CHECK(EndDate IS NULL OR (date(EndDate,'+0 days') IS NOT NULL AND date(EndDate,'+0 days')=EndDate AND EndDate>=StartDate)),
    Outcome TEXT,
    Compliance TEXT,
    FrequencyTreatment TEXT,
    ResponsibleRole TEXT NOT NULL CHECK(length(trim(ResponsibleRole))>0)
);
-- Additional care-team members; responsibility is represented separately above.
CREATE TABLE PhysicianTreatment (
    PhysicianID INTEGER NOT NULL REFERENCES Physician(PhysicianID),
    PatientTreatmentID INTEGER NOT NULL REFERENCES PatientTreatment(PatientTreatmentID),
    Role TEXT NOT NULL CHECK(length(trim(Role))>0),
    PRIMARY KEY(PhysicianID,PatientTreatmentID)
);
CREATE TABLE Medication (
    MedicationID INTEGER PRIMARY KEY,
    MedicationName TEXT NOT NULL UNIQUE CHECK(length(trim(MedicationName))>0),
    StandardDosage TEXT
);
-- A row is an order, not proof that a dose was administered.
CREATE TABLE MedicationOrder (
    MedicationOrderID INTEGER PRIMARY KEY,
    PatientTreatmentID INTEGER NOT NULL REFERENCES PatientTreatment(PatientTreatmentID),
    MedicationID INTEGER NOT NULL REFERENCES Medication(MedicationID),
    Dosage TEXT NOT NULL CHECK(length(trim(Dosage))>0),
    Frequency TEXT NOT NULL CHECK(length(trim(Frequency))>0),
    PrescribingPhysicianID INTEGER REFERENCES Physician(PhysicianID),
    OrderDate TEXT CHECK(OrderDate IS NULL OR (date(OrderDate,'+0 days') IS NOT NULL AND date(OrderDate,'+0 days')=OrderDate)),
    Route TEXT,
    Indication TEXT
);
CREATE TABLE SideEffect (
    SideEffectID INTEGER PRIMARY KEY,
    EffectName TEXT NOT NULL UNIQUE CHECK(length(trim(EffectName))>0)
);
CREATE TABLE MedicationSideEffect (
    MedicationID INTEGER NOT NULL REFERENCES Medication(MedicationID),
    SideEffectID INTEGER NOT NULL REFERENCES SideEffect(SideEffectID),
    PRIMARY KEY(MedicationID,SideEffectID)
);
CREATE TABLE TreatmentSideEffect (
    TreatmentID INTEGER NOT NULL REFERENCES Treatment(TreatmentID),
    SideEffectID INTEGER NOT NULL REFERENCES SideEffect(SideEffectID),
    PRIMARY KEY(TreatmentID,SideEffectID)
);
CREATE TABLE InfectionType (
    InfectionTypeID INTEGER PRIMARY KEY,
    TypeName TEXT NOT NULL UNIQUE CHECK(length(trim(TypeName))>0)
);
CREATE TABLE HospitalInfection (
    HospitalInfectionID INTEGER PRIMARY KEY,
    EncounterID INTEGER NOT NULL REFERENCES Hospitalization(EncounterID),
    InfectionTypeID INTEGER NOT NULL REFERENCES InfectionType(InfectionTypeID),
    DetectedDate TEXT NOT NULL CHECK(date(DetectedDate,'+0 days') IS NOT NULL AND date(DetectedDate,'+0 days')=DetectedDate),
    HospitalAcquired INTEGER NOT NULL CHECK(HospitalAcquired IN (0,1)),
    ResolvedDate TEXT CHECK(ResolvedDate IS NULL OR (date(ResolvedDate,'+0 days') IS NOT NULL AND date(ResolvedDate,'+0 days')=ResolvedDate AND ResolvedDate>=DetectedDate)),
    Organism TEXT,
    ClinicalNote TEXT
);
CREATE INDEX EncounterPatientDate ON Encounter(PatientID,StartDate);
CREATE INDEX TreatmentEncounter ON PatientTreatment(EncounterID);
CREATE INDEX MedicationOrderTreatment ON MedicationOrder(PatientTreatmentID);
CREATE INDEX AdditionalPhysiciansTreatment ON PhysicianTreatment(PatientTreatmentID);
CREATE INDEX InfectionEncounter ON HospitalInfection(EncounterID);
CREATE INDEX MedicationOrderPrescriber ON MedicationOrder(PrescribingPhysicianID);

CREATE TRIGGER HospitalizationTypeInsert BEFORE INSERT ON Hospitalization
WHEN (SELECT EncounterType FROM Encounter WHERE EncounterID=NEW.EncounterID) IS NOT 'inpatient'
BEGIN SELECT RAISE(ABORT,'Hospitalization requires an inpatient encounter'); END;
CREATE TRIGGER HospitalizationTypeUpdate BEFORE UPDATE ON Hospitalization
WHEN (SELECT EncounterType FROM Encounter WHERE EncounterID=NEW.EncounterID) IS NOT 'inpatient'
BEGIN SELECT RAISE(ABORT,'Hospitalization requires an inpatient encounter'); END;
CREATE TRIGGER EncounterTypeUpdate BEFORE UPDATE OF EncounterType ON Encounter
WHEN NEW.EncounterType<>'inpatient' AND EXISTS(SELECT 1 FROM Hospitalization WHERE EncounterID=OLD.EncounterID)
BEGIN SELECT RAISE(ABORT,'Remove hospitalization subtype before changing encounter type'); END;

-- Reject treatment dates outside the associated encounter, including updates.
CREATE TRIGGER TreatmentDatesInsert BEFORE INSERT ON PatientTreatment
WHEN EXISTS(SELECT 1 FROM Encounter e WHERE e.EncounterID=NEW.EncounterID AND
 (NEW.StartDate<e.StartDate OR (e.EndDate IS NOT NULL AND (NEW.StartDate>e.EndDate OR NEW.EndDate IS NULL OR NEW.EndDate>e.EndDate))))
BEGIN SELECT RAISE(ABORT,'Treatment dates outside encounter'); END;
CREATE TRIGGER TreatmentDatesUpdate BEFORE UPDATE ON PatientTreatment
WHEN EXISTS(SELECT 1 FROM Encounter e WHERE e.EncounterID=NEW.EncounterID AND
 (NEW.StartDate<e.StartDate OR (e.EndDate IS NOT NULL AND (NEW.StartDate>e.EndDate OR NEW.EndDate IS NULL OR NEW.EndDate>e.EndDate))))
BEGIN SELECT RAISE(ABORT,'Treatment dates outside encounter'); END;
CREATE TRIGGER EncounterDatesUpdate BEFORE UPDATE OF StartDate,EndDate ON Encounter
WHEN EXISTS(SELECT 1 FROM PatientTreatment p WHERE p.EncounterID=OLD.EncounterID AND
 (p.StartDate<NEW.StartDate OR (NEW.EndDate IS NOT NULL AND (p.StartDate>NEW.EndDate OR p.EndDate IS NULL OR p.EndDate>NEW.EndDate))))
BEGIN SELECT RAISE(ABORT,'Encounter dates would invalidate a treatment'); END;

CREATE TRIGGER MedicationOrderDateInsert BEFORE INSERT ON MedicationOrder
WHEN NEW.OrderDate IS NOT NULL AND EXISTS(
 SELECT 1 FROM PatientTreatment p JOIN Encounter e USING(EncounterID)
 WHERE p.PatientTreatmentID=NEW.PatientTreatmentID AND
 (NEW.OrderDate<e.StartDate OR (e.EndDate IS NOT NULL AND NEW.OrderDate>e.EndDate)))
BEGIN SELECT RAISE(ABORT,'Medication order date outside encounter'); END;
CREATE TRIGGER MedicationOrderDateUpdate BEFORE UPDATE ON MedicationOrder
WHEN NEW.OrderDate IS NOT NULL AND EXISTS(
 SELECT 1 FROM PatientTreatment p JOIN Encounter e USING(EncounterID)
 WHERE p.PatientTreatmentID=NEW.PatientTreatmentID AND
 (NEW.OrderDate<e.StartDate OR (e.EndDate IS NOT NULL AND NEW.OrderDate>e.EndDate)))
BEGIN SELECT RAISE(ABORT,'Medication order date outside encounter'); END;
CREATE TRIGGER TreatmentEncounterOrdersUpdate BEFORE UPDATE OF EncounterID ON PatientTreatment
WHEN EXISTS(SELECT 1 FROM MedicationOrder m JOIN Encounter e ON e.EncounterID=NEW.EncounterID
 WHERE m.PatientTreatmentID=OLD.PatientTreatmentID AND m.OrderDate IS NOT NULL AND
 (m.OrderDate<e.StartDate OR (e.EndDate IS NOT NULL AND m.OrderDate>e.EndDate)))
BEGIN SELECT RAISE(ABORT,'Treatment move would invalidate medication order dates'); END;
CREATE TRIGGER EncounterDatesOrdersUpdate BEFORE UPDATE OF StartDate,EndDate ON Encounter
WHEN EXISTS(SELECT 1 FROM PatientTreatment p JOIN MedicationOrder m USING(PatientTreatmentID)
 WHERE p.EncounterID=OLD.EncounterID AND m.OrderDate IS NOT NULL AND
 (m.OrderDate<NEW.StartDate OR (NEW.EndDate IS NOT NULL AND m.OrderDate>NEW.EndDate)))
BEGIN SELECT RAISE(ABORT,'Encounter dates would invalidate medication order dates'); END;

-- A local correction history, not an authenticated or tamper-proof clinical audit log.
CREATE TABLE EncounterPatientChange (
    ChangeID INTEGER PRIMARY KEY,
    EncounterID INTEGER NOT NULL REFERENCES Encounter(EncounterID),
    PreviousPatientID INTEGER NOT NULL REFERENCES Patient(PatientID),
    NewPatientID INTEGER NOT NULL REFERENCES Patient(PatientID),
    ChangedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(PreviousPatientID<>NewPatientID)
);
CREATE TRIGGER EncounterPatientChanged AFTER UPDATE OF PatientID ON Encounter
WHEN OLD.PatientID<>NEW.PatientID
BEGIN
 INSERT INTO EncounterPatientChange(EncounterID,PreviousPatientID,NewPatientID)
 VALUES(NEW.EncounterID,OLD.PatientID,NEW.PatientID);
END;

CREATE TRIGGER EncounterBirthInsert BEFORE INSERT ON Encounter
WHEN NEW.StartDate<(SELECT DateOfBirth FROM Patient WHERE PatientID=NEW.PatientID)
BEGIN SELECT RAISE(ABORT,'Encounter cannot precede patient birth'); END;
CREATE TRIGGER EncounterBirthUpdate BEFORE UPDATE OF PatientID,StartDate ON Encounter
WHEN NEW.StartDate<(SELECT DateOfBirth FROM Patient WHERE PatientID=NEW.PatientID)
BEGIN SELECT RAISE(ABORT,'Encounter cannot precede patient birth'); END;
CREATE TRIGGER PatientBirthUpdate BEFORE UPDATE OF DateOfBirth ON Patient
WHEN EXISTS(SELECT 1 FROM Encounter WHERE PatientID=OLD.PatientID AND StartDate<NEW.DateOfBirth)
BEGIN SELECT RAISE(ABORT,'Birth date would invalidate existing encounters'); END;

-- Day-level chronology: a discharge and next admission on the same day are allowed.
CREATE TRIGGER EncounterOverlapInsert BEFORE INSERT ON Encounter
WHEN NEW.EncounterType='inpatient' AND EXISTS(
 SELECT 1 FROM Encounter e WHERE e.PatientID=NEW.PatientID AND e.EncounterType='inpatient'
 AND NEW.StartDate<COALESCE(e.EndDate,'9999-12-31')
 AND e.StartDate<COALESCE(NEW.EndDate,'9999-12-31'))
BEGIN SELECT RAISE(ABORT,'Overlapping inpatient encounters'); END;
CREATE TRIGGER EncounterOverlapUpdate BEFORE UPDATE OF PatientID,EncounterType,StartDate,EndDate ON Encounter
WHEN NEW.EncounterType='inpatient' AND EXISTS(
 SELECT 1 FROM Encounter e WHERE e.PatientID=NEW.PatientID AND e.EncounterID<>OLD.EncounterID
 AND e.EncounterType='inpatient' AND NEW.StartDate<COALESCE(e.EndDate,'9999-12-31')
 AND e.StartDate<COALESCE(NEW.EndDate,'9999-12-31'))
BEGIN SELECT RAISE(ABORT,'Overlapping inpatient encounters'); END;

CREATE TRIGGER InfectionDatesInsert BEFORE INSERT ON HospitalInfection
WHEN EXISTS(SELECT 1 FROM Encounter e WHERE e.EncounterID=NEW.EncounterID AND
 (NEW.DetectedDate<e.StartDate OR (e.EndDate IS NOT NULL AND NEW.DetectedDate>e.EndDate)))
BEGIN SELECT RAISE(ABORT,'Infection detection outside encounter'); END;
CREATE TRIGGER InfectionDatesUpdate BEFORE UPDATE ON HospitalInfection
WHEN EXISTS(SELECT 1 FROM Encounter e WHERE e.EncounterID=NEW.EncounterID AND
 (NEW.DetectedDate<e.StartDate OR (e.EndDate IS NOT NULL AND NEW.DetectedDate>e.EndDate)))
BEGIN SELECT RAISE(ABORT,'Infection detection outside encounter'); END;
CREATE TRIGGER EncounterDatesInfectionsUpdate BEFORE UPDATE OF StartDate,EndDate ON Encounter
WHEN EXISTS(SELECT 1 FROM HospitalInfection h WHERE h.EncounterID=OLD.EncounterID AND
 (h.DetectedDate<NEW.StartDate OR (NEW.EndDate IS NOT NULL AND h.DetectedDate>NEW.EndDate)))
BEGIN SELECT RAISE(ABORT,'Encounter dates would invalidate infection detection'); END;

CREATE TRIGGER AdditionalPhysicianInsert BEFORE INSERT ON PhysicianTreatment
WHEN NEW.PhysicianID=(SELECT ResponsiblePhysicianID FROM PatientTreatment WHERE PatientTreatmentID=NEW.PatientTreatmentID)
BEGIN SELECT RAISE(ABORT,'Responsible physician cannot also be additional'); END;
CREATE TRIGGER AdditionalPhysicianUpdate BEFORE UPDATE ON PhysicianTreatment
WHEN NEW.PhysicianID=(SELECT ResponsiblePhysicianID FROM PatientTreatment WHERE PatientTreatmentID=NEW.PatientTreatmentID)
BEGIN SELECT RAISE(ABORT,'Responsible physician cannot also be additional'); END;
CREATE TRIGGER ResponsiblePhysicianUpdate BEFORE UPDATE OF ResponsiblePhysicianID ON PatientTreatment
WHEN EXISTS(SELECT 1 FROM PhysicianTreatment WHERE PatientTreatmentID=OLD.PatientTreatmentID AND PhysicianID=NEW.ResponsiblePhysicianID)
BEGIN SELECT RAISE(ABORT,'Remove additional assignment before making physician responsible'); END;

-- Simplified descriptive measure; the reporting query applies a follow-up cutoff.
CREATE VIEW InpatientReadmission AS
WITH ordered AS (
 SELECT e.EncounterID,e.PatientID,e.StartDate AS AdmitDate,e.EndDate AS DischargeDate,
        LEAD(e.StartDate) OVER(PARTITION BY e.PatientID ORDER BY e.StartDate,e.EncounterID) AS NextAdmitDate,
        LEAD(e.EncounterID) OVER(PARTITION BY e.PatientID ORDER BY e.StartDate,e.EncounterID) AS NextEncounterID
 FROM Encounter e JOIN Hospitalization h USING(EncounterID)
)
SELECT *,CASE WHEN DischargeDate IS NOT NULL AND NextAdmitDate IS NOT NULL
 THEN CAST(julianday(NextAdmitDate)-julianday(DischargeDate) AS INTEGER) END AS DaysToNextAdmission
FROM ordered;

CREATE VIEW TreatmentCareTeam AS
SELECT PatientTreatmentID,ResponsiblePhysicianID AS PhysicianID,ResponsibleRole AS Role,1 AS Responsible
FROM PatientTreatment
UNION ALL
SELECT PatientTreatmentID,PhysicianID,Role,0 AS Responsible FROM PhysicianTreatment;
