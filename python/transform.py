
import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from .extract import (
    extract_member_data,
    extract_excel_member_data,
    extract_redemption_data,
    PROCESSED_DIR
)


# ============================================================
# 1. LOGGING CONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# ============================================================
# 2. CLEAN STRING COLUMNS
# ============================================================

def clean_string_columns(df):
    df = df.copy()

    for column in df.columns:
        if (
            pd.api.types.is_string_dtype(df[column].dtype)
            or df[column].dtype == object
        ):
            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )

    return df


# ============================================================
# 3. SAFE DATE CONVERSION
# ============================================================

def convert_date_column(df, column, date_format=None):
    if column not in df.columns:
        return df

    def parse_date(value):
        if pd.isna(value):
            return pd.NaT

        if isinstance(value, (pd.Timestamp, datetime, date)):
            return pd.to_datetime(value, errors="coerce")

        value_str = str(value).strip()

        if not value_str:
            return pd.NaT

        if date_format and value_str.isdigit():
            return pd.to_datetime(
                value_str,
                format=date_format,
                errors="coerce"
            )

        return pd.to_datetime(
            value_str,
            errors="coerce"
        )

    df[column] = pd.to_datetime(
        df[column].apply(parse_date),
        errors="coerce"
    )

    return df


# ============================================================
# 4. CALCULATE AGE
# ============================================================

def calculate_age(dob, today):
    if pd.isna(dob):
        return None

    dob = pd.Timestamp(dob)

    if dob > today:
        return None

    age = today.year - dob.year

    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1

    return age


# ============================================================
# 5. TRANSFORM MEMBER DATA
# ============================================================

def transform_member_data(df):

    try:
        logging.info("Starting member data transformation")

        df = df.copy()

        df.columns = (
            df.columns.astype(str).str.strip()
        )

        # Remove record markers if present
        for marker in ["H", "D"]:
            if marker in df.columns:
                df.drop(columns=[marker], inplace=True)

        # Clean string values
        df = clean_string_columns(df)

        # Standardize Member ID
        if "Member_Id" in df.columns:
            df["Member_Id"] = (
                df["Member_Id"]
                .astype("string")
                .str.strip()
            )

        # Standardize country values
        if "Country" in df.columns:
            df["Country"] = (
                df["Country"]
                .astype("string")
                .str.strip()
                .str.upper()
            )
        else:
            df["Country"] = pd.NA

        # Convert date columns
        df = convert_date_column(
            df, "Enrollment_Date", "%Y%m%d"
        )

        df = convert_date_column(
            df, "Last_Flight_Date", "%Y%m%d"
        )

        df = convert_date_column(
            df, "DOB", "%m%d%Y"
        )

        today = pd.Timestamp.today().normalize()

        # ----------------------------------------------------
        # AGE CALCULATION
        # ----------------------------------------------------

        if "DOB" in df.columns:
            ages = [
                calculate_age(dob, today)
                for dob in df["DOB"]
            ]

            df["Age"] = pd.array(
                ages,
                dtype="Int64"
            )
        else:
            df["Age"] = pd.array(
                [None] * len(df),
                dtype="Int64"
            )

        # ----------------------------------------------------
        # STALE MEMBER CALCULATION
        # Stale = Y when days since last flight > 90
        # Missing flight date remains NULL
        # ----------------------------------------------------

        if "Last_Flight_Date" in df.columns:

            days_since_flight = (
                today - df["Last_Flight_Date"]
            ).dt.days

            stale_flags = []

            for days in days_since_flight:
                if pd.isna(days) or days < 0:
                    stale_flags.append(None)

                elif days > 90:
                    stale_flags.append("Y")

                else:
                    stale_flags.append("N")

            df["Stale_Member"] = pd.array(
                stale_flags,
                dtype="string"
            )

        else:
            df["Stale_Member"] = pd.array(
                [None] * len(df),
                dtype="string"
            )

        # ----------------------------------------------------
        # MEMBER IDENTITY — ASSESSMENT KEY: MEMBER_NAME
        # Latest record wins for duplicate member names.
        # ----------------------------------------------------

        if "Member_Name" in df.columns:
            member_names = (
                df["Member_Name"]
                .astype("string")
                .str.strip()
                .str.upper()
            )
        else:
            member_names = pd.Series(
                pd.NA, index=df.index, dtype="string"
            )

        df["Member_Key"] = member_names

        missing_member_name = (
            member_names.isna() | member_names.eq("")
        )
        df.loc[missing_member_name, "Member_Key"] = pd.NA

        df["Identity_Resolution_Status"] = pd.array(
            [
                "MISSING_MEMBER_NAME" if missing else "MEMBER_NAME_KEY"
                for missing in missing_member_name
            ],
            dtype="string"
        )

        # Sort newest records first so duplicate detection keeps
        # the latest enrollment record (then latest flight date).
        sort_columns = [
            column for column in ["Enrollment_Date", "Last_Flight_Date"]
            if column in df.columns
        ]
        if sort_columns:
            df = df.sort_values(
                sort_columns,
                ascending=[False] * len(sort_columns),
                na_position="last"
            )

        # ----------------------------------------------------
        # MEMBER DATA QUALITY VALIDATION
        # Mandatory: Member_Id, Member_Name, Enrollment_Date
        # DOB, Country and Last_Flight_Date are optional
        # ----------------------------------------------------

        mandatory_columns = [
            "Member_Id",
            "Member_Name",
            "Enrollment_Date"
        ]

        quality_issues = []

        for _, row in df.iterrows():

            issues = []

            for column in mandatory_columns:

                if column not in df.columns:
                    issues.append(
                        f"MISSING_COLUMN_{column}"
                    )

                elif (
                    pd.isna(row[column])
                    or str(row[column]).strip() == ""
                ):
                    issues.append(
                        f"MISSING_{column}"
                    )

            # Future enrollment date
            if (
                "Enrollment_Date" in df.columns
                and pd.notna(row["Enrollment_Date"])
                and row["Enrollment_Date"] > today
            ):
                issues.append("FUTURE_ENROLLMENT_DATE")

            # Future DOB is invalid when DOB is provided
            if (
                "DOB" in df.columns
                and pd.notna(row["DOB"])
                and row["DOB"] > today
            ):
                issues.append("FUTURE_DOB")

            # Future flight date is invalid when provided
            if (
                "Last_Flight_Date" in df.columns
                and pd.notna(row["Last_Flight_Date"])
                and row["Last_Flight_Date"] > today
            ):
                issues.append("FUTURE_LAST_FLIGHT_DATE")

            quality_issues.append(
                "|".join(issues) if issues else "VALID"
            )

        df["Data_Quality_Issues"] = quality_issues

        df["Is_Valid"] = (
            df["Data_Quality_Issues"] == "VALID"
        )

        # ----------------------------------------------------
        # DUPLICATE MEMBER CHECK
        # Keep the latest record for each assessment key.
        # Missing member names are not treated as duplicates.
        # ----------------------------------------------------

        df["Is_Duplicate_Source_Record"] = (
            df.duplicated(
                subset=["Member_Key"],
                keep="first"
            )
            & df["Member_Key"].notna()
        )

        df = df.reset_index(drop=True)

        # ----------------------------------------------------
        # MEMBER TRANSFORMATION SUMMARY
        # ----------------------------------------------------

        logging.info(
            "Member transformation completed: %d records",
            len(df)
        )

        logging.info(
            "Valid member records: %d",
            int(df["Is_Valid"].sum())
        )

        logging.info(
            "Invalid member records: %d",
            int((~df["Is_Valid"]).sum())
        )

        logging.info(
            "Duplicate member records: %d",
            int(df["Is_Duplicate_Source_Record"].sum())
        )

        return df

    except Exception:
        logging.exception(
            "Member data transformation failed"
        )
        raise


# ============================================================
# 6. TRANSFORM REDEMPTION DATA
# ============================================================

def transform_redemption_data(df):

    try:
        logging.info("Starting redemption data transformation")

        df = df.copy()

        df.columns = (
            df.columns.astype(str).str.strip()
        )

        df = clean_string_columns(df)

        if "member_id" in df.columns:
            df["member_id"] = (
                df["member_id"]
                .astype("string")
                .str.strip()
            )

        # Convert transaction date
        df = convert_date_column(
            df, "txn_date", "%Y%m%d"
        )

        # Convert feed date
        df = convert_date_column(
            df, "feed_date", "%Y%m%d"
        )

        # Convert miles to numeric
        if "miles_redeemed" in df.columns:
            df["miles_redeemed"] = pd.to_numeric(
                df["miles_redeemed"],
                errors="coerce"
            ).astype("Int64")
        else:
            df["miles_redeemed"] = pd.array(
                [None] * len(df),
                dtype="Int64"
            )

        # Normalize status
        if "status" in df.columns:
            df["status"] = (
                df["status"]
                .astype("string")
                .str.upper()
                .str.strip()
            )

        # Ensure mandatory columns exist
        mandatory_columns = [
            "txn_id",
            "member_id",
            "txn_date",
            "miles_redeemed"
        ]

        for column in mandatory_columns:
            if column not in df.columns:
                df[column] = pd.NA

        # ----------------------------------------------------
        # REDEMPTION DATA QUALITY VALIDATION
        # ----------------------------------------------------

        df["Is_Valid"] = (
            df["txn_id"].notna()
            & df["member_id"].notna()
            & df["txn_date"].notna()
            & df["miles_redeemed"].notna()
            & df["txn_id"].astype("string").str.strip().ne("")
            & df["member_id"].astype("string").str.strip().ne("")
            & df["miles_redeemed"].ge(0).fillna(False)
        )

        # ----------------------------------------------------
        # DUPLICATE TRANSACTION CHECK
        # ----------------------------------------------------

        df["Is_Duplicate_Transaction"] = (
            df.duplicated(
                subset=["txn_id"],
                keep="first"
            )
            & df["txn_id"].notna()
        )

        df = df.reset_index(drop=True)

        logging.info(
            "Redemption transformation completed: %d records",
            len(df)
        )

        logging.info(
            "Valid redemption records: %d",
            int(df["Is_Valid"].sum())
        )

        logging.info(
            "Invalid redemption records: %d",
            int((~df["Is_Valid"]).sum())
        )

        logging.info(
            "Duplicate redemption records: %d",
            int(df["Is_Duplicate_Transaction"].sum())
        )

        return df

    except Exception:
        logging.exception(
            "Redemption data transformation failed"
        )
        raise


# ============================================================
# 7. MAIN EXECUTION
# ============================================================

if __name__ == "__main__":

    try:
        logging.info(
            "========== TRANSFORMATION STARTED =========="
        )

        # Extract flat-file members
        flat_member_df = extract_member_data()

        # Extract Excel members
        excel_member_df = extract_excel_member_data()

        # Combine member sources
        all_member_df = pd.concat(
            [
                flat_member_df,
                excel_member_df
            ],
            ignore_index=True,
            sort=False
        )

        logging.info(
            "Total extracted member records: %d",
            len(all_member_df)
        )

        # Extract redemption data
        redemption_df = extract_redemption_data()

        # Transform members
        transformed_members = transform_member_data(
            all_member_df
        )

        # Transform redemptions
        transformed_redemptions = transform_redemption_data(
            redemption_df
        )

        # Separate valid and rejected members
        valid_members = transformed_members[
            transformed_members["Is_Valid"]
            & ~transformed_members["Is_Duplicate_Source_Record"]
        ].copy()

        rejected_members = transformed_members[
            (~transformed_members["Is_Valid"])
            | transformed_members["Is_Duplicate_Source_Record"]
        ].copy()

        # Separate valid and rejected redemptions
        valid_redemptions = transformed_redemptions[
            transformed_redemptions["Is_Valid"]
            & ~transformed_redemptions["Is_Duplicate_Transaction"]
        ].copy()

        rejected_redemptions = transformed_redemptions[
            (~transformed_redemptions["Is_Valid"])
            | transformed_redemptions["Is_Duplicate_Transaction"]
        ].copy()

        # Create processed directory
        PROCESSED_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        # Save member outputs
        valid_members.to_csv(
            PROCESSED_DIR / "valid_members.csv",
            index=False
        )

        rejected_members.to_csv(
            PROCESSED_DIR / "rejected_members.csv",
            index=False
        )

        # Save redemption outputs
        valid_redemptions.to_csv(
            PROCESSED_DIR / "transformed_redemptions.csv",
            index=False
        )

        rejected_redemptions.to_csv(
            PROCESSED_DIR / "rejected_redemptions.csv",
            index=False
        )

        logging.info(
            "Processed CSV files saved successfully"
        )

        # ----------------------------------------------------
        # DISPLAY MEMBER SUMMARY
        # ----------------------------------------------------

        print("\n========== MEMBER DATA QUALITY SUMMARY ==========")

        print(
            transformed_members[
                "Data_Quality_Issues"
            ].value_counts(dropna=False)
        )

        print("\n========== MEMBER RECORD SUMMARY ==========")

        print(f"Total extracted members: {len(transformed_members)}")
        print(f"Valid members: {len(valid_members)}")
        print(f"Rejected members: {len(rejected_members)}")

        # ----------------------------------------------------
        # DISPLAY REDEMPTION SUMMARY
        # ----------------------------------------------------

        print("\n========== REDEMPTION DATA SUMMARY ==========")

        print(f"Total redemptions: {len(transformed_redemptions)}")
        print(f"Valid redemptions: {len(valid_redemptions)}")
        print(f"Rejected redemptions: {len(rejected_redemptions)}")

        print("\n========== TRANSFORMED REDEMPTIONS ==========")

        print(
            valid_redemptions.to_string(index=False)
        )

        logging.info(
            "========== TRANSFORMATION COMPLETED =========="
        )

    except Exception:
        logging.exception(
            "Transformation process failed"
        )
        raise
