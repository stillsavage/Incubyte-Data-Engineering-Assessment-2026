
-- =====================================================
-- INCUBYTE DATA ENGINEERING ASSESSMENT
-- JSON REDEMPTION FEED FLATTENING
-- =====================================================

USE DATABASE INCUBYTE_DB;
USE SCHEMA PUBLIC;


-- -----------------------------------------------------
-- 1. CREATE RAW JSON TABLE
-- -----------------------------------------------------

CREATE TABLE IF NOT EXISTS RAW_REDEMPTION_JSON (
    RAW_ID NUMBER AUTOINCREMENT,
    RAW_DATA VARIANT,
    INGESTED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);


-- -----------------------------------------------------
-- 2. LOAD SAMPLE JSON INTO RAW TABLE
-- -----------------------------------------------------

INSERT INTO RAW_REDEMPTION_JSON (RAW_DATA)
SELECT PARSE_JSON(
'{
  "member_id": "223457",
  "feed_date": "2024-01-15",
  "redemptions": [
    {
      "txn_id": "RX10091",
      "txn_date": "2024-01-10",
      "partner": "AeroLink",
      "miles_redeemed": 12000,
      "status": "COMPLETED"
    },
    {
      "txn_id": "RX10092",
      "txn_date": "2024-01-13",
      "partner": "SkyPoints",
      "miles_redeemed": 5000,
      "status": "PENDING"
    }
  ]
}'
);


-- -----------------------------------------------------
-- 3. CREATE FLATTENED REDEMPTION TABLE
-- -----------------------------------------------------

CREATE TABLE IF NOT EXISTS FLATTENED_REDEMPTIONS (
    TXN_ID VARCHAR(50),
    TXN_DATE DATE,
    PARTNER VARCHAR(100),
    MILES_REDEEMED NUMBER(18,0),
    STATUS VARCHAR(30),
    MEMBER_ID VARCHAR(50),
    FEED_DATE DATE,
    INGESTED_AT TIMESTAMP_NTZ
);


-- -----------------------------------------------------
-- 4. FLATTEN JSON ARRAY INTO ROWS
-- -----------------------------------------------------


MERGE INTO FLATTENED_REDEMPTIONS T
USING (
    SELECT
        R.RAW_ID,
        R.RAW_DATA:member_id::VARCHAR AS MEMBER_ID,
        F.VALUE:txn_id::VARCHAR AS TXN_ID,

        TO_DATE(
            F.VALUE:txn_date::VARCHAR,
            'YYYY-MM-DD'
        ) AS TXN_DATE,

        F.VALUE:partner::VARCHAR AS PARTNER,
        F.VALUE:miles_redeemed::NUMBER AS MILES_REDEEMED,
        UPPER(F.VALUE:status::VARCHAR) AS STATUS,

        TO_DATE(
            R.RAW_DATA:feed_date::VARCHAR,
            'YYYY-MM-DD'
        ) AS FEED_DATE,

        R.INGESTED_AT

    FROM RAW_REDEMPTION_JSON R,
    LATERAL FLATTEN(
        INPUT => R.RAW_DATA:redemptions
    ) F

    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY F.VALUE:txn_id::VARCHAR
        ORDER BY R.INGESTED_AT DESC, R.RAW_ID DESC
    ) = 1

) S

ON T.TXN_ID = S.TXN_ID

WHEN MATCHED THEN UPDATE SET
    T.TXN_DATE = S.TXN_DATE,
    T.PARTNER = S.PARTNER,
    T.MILES_REDEEMED = S.MILES_REDEEMED,
    T.STATUS = S.STATUS,
    T.MEMBER_ID = S.MEMBER_ID,
    T.FEED_DATE = S.FEED_DATE,
    T.INGESTED_AT = S.INGESTED_AT

WHEN NOT MATCHED THEN INSERT (
    TXN_ID,
    TXN_DATE,
    PARTNER,
    MILES_REDEEMED,
    STATUS,
    MEMBER_ID,
    FEED_DATE,
    INGESTED_AT
)
VALUES (
    S.TXN_ID,
    S.TXN_DATE,
    S.PARTNER,
    S.MILES_REDEEMED,
    S.STATUS,
    S.MEMBER_ID,
    S.FEED_DATE,
    S.INGESTED_AT
);


-- -----------------------------------------------------
-- 5. VERIFY FLATTENED REDEMPTION RECORDS
-- -----------------------------------------------------

SELECT *
FROM FLATTENED_REDEMPTIONS
ORDER BY TXN_DATE;


-- -----------------------------------------------------
-- 6. JOIN REDEMPTIONS WITH MEMBER PROFILE
-- -----------------------------------------------------

SELECT
    M.MEMBER_ID,
    M.MEMBER_NAME,
    M.COUNTRY,
    M.TIER_CODE,
    R.TXN_ID,
    R.TXN_DATE,
    R.PARTNER,
    R.MILES_REDEEMED,
    R.STATUS,
    R.FEED_DATE

FROM INCUBYTE_DB.PUBLIC.MEMBERS M

INNER JOIN FLATTENED_REDEMPTIONS R
    ON M.MEMBER_ID = R.MEMBER_ID

ORDER BY R.TXN_DATE;
