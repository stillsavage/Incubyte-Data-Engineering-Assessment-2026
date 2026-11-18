
import logging
import pandas as pd

from .extract import (
    extract_member_data,
    extract_excel_member_data,
    extract_redemption_data
)

from .transform import (
    transform_member_data,
    transform_redemption_data
)

from .load import load_data


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def run_pipeline():

    logging.info("========== ETL PIPELINE STARTED ==========")

    # 1. EXTRACT MEMBER DATA
    logging.info("Starting member data extraction")

    flat_members = extract_member_data()
    excel_members = extract_excel_member_data()

    member_df = pd.concat(
        [flat_members, excel_members],
        ignore_index=True,
        sort=False
    )

    logging.info(
        "Total member records extracted: %d",
        len(member_df)
    )

    # 2. EXTRACT REDEMPTION DATA
    logging.info("Starting redemption data extraction")

    redemption_df = extract_redemption_data()

    # 3. TRANSFORM MEMBER DATA
    logging.info("Starting member transformation")

    transformed_members = transform_member_data(member_df)

    # 4. TRANSFORM REDEMPTION DATA
    logging.info("Starting redemption transformation")

    transformed_redemptions = transform_redemption_data(
        redemption_df
    )

    # 5. LOAD DATA INTO SNOWFLAKE
    logging.info("Starting Snowflake loading")

    result = load_data(
        transformed_members,
        transformed_redemptions
    )

    # 6. EXECUTION SUMMARY
    print("\n========== ETL PIPELINE SUMMARY ==========")

    print(f"Members processed: {result['members_processed']}")

    print(
        "Country table records processed: "
        f"{result['country_records_processed']}"
    )

    print(
        f"Redemptions processed: "
        f"{result['redemptions_processed']}"
    )

    logging.info("========== ETL PIPELINE COMPLETED ==========")

    return result


if __name__ == "__main__":

    try:
        run_pipeline()

    except Exception:
        logging.exception("ETL pipeline execution failed")
        raise
