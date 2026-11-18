
import pandas as pd
import json
import logging
from pathlib import Path


# --------------------------------------------------
# 1. PROJECT CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# Input files
MEMBER_FILE = BASE_DIR / "data" / "raw" / "members_20240115.txt"
REDEMPTION_FILE = BASE_DIR / "data" / "raw" / "redemptions_20240115.json"

AUS_FILE = BASE_DIR / "data" / "raw" / "AUS.xlsx"
USA_FILE = BASE_DIR / "data" / "raw" / "USA.xlsx"
IND_FILE = BASE_DIR / "data" / "raw" / "IND.xlsx"

# Output directory
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. LOGGING CONFIGURATION
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# --------------------------------------------------
# 3. EXTRACT MEMBER DATA FROM FLAT FILE
# --------------------------------------------------

def extract_member_data():
    """Extract member records from pipe-delimited flat file."""

    try:
        logging.info("Starting flat file member extraction")

        if not MEMBER_FILE.exists():
            raise FileNotFoundError(
                f"Member file not found: {MEMBER_FILE}"
            )

        with open(MEMBER_FILE, "r", encoding="utf-8") as file:
            lines = [
                line.strip()
                for line in file
                if line.strip()
            ]

        if not lines:
            raise ValueError("Member file is empty")

        # Extract header
        header = lines[0].strip("|").split("|")

        if header[0] == "H":
            header = header[1:]

        records = []

        # Extract detail records
        for line in lines[1:]:

            values = line.strip("|").split("|")

            if values[0] == "D":
                values = values[1:]

            if len(values) != len(header):
                logging.warning(
                    "Skipping invalid member record: %s",
                    line
                )
                continue

            records.append(dict(zip(header, values)))

        df = pd.DataFrame(records)

        logging.info(
            "Extracted %d flat file member records",
            len(df)
        )

        return df

    except Exception:
        logging.exception("Flat file member extraction failed")
        raise


# --------------------------------------------------
# 4. EXTRACT MEMBER DATA FROM EXCEL FILES
# --------------------------------------------------

def extract_excel_member_data():
    """
    Extract member records from USA, India and Australia Excel files.
    Standardize column names and date formats.
    """

    try:
        logging.info("Starting Excel member extraction")

        file_configs = [
            (AUS_FILE, "AU"),
            (USA_FILE, "USA"),
            (IND_FILE, "IND")
        ]

        column_mappings = {
            "Unique ID": "Member_Id",
            "ID": "Member_Id",
            "Member Name": "Member_Name",
            "Name": "Member_Name",
            "Tier Type": "Tier_Code",
            "TierCode": "Tier_Code",
            "Tier Code": "Tier_Code",
            "Date of Birth": "DOB",
            "DOB": "DOB",
            "Date of Enrollment": "Enrollment_Date",
            "EnrollmentDate": "Enrollment_Date",
            "Date of Flight": "Last_Flight_Date",
            "FlightDate": "Last_Flight_Date",
            "Flight Date": "Last_Flight_Date"
        }

        required_columns = [
            "Member_Id",
            "Member_Name",
            "Tier_Code",
            "Enrollment_Date",
            "Last_Flight_Date",
            "DOB"
        ]

        all_members = []

        for file_path, country in file_configs:

            logging.info(
                "Reading Excel file: %s",
                file_path.name
            )

            if not file_path.exists():
                raise FileNotFoundError(
                    f"Excel file not found: {file_path}"
                )

            df = pd.read_excel(file_path)

            # Clean column names
            df.columns = df.columns.astype(str).str.strip()

            # Standardize column names
            df.rename(
                columns=column_mappings,
                inplace=True
            )

            # Add missing standard columns
            for column in required_columns:
                if column not in df.columns:
                    df[column] = pd.NA

            # Convert member ID to string
            df["Member_Id"] = (
                df["Member_Id"]
                .astype("string")
                .str.strip()
            )

            # --------------------------------------------------
            # USA DATE PARSING
            # USA dates are stored as numeric MDDYYYY / MMDDYYYY
            # --------------------------------------------------

            if country == "USA":

                for column in [
                    "Enrollment_Date",
                    "Last_Flight_Date"
                ]:

                    original_values = df[column].copy()

                    values = (
                        original_values
                        .astype("string")
                        .str.strip()
                        .str.replace(r"\.0$", "", regex=True)
                    )

                    parsed_values = pd.to_datetime(
                        values.str.zfill(8),
                        format="%m%d%Y",
                        errors="coerce"
                    )

                    # Identify invalid non-empty dates
                    df[f"{column}_Invalid"] = (
                        original_values.notna()
                        & values.ne("")
                        & parsed_values.isna()
                    )

                    df[column] = parsed_values

                # Parse DOB separately
                original_dob = df["DOB"].copy()

                parsed_dob = pd.to_datetime(
                    original_dob,
                    errors="coerce"
                )

                df["DOB_Invalid"] = (
                    original_dob.notna()
                    & original_dob.astype("string").str.strip().ne("")
                    & parsed_dob.isna()
                )

                df["DOB"] = parsed_dob

            # --------------------------------------------------
            # AUSTRALIA AND INDIA DATE PARSING
            # --------------------------------------------------

            else:

                for column in [
                    "DOB",
                    "Enrollment_Date",
                    "Last_Flight_Date"
                ]:

                    original_values = df[column].copy()

                    parsed_values = pd.to_datetime(
                        original_values,
                        errors="coerce"
                    )

                    # Identify invalid non-empty dates
                    df[f"{column}_Invalid"] = (
                        original_values.notna()
                        & original_values.astype("string").str.strip().ne("")
                        & parsed_values.isna()
                    )

                    df[column] = parsed_values

            # --------------------------------------------------
            # ADD SOURCE INFORMATION
            # --------------------------------------------------

            df["Country"] = country
            df["Source_File"] = file_path.name

            all_members.append(df)

            logging.info(
                "Extracted %d records from %s",
                len(df),
                file_path.name
            )

        if not all_members:
            return pd.DataFrame()

        # Combine all country records
        result = pd.concat(
            all_members,
            ignore_index=True,
            sort=False
        )

        logging.info(
            "Total Excel member records extracted: %d",
            len(result)
        )

        return result

    except Exception:
        logging.exception("Excel member extraction failed")
        raise


# --------------------------------------------------
# 5. EXTRACT REDEMPTION DATA FROM JSON FILE
# --------------------------------------------------

def extract_redemption_data():
    """Extract redemption transactions from JSON feed."""

    try:
        logging.info("Starting redemption data extraction")

        if not REDEMPTION_FILE.exists():
            raise FileNotFoundError(
                f"Redemption file not found: {REDEMPTION_FILE}"
            )

        # Read JSON file
        with open(REDEMPTION_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Extract parent-level information
        member_id = data.get("member_id")
        feed_date = data.get("feed_date")

        # Extract transactions
        redemptions = data.get("redemptions", [])

        df = pd.DataFrame(redemptions)

        # Add parent-level information
        df["member_id"] = member_id
        df["feed_date"] = feed_date

        logging.info(
            "Extracted %d redemption records",
            len(df)
        )

        return df

    except Exception:
        logging.exception("Redemption data extraction failed")
        raise


# --------------------------------------------------
# 6. MAIN EXECUTION FOR EXTRACTION TESTING
# --------------------------------------------------

if __name__ == "__main__":

    print("\n========== FLAT FILE MEMBER DATA ==========")

    member_df = extract_member_data()
    print(member_df.to_string(index=False))

    print("\n========== EXCEL MEMBER DATA ==========")

    excel_member_df = extract_excel_member_data()
    print(excel_member_df.to_string(index=False))

    print("\n========== REDEMPTION JSON DATA ==========")

    redemption_df = extract_redemption_data()
    print(redemption_df.to_string(index=False))

    logging.info(
        "All source data extraction completed successfully"
    )
