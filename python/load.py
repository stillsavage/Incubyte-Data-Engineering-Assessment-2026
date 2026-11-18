
import os
import logging
import re
from pathlib import Path

import pandas as pd
import snowflake.connector

from snowflake.connector.pandas_tools import write_pandas
from dotenv import load_dotenv

from .extract import (
    extract_member_data,
    extract_excel_member_data,
    extract_redemption_data
)

from .transform import (
    transform_member_data,
    transform_redemption_data
)


# --------------------------------------------------
# 1. PROJECT CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

SNOWFLAKE_CONFIG = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    "role": os.getenv("SNOWFLAKE_ROLE")
}

MEMBER_TABLE = os.getenv("SNOWFLAKE_MEMBER_TABLE", "MEMBERS")
REDEMPTION_TABLE = os.getenv(
    "SNOWFLAKE_REDEMPTION_TABLE",
    "REDEMPTIONS"
)

COUNTRY_TABLES = {
    "USA": "MEMBERS_USA",
    "IND": "MEMBERS_IND",
    "PHIL": "MEMBERS_PHIL",
    "CAN": "MEMBERS_CAN",
    "AU": "MEMBERS_AU"
}

MEMBER_COLUMNS = [
    "MEMBER_NAME",
    "MEMBER_ID",
    "ENROLLMENT_DATE",
    "LAST_FLIGHT_DATE",
    "TIER_CODE",
    "AGENT_NAME",
    "STATE",
    "COUNTRY",
    "DOB",
    "IS_ACTIVE",
    "AGE",
    "STALE_MEMBER"
]

REDEMPTION_COLUMNS = [
    "TXN_ID",
    "TXN_DATE",
    "PARTNER",
    "MILES_REDEEMED",
    "STATUS",
    "MEMBER_ID",
    "FEED_DATE"
]


# --------------------------------------------------
# 2. VALIDATE CONFIGURATION
# --------------------------------------------------

def validate_config():

    required_fields = [
        "account",
        "user",
        "password",
        "warehouse",
        "database",
        "schema"
    ]

    missing = [
        field.upper()
        for field in required_fields
        if not SNOWFLAKE_CONFIG.get(field)
    ]

    if missing:
        raise ValueError(
            "Missing Snowflake configuration: "
            + ", ".join(missing)
        )

    all_tables = [
        MEMBER_TABLE,
        REDEMPTION_TABLE,
        *COUNTRY_TABLES.values()
    ]

    for table in all_tables:
        if not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_$]*",
            table
        ):
            raise ValueError(f"Invalid table name: {table}")


# --------------------------------------------------
# 3. SNOWFLAKE CONNECTION
# --------------------------------------------------

def get_snowflake_connection():

    validate_config()

    logging.info("Connecting to Snowflake")

    connection = snowflake.connector.connect(
        **{
            key: value
            for key, value in SNOWFLAKE_CONFIG.items()
            if value
        }
    )

    logging.info("Snowflake connection successful")

    return connection


# --------------------------------------------------
# 4. PREPARE DATAFRAME
# --------------------------------------------------

def prepare_dataframe(df):

    df = df.copy()

    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            df[column] = df[column].dt.date

    return df.astype(object).where(pd.notna(df), None)


# --------------------------------------------------
# 5. PREPARE MEMBER DATA
# --------------------------------------------------


def prepare_member_data(df):

    df = df.copy()

    # Keep only records that passed transformation validations.
    if "Is_Valid" in df.columns:
        valid = (
            df["Is_Valid"]
            .astype("string")
            .str.lower()
            .eq("true")
        )
        df = df.loc[valid].copy()

    # The assessment identifies MEMBER_NAME as the member key.
    # The transform step has already selected the latest source record.
    if "Is_Duplicate_Source_Record" in df.columns:
        duplicate = (
            df["Is_Duplicate_Source_Record"]
            .astype("string")
            .str.lower()
            .eq("true")
        )
        df = df.loc[~duplicate].copy()

    column_mapping = {
        "Member_Name": "MEMBER_NAME",
        "Member_Id": "MEMBER_ID",
        "Enrollment_Date": "ENROLLMENT_DATE",
        "Last_Flight_Date": "LAST_FLIGHT_DATE",
        "Tier_Code": "TIER_CODE",
        "Agent_Name": "AGENT_NAME",
        "State": "STATE",
        "Country": "COUNTRY",
        "DOB": "DOB",
        "Is_Active": "IS_ACTIVE",
        "Age": "AGE",
        "Stale_Member": "STALE_MEMBER"
    }

    df = df.rename(columns=column_mapping)

    for column in MEMBER_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    df = df[MEMBER_COLUMNS].copy()

    df["MEMBER_NAME"] = (
        df["MEMBER_NAME"]
        .astype("string")
        .str.strip()
    )

    df["MEMBER_ID"] = (
        df["MEMBER_ID"]
        .astype("string")
        .str.strip()
    )

    df["COUNTRY"] = (
        df["COUNTRY"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df["ENROLLMENT_DATE"] = pd.to_datetime(
        df["ENROLLMENT_DATE"],
        errors="coerce"
    )

    df["LAST_FLIGHT_DATE"] = pd.to_datetime(
        df["LAST_FLIGHT_DATE"],
        errors="coerce"
    )

    # Normalize the assessment key for case-insensitive matching.
    member_name_key = df["MEMBER_NAME"].str.strip().str.upper()
    missing_name = member_name_key.isna() | member_name_key.eq("")
    df = df.loc[~missing_name].copy()
    member_name_key = member_name_key.loc[~missing_name]

    duplicate_count = int(member_name_key.duplicated(keep=False).sum())
    if duplicate_count:
        logging.warning(
            "Duplicate MEMBER_NAME keys detected before final deduplication: %d records",
            duplicate_count
        )

    # Safety net: latest enrollment / flight record wins for each name.
    df = df.assign(_MEMBER_NAME_KEY=member_name_key)
    df = df.sort_values(
        ["ENROLLMENT_DATE", "LAST_FLIGHT_DATE"],
        ascending=[False, False],
        na_position="last",
        kind="mergesort"
    )
    df = df.drop_duplicates(
        subset=["_MEMBER_NAME_KEY"],
        keep="first"
    ).drop(columns=["_MEMBER_NAME_KEY"])

    logging.info(
        "Member records prepared for Snowflake: %d",
        len(df)
    )

    return prepare_dataframe(df)


# --------------------------------------------------
# 6. PREPARE REDEMPTION DATA
# --------------------------------------------------

def prepare_redemption_data(df):

    df = df.copy()

    if "Is_Valid" in df.columns:
        valid = (
            df["Is_Valid"]
            .astype("string")
            .str.lower()
            .eq("true")
        )
        df = df.loc[valid].copy()

    if "Is_Duplicate_Transaction" in df.columns:
        duplicate = (
            df["Is_Duplicate_Transaction"]
            .astype("string")
            .str.lower()
            .eq("true")
        )
        df = df.loc[~duplicate].copy()

    column_mapping = {
        "txn_id": "TXN_ID",
        "txn_date": "TXN_DATE",
        "partner": "PARTNER",
        "miles_redeemed": "MILES_REDEEMED",
        "status": "STATUS",
        "member_id": "MEMBER_ID",
        "feed_date": "FEED_DATE"
    }

    df = df.rename(columns=column_mapping)

    for column in REDEMPTION_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    df = df[REDEMPTION_COLUMNS].copy()

    df = df.drop_duplicates(
        subset=["TXN_ID"],
        keep="last"
    )

    return prepare_dataframe(df)


# --------------------------------------------------
# 7. WRITE DATA TO TEMPORARY STAGING TABLE
# --------------------------------------------------

def write_to_staging(
    connection,
    df,
    target_table,
    staging_table
):

    database = SNOWFLAKE_CONFIG["database"]
    schema = SNOWFLAKE_CONFIG["schema"]

    if df.empty:
        logging.warning(
            "No records available for %s",
            target_table
        )
        return 0

    cursor = connection.cursor()

    try:
        cursor.execute(
            f"CREATE OR REPLACE TEMPORARY TABLE "
            f"{staging_table} "
            f"LIKE {database}.{schema}.{target_table}"
        )

    finally:
        cursor.close()

    success, nchunks, nrows, output = write_pandas(
        conn=connection,
        df=df,
        table_name=staging_table,
        database=database,
        schema=schema,
        auto_create_table=False,
        overwrite=False,
        quote_identifiers=False
    )

    if not success or nrows != len(df):
        raise RuntimeError(
            f"Staging load failed for {target_table}. "
            f"Expected {len(df)}, loaded {nrows}. "
            f"Details: {output}"
        )

    logging.info(
        "Loaded %d records into staging table %s",
        nrows,
        staging_table
    )

    return nrows


# --------------------------------------------------
# 8. MERGE MEMBERS INTO A TARGET TABLE
# --------------------------------------------------


def merge_members_to_table(
    connection,
    df,
    target_table
):

    if df.empty:
        logging.warning(
            "No member records for %s",
            target_table
        )
        return 0

    staging_table = "STG_MEMBERS_LOAD"

    write_to_staging(
        connection,
        df,
        target_table,
        staging_table
    )

    database = SNOWFLAKE_CONFIG["database"]
    schema = SNOWFLAKE_CONFIG["schema"]

    update_columns = [
        column
        for column in MEMBER_COLUMNS
        if column != "MEMBER_NAME"
    ]

    update_clause = ", ".join(
        f"T.{column} = S.{column}"
        for column in update_columns
    )

    insert_columns = ", ".join(MEMBER_COLUMNS)

    insert_values = ", ".join(
        f"S.{column}"
        for column in MEMBER_COLUMNS
    )

    sql = f"""
        MERGE INTO {database}.{schema}.{target_table} T
        USING {staging_table} S
        ON UPPER(TRIM(T.MEMBER_NAME)) =
           UPPER(TRIM(S.MEMBER_NAME))

        WHEN MATCHED THEN UPDATE SET
            {update_clause}

        WHEN NOT MATCHED THEN INSERT
            ({insert_columns})
        VALUES
            ({insert_values})
    """

    cursor = connection.cursor()

    try:
        cursor.execute(sql)

        logging.info(
            "Member MERGE completed for %s",
            target_table
        )

    finally:
        cursor.close()

    return len(df)


# --------------------------------------------------
# 9. COUNTRY-WISE MEMBER LOADING
# --------------------------------------------------



def merge_country_members(connection, member_df):

    total_loaded = 0

    if member_df.empty:
        logging.warning("No member records for country loading")
        return 0

    database = SNOWFLAKE_CONFIG["database"]
    schema = SNOWFLAKE_CONFIG["schema"]

    cursor = connection.cursor()

    try:
        for country, target_table in COUNTRY_TABLES.items():

            sql = f"""
                DELETE FROM {database}.{schema}.{target_table} T
                USING {database}.{schema}.STG_MEMBERS_LOAD S
                WHERE UPPER(TRIM(T.MEMBER_NAME)) =
                      UPPER(TRIM(S.MEMBER_NAME))
                  AND (
                      S.COUNTRY IS NULL
                      OR UPPER(TRIM(S.COUNTRY)) <> '{country}'
                  )
            """

            cursor.execute(sql)

    finally:
        cursor.close()

    for country, target_table in COUNTRY_TABLES.items():

        country_df = member_df.loc[
            member_df["COUNTRY"].astype("string").str.strip().str.upper().eq(country)
        ].copy()

        if country_df.empty:
            continue

        loaded = merge_members_to_table(
            connection,
            country_df,
            target_table
        )

        total_loaded += loaded

    supported_countries = list(COUNTRY_TABLES.keys())

    unsupported = member_df[
        ~member_df["COUNTRY"].isin(supported_countries)
    ]

    if not unsupported.empty:
        logging.warning(
            "Unsupported or missing country records: %d",
            len(unsupported)
        )

    return total_loaded


# --------------------------------------------------
# 10. MERGE REDEMPTIONS
# --------------------------------------------------

def merge_redemptions(connection, df):

    if df.empty:
        logging.warning("No redemption records to merge")
        return 0

    staging_table = "STG_REDEMPTIONS_LOAD"

    write_to_staging(
        connection,
        df,
        REDEMPTION_TABLE,
        staging_table
    )

    database = SNOWFLAKE_CONFIG["database"]
    schema = SNOWFLAKE_CONFIG["schema"]

    update_columns = [
        column
        for column in REDEMPTION_COLUMNS
        if column != "TXN_ID"
    ]

    update_clause = ", ".join(
        f"T.{column} = S.{column}"
        for column in update_columns
    )

    insert_columns = ", ".join(REDEMPTION_COLUMNS)

    insert_values = ", ".join(
        f"S.{column}"
        for column in REDEMPTION_COLUMNS
    )

    sql = f"""
        MERGE INTO {database}.{schema}.{REDEMPTION_TABLE} T
        USING {staging_table} S
        ON T.TXN_ID = S.TXN_ID

        WHEN MATCHED THEN UPDATE SET
            {update_clause}

        WHEN NOT MATCHED THEN INSERT
            ({insert_columns})
        VALUES
            ({insert_values})
    """

    cursor = connection.cursor()

    try:
        cursor.execute(sql)
        logging.info("Redemptions MERGE completed")

    finally:
        cursor.close()

    return len(df)


# --------------------------------------------------
# 11. MAIN LOAD PROCESS
# --------------------------------------------------

def load_data(member_df, redemption_df):

    connection = None

    try:
        connection = get_snowflake_connection()

        member_data = prepare_member_data(member_df)

        redemption_data = prepare_redemption_data(
            redemption_df
        )

        logging.info(
            "Valid member records ready: %d",
            len(member_data)
        )

        logging.info(
            "Valid redemption records ready: %d",
            len(redemption_data)
        )

        # Master member table
        master_count = merge_members_to_table(
            connection,
            member_data,
            MEMBER_TABLE
        )

        # Country-specific member tables
        country_count = merge_country_members(
            connection,
            member_data
        )

        # Redemption table
        redemption_count = merge_redemptions(
            connection,
            redemption_data
        )

        connection.commit()

        return {
            "members_processed": master_count,
            "country_records_processed": country_count,
            "redemptions_processed": redemption_count
        }

    except Exception:

        if connection is not None:
            connection.rollback()

        logging.exception("Snowflake loading failed")
        raise

    finally:

        if connection is not None:
            connection.close()
            logging.info("Snowflake connection closed")


# --------------------------------------------------
# 12. COMPLETE ETL PIPELINE
# --------------------------------------------------

if __name__ == "__main__":

    try:
        logging.info(
            "========== ETL PIPELINE STARTED =========="
        )

        # Extract flat-file members
        flat_member_df = extract_member_data()

        # Extract Excel members
        excel_member_df = extract_excel_member_data()

        # Combine member sources
        member_df = pd.concat(
            [flat_member_df, excel_member_df],
            ignore_index=True,
            sort=False
        )

        logging.info(
            "Total member records extracted: %d",
            len(member_df)
        )

        # Extract redemption data
        redemption_df = extract_redemption_data()

        # Transform members
        transformed_members = transform_member_data(
            member_df
        )

        # Transform redemptions
        transformed_redemptions = transform_redemption_data(
            redemption_df
        )

        # Load into Snowflake
        result = load_data(
            transformed_members,
            transformed_redemptions
        )

        print("\n========== ETL LOAD SUMMARY ==========")

        print(
            f"Members processed: "
            f"{result['members_processed']}"
        )

        print(
            f"Country table records processed: "
            f"{result['country_records_processed']}"
        )

        print(
            f"Redemptions processed: "
            f"{result['redemptions_processed']}"
        )

        logging.info(
            "========== ETL PIPELINE COMPLETED =========="
        )

    except Exception:
        logging.exception(
            "ETL pipeline execution failed"
        )
        raise