
-- ============================================================
-- INCUBYTE DATA ENGINEERING ASSESSMENT
-- DATA QUALITY AND VALIDATION QUERIES
-- ============================================================

USE DATABASE INCUBYTE_DB;
USE SCHEMA PUBLIC;


-- ============================================================
-- 1. TOTAL RECORD COUNTS
-- ============================================================

SELECT 'MEMBERS' AS TABLE_NAME, COUNT(*) AS TOTAL_RECORDS
FROM MEMBERS

UNION ALL

SELECT 'REDEMPTIONS', COUNT(*)
FROM REDEMPTIONS

UNION ALL

SELECT 'FLATTENED_REDEMPTIONS', COUNT(*)
FROM FLATTENED_REDEMPTIONS;


-- ============================================================
-- 2. MANDATORY FIELD VALIDATION - MEMBERS
-- Mandatory fields: MEMBER_NAME, MEMBER_ID, ENROLLMENT_DATE
-- DOB, COUNTRY and LAST_FLIGHT_DATE are optional.
-- ============================================================

SELECT *
FROM MEMBERS
WHERE MEMBER_ID IS NULL
   OR TRIM(MEMBER_ID) = ''
   OR MEMBER_NAME IS NULL
   OR TRIM(MEMBER_NAME) = ''
   OR ENROLLMENT_DATE IS NULL;


-- ============================================================
-- 3. DUPLICATE MEMBER KEY CHECK
-- Member IDs can repeat across different countries.
-- The combination MEMBER_ID + COUNTRY must be unique.
-- ============================================================

SELECT
    UPPER(TRIM(MEMBER_NAME)) AS MEMBER_KEY,
    COUNT(*) AS DUPLICATE_COUNT
FROM MEMBERS
GROUP BY UPPER(TRIM(MEMBER_NAME))
HAVING COUNT(*) > 1;


-- ============================================================
-- 4. DUPLICATE TRANSACTION ID CHECK
-- ============================================================

SELECT
    TXN_ID,
    COUNT(*) AS DUPLICATE_COUNT
FROM REDEMPTIONS
GROUP BY TXN_ID
HAVING COUNT(*) > 1;


-- ============================================================
-- 5. REDEMPTION MANDATORY FIELD VALIDATION
-- ============================================================

SELECT *
FROM REDEMPTIONS
WHERE TXN_ID IS NULL
   OR MEMBER_ID IS NULL
   OR TXN_DATE IS NULL
   OR MILES_REDEEMED IS NULL;


-- ============================================================
-- 6. INVALID MILES VALIDATION
-- ============================================================

SELECT *
FROM REDEMPTIONS
WHERE MILES_REDEEMED < 0;


-- ============================================================
-- 7. MEMBER AGE VALIDATION
-- DOB is optional. Age can be NULL when DOB is missing.
-- ============================================================

SELECT *
FROM MEMBERS
WHERE DOB > CURRENT_DATE()
   OR AGE < 0;


-- ============================================================
-- 8. STALE MEMBER VALIDATION
-- A member is stale when days since last flight exceed 90.
-- Missing LAST_FLIGHT_DATE is optional and is excluded.
-- ============================================================

SELECT
    MEMBER_ID,
    COUNTRY,
    LAST_FLIGHT_DATE,
    DATEDIFF(
        'DAY',
        LAST_FLIGHT_DATE,
        CURRENT_DATE()
    ) AS DAYS_SINCE_LAST_FLIGHT,
    STALE_MEMBER
FROM MEMBERS
WHERE LAST_FLIGHT_DATE IS NOT NULL
  AND (
        (
            DATEDIFF(
                'DAY',
                LAST_FLIGHT_DATE,
                CURRENT_DATE()
            ) > 90
            AND COALESCE(STALE_MEMBER, '') <> 'Y'
        )
        OR
        (
            DATEDIFF(
                'DAY',
                LAST_FLIGHT_DATE,
                CURRENT_DATE()
            ) <= 90
            AND COALESCE(STALE_MEMBER, '') <> 'N'
        )
  );


-- ============================================================
-- 9. ORPHAN REDEMPTION CHECK
-- Redemption records without a matching member profile.
-- ============================================================

SELECT
    R.*
FROM FLATTENED_REDEMPTIONS R
LEFT JOIN MEMBERS M
    ON R.MEMBER_ID = M.MEMBER_ID
WHERE M.MEMBER_ID IS NULL;


-- ============================================================
-- 10. INVALID COUNTRY CHECK
-- NULL country is allowed because COUNTRY is optional.
-- If country is provided, it must be a supported value.
-- ============================================================

SELECT *
FROM MEMBERS
WHERE COUNTRY IS NOT NULL
  AND UPPER(TRIM(COUNTRY)) NOT IN (
      'USA',
      'IND',
      'PHIL',
      'CAN',
      'AU'
  );


-- ============================================================
-- 11. COUNTRY-WISE RECORD COUNT VALIDATION
-- ============================================================

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


-- ============================================================
-- 12. COUNTRY TABLE CONSOLIDATION CHECK
-- ============================================================

SELECT
    COUNT(*) AS TOTAL_COUNTRY_RECORDS,
    COUNT(DISTINCT UPPER(TRIM(MEMBER_NAME))) AS DISTINCT_MEMBER_NAMES
FROM (
    SELECT MEMBER_NAME FROM MEMBERS_USA
    UNION ALL
    SELECT MEMBER_NAME FROM MEMBERS_IND
    UNION ALL
    SELECT MEMBER_NAME FROM MEMBERS_PHIL
    UNION ALL
    SELECT MEMBER_NAME FROM MEMBERS_CAN
    UNION ALL
    SELECT MEMBER_NAME FROM MEMBERS_AU
);

-- ============================================================
-- 13. REDEMPTION TO MEMBER PROFILE JOIN VALIDATION
-- ============================================================

SELECT
    M.MEMBER_ID,
    M.MEMBER_NAME,
    M.COUNTRY,
    R.TXN_ID,
    R.TXN_DATE,
    R.MILES_REDEEMED,
    R.STATUS
FROM MEMBERS M
INNER JOIN FLATTENED_REDEMPTIONS R
    ON M.MEMBER_ID = R.MEMBER_ID
ORDER BY R.TXN_DATE;


-- ============================================================
-- 14. MASTER TO COUNTRY TABLE RECONCILIATION
-- Check whether every master member exists in country tables.
-- Expected result: 0 rows.
-- ============================================================

SELECT
    MEMBER_ID,
    COUNTRY
FROM MEMBERS

MINUS

SELECT
    MEMBER_ID,
    COUNTRY
FROM (
    SELECT MEMBER_ID, COUNTRY FROM MEMBERS_USA

    UNION ALL

    SELECT MEMBER_ID, COUNTRY FROM MEMBERS_IND

    UNION ALL

    SELECT MEMBER_ID, COUNTRY FROM MEMBERS_PHIL

    UNION ALL

    SELECT MEMBER_ID, COUNTRY FROM MEMBERS_CAN

    UNION ALL

    SELECT MEMBER_ID, COUNTRY FROM MEMBERS_AU
);


-- ============================================================
-- 15. COUNTRY TO MASTER TABLE RECONCILIATION
-- Check whether country tables contain extra records.
-- Expected result: 0 rows.
-- ============================================================

SELECT
    MEMBER_ID,
    COUNTRY
FROM (
    SELECT MEMBER_ID, COUNTRY FROM MEMBERS_USA

    UNION ALL

    SELECT MEMBER_ID, COUNTRY FROM MEMBERS_IND

    UNION ALL

    SELECT MEMBER_ID, COUNTRY FROM MEMBERS_PHIL

    UNION ALL

    SELECT MEMBER_ID, COUNTRY FROM MEMBERS_CAN

    UNION ALL

    SELECT MEMBER_ID, COUNTRY FROM MEMBERS_AU
)

MINUS

SELECT
    MEMBER_ID,
    COUNTRY
FROM MEMBERS;
