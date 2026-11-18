
-- =====================================================
-- INCUBYTE DATA ENGINEERING ASSESSMENT
-- COUNTRY-WISE MEMBER TABLES
-- =====================================================

USE DATABASE INCUBYTE_DB;
USE SCHEMA PUBLIC;


-- -----------------------------------------------------
-- 1. CREATE COUNTRY-WISE TABLES
-- -----------------------------------------------------

CREATE TABLE IF NOT EXISTS MEMBERS_USA LIKE MEMBERS;
CREATE TABLE IF NOT EXISTS MEMBERS_IND LIKE MEMBERS;
CREATE TABLE IF NOT EXISTS MEMBERS_PHIL LIKE MEMBERS;
CREATE TABLE IF NOT EXISTS MEMBERS_CAN LIKE MEMBERS;
CREATE TABLE IF NOT EXISTS MEMBERS_AU LIKE MEMBERS;


-- -----------------------------------------------------
-- 2. IDENTIFY LATEST RECORD FOR EACH MEMBER
-- -----------------------------------------------------


-- 2. IDENTIFY LATEST RECORD FOR EACH MEMBER

CREATE OR REPLACE TEMPORARY TABLE LATEST_MEMBERS AS
SELECT *
FROM MEMBERS
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY UPPER(TRIM(MEMBER_NAME))
    ORDER BY
        ENROLLMENT_DATE DESC NULLS LAST,
        LAST_FLIGHT_DATE DESC NULLS LAST
) = 1;


-- -----------------------------------------------------
-- 3. REFRESH COUNTRY-WISE TABLES
-- -----------------------------------------------------


-- Remove previous country records for members
-- present in the latest source data.


-- 3. REFRESH COUNTRY-WISE TABLES
BEGIN TRANSACTION;

DELETE FROM MEMBERS_USA
WHERE UPPER(TRIM(MEMBER_NAME)) IN (
    SELECT UPPER(TRIM(MEMBER_NAME))
    FROM LATEST_MEMBERS
);

DELETE FROM MEMBERS_IND
WHERE UPPER(TRIM(MEMBER_NAME)) IN (
    SELECT UPPER(TRIM(MEMBER_NAME))
    FROM LATEST_MEMBERS
);

DELETE FROM MEMBERS_PHIL
WHERE UPPER(TRIM(MEMBER_NAME)) IN (
    SELECT UPPER(TRIM(MEMBER_NAME))
    FROM LATEST_MEMBERS
);

DELETE FROM MEMBERS_CAN
WHERE UPPER(TRIM(MEMBER_NAME)) IN (
    SELECT UPPER(TRIM(MEMBER_NAME))
    FROM LATEST_MEMBERS
);

DELETE FROM MEMBERS_AU
WHERE UPPER(TRIM(MEMBER_NAME)) IN (
    SELECT UPPER(TRIM(MEMBER_NAME))
    FROM LATEST_MEMBERS
);



-- -----------------------------------------------------
-- 4. INSERT USA MEMBERS
-- -----------------------------------------------------

INSERT INTO MEMBERS_USA
SELECT *
FROM LATEST_MEMBERS
WHERE UPPER(TRIM(COUNTRY)) = 'USA';


-- -----------------------------------------------------
-- 5. INSERT INDIA MEMBERS
-- -----------------------------------------------------

INSERT INTO MEMBERS_IND
SELECT *
FROM LATEST_MEMBERS
WHERE UPPER(TRIM(COUNTRY)) = 'IND';


-- -----------------------------------------------------
-- 6. INSERT PHILIPPINES MEMBERS
-- -----------------------------------------------------

INSERT INTO MEMBERS_PHIL
SELECT *
FROM LATEST_MEMBERS
WHERE UPPER(TRIM(COUNTRY)) = 'PHIL';


-- -----------------------------------------------------
-- 7. INSERT CANADA MEMBERS
-- -----------------------------------------------------

INSERT INTO MEMBERS_CAN
SELECT *
FROM LATEST_MEMBERS
WHERE UPPER(TRIM(COUNTRY)) = 'CAN';


-- -----------------------------------------------------
-- 8. INSERT AUSTRALIA MEMBERS
-- -----------------------------------------------------

INSERT INTO MEMBERS_AU
SELECT *
FROM LATEST_MEMBERS
WHERE UPPER(TRIM(COUNTRY)) = 'AU';


COMMIT;


-- -----------------------------------------------------
-- 9. VERIFY COUNTRY-WISE RECORD COUNTS
-- -----------------------------------------------------

SELECT 'USA' AS COUNTRY, COUNT(*) AS MEMBER_COUNT
FROM MEMBERS_USA

UNION ALL

SELECT 'IND', COUNT(*)
FROM MEMBERS_IND

UNION ALL

SELECT 'PHIL', COUNT(*)
FROM MEMBERS_PHIL

UNION ALL

SELECT 'CAN', COUNT(*)
FROM MEMBERS_CAN

UNION ALL

SELECT 'AU', COUNT(*)
FROM MEMBERS_AU;


-- -----------------------------------------------------
-- 10. VERIFY ALL COUNTRY-WISE MEMBER RECORDS
-- -----------------------------------------------------

SELECT * FROM MEMBERS_USA
UNION ALL
SELECT * FROM MEMBERS_IND
UNION ALL
SELECT * FROM MEMBERS_PHIL
UNION ALL
SELECT * FROM MEMBERS_CAN
UNION ALL
SELECT * FROM MEMBERS_AU;
