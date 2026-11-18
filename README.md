# Incubyte Data Engineering Assessment

## 1. Project Overview

This project implements an end-to-end ETL pipeline for SkyPoints, a global airline loyalty program.

The pipeline processes member profile data and mileage redemption transactions received from multiple source formats. It uses Python, Pandas and Snowflake to extract, transform, validate and load the data.

The solution covers multi-source ingestion, data standardization, data quality validation, country-wise member processing, JSON transaction flattening and Snowflake integration.

## 2. Technologies Used

- Python
- Pandas
- Snowflake
- Snowflake SQL
- JSON
- Excel
- Pytest
- Git and GitHub

## 3. Project Structure

```text
INCUBYTE-DATA-ENGINEERING-ASSESSMENT/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── docs/
│   ├── data_dictionary.md
│   └── project_overview.md
│
├── python/
│   ├── extract.py
│   ├── transform.py
│   ├── load.py
│   └── main.py
│
├── sql/
│   ├── create_tables.sql
│   ├── 03_country_wise_tables.sql
│   ├── 04_redemption_json_flatten.sql
│   └── validation_queries.sql
│
├── tests/
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## 4. Data Sources

The pipeline processes the following source files:

**Member Profile Data**
- Pipe-delimited flat file containing member records.
- `AUS.xlsx` – Australia member records.
- `USA.xlsx` – USA member records.
- `IND.xlsx` – India member records.

**Redemption Transaction Data**
- JSON file containing mileage redemption transactions from partner airlines.

## 5. Data Processing

### Member Data

- Extract member records from the pipe-delimited text file.
- Extract country-specific member records from Excel files.
- Combine records from multiple sources.
- Standardize column names and string values.
- Convert enrollment date, last flight date and DOB into standard date formats.
- Calculate member age using DOB.
- Identify stale members when more than 90 days have passed since the last flight.
- Validate mandatory fields and identify invalid records.
- Identify duplicate member records using the assessment-defined `MEMBER_NAME` key.
- Retain the latest record based on enrollment date and last flight date.
- Separate valid and rejected member records.

### Redemption Data

- Read redemption transactions from the JSON source.
- Flatten nested transaction data into individual records.
- Extract transaction ID, transaction date, partner, miles redeemed, status, member ID and feed date.
- Validate mandatory transaction fields.
- Identify duplicate transaction IDs.
- Separate valid and rejected redemption records.

## 6. Member Identity and Country-wise Processing

The assessment identifies `Member_Name` as the key column. Accordingly, the implementation uses normalized `MEMBER_NAME` as the member matching key.

The latest record is retained when duplicate member names are found. This supports the assessment's requirement to retain the latest record when a member changes countries.

The pipeline maintains the following country-specific Snowflake tables:

- `MEMBERS_USA`
- `MEMBERS_IND`
- `MEMBERS_PHIL`
- `MEMBERS_CAN`
- `MEMBERS_AU`

Snowflake MERGE operations are used to insert new records and update existing records. When a member's latest record belongs to a different country, the previous country-table record is removed before loading the latest country assignment.

**Identity limitation:** `MEMBER_NAME` is the key specified in the assessment, but names are not guaranteed to be globally unique in a real-world system. A stable global member identifier would be preferable for production use.

## 7. Redemption-to-Member Association

Redemption records contain `MEMBER_ID`, which is used to associate transactions with member profiles.

The supplied sample demonstrates successful matching of both redemption transactions to Elena.

**Known limitation:** The sample Excel files reuse `MEMBER_ID` values across different countries. Therefore, joining on `MEMBER_ID` alone can produce ambiguous matches for some records. A stable global member identifier or an additional source-provided country/business key is required for reliable production-level association.

## 8. Data Quality Checks

The implementation and SQL validation scripts cover:

- Mandatory field validation.
- Missing member name, member ID and enrollment date checks.
- Duplicate member name checks.
- Duplicate redemption transaction checks.
- Invalid and future date checks.
- Invalid or negative miles validation.
- Member age calculation.
- Stale member identification.
- Country-wise record count reconciliation.
- Country-table mapping validation.
- Redemption transaction and member association checks.

Invalid and duplicate records are excluded from the final member load and retained in processed rejection outputs for review.

## 9. Environment Setup

Create and activate a Python virtual environment:

```bash
python -m venv .venv
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Configure Snowflake connection details in the `.env` file:

```text
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_WAREHOUSE=
SNOWFLAKE_DATABASE=
SNOWFLAKE_SCHEMA=
SNOWFLAKE_ROLE=
```

Do not commit `.env` or expose database credentials in version control.

## 10. Running the Pipeline

Create the required Snowflake tables by executing the table creation SQL script.

Run the complete Python ETL pipeline from the project root:

```bash
python -m python.main
```

The pipeline performs the following operations:

1. Extract member profile data from flat files and Excel sources.
2. Extract redemption transactions from JSON.
3. Transform and validate member and redemption records.
4. Save processed valid and rejected records.
5. Connect to Snowflake.
6. Load member records into the master table.
7. Load member records into country-specific tables.
8. Load redemption transactions into the redemption table.
9. Close the Snowflake connection.

The SQL scripts in the `sql/` directory provide table definitions, country-wise processing logic, JSON flattening examples and validation queries.

## 11. Latest Execution Results

The following results are from the latest successful ETL execution.

### Python Extraction and Transformation

| Dataset / Metric | Records |
|---|---:|
| Flat-file member records | 5 |
| Excel member records | 9 |
| Total extracted member records | 14 |
| Valid member records before deduplication | 13 |
| Invalid member records | 1 |
| Duplicate member records | 1 |
| Final member records prepared for loading | 12 |
| Redemption transactions extracted | 2 |
| Valid redemption transactions | 2 |
| Invalid redemption transactions | 0 |

One member record was rejected because its enrollment date was missing. One additional record was excluded as a duplicate based on the assessment-defined member key.

### Snowflake Loading Results

| Table / Metric | Records |
|---|---:|
| `MEMBERS` | 12 |
| `MEMBERS_USA` | 3 |
| `MEMBERS_IND` | 4 |
| `MEMBERS_PHIL` | 1 |
| `MEMBERS_CAN` | 1 |
| `MEMBERS_AU` | 3 |
| Total country-wise records | 12 |
| `REDEMPTIONS` | 2 |

The combined country-wise record count matches the master member table count.

### Automated Test Results

- Total tests executed: 4
- Passed: 4
- Failed: 0

### Database Validation Results

- No duplicate member names found in the master table.
- Country-wise record counts reconcile with the master table.
- No records were found in an incorrect country-specific table.
- Two unique redemption transaction IDs were loaded.
- No null transaction IDs were found.
- Age and stale-member fields were populated according to the transformation logic.

## 12. Scalability Considerations

For larger production workloads involving millions or billions of records:

- Use Snowflake bulk loading with staged files and `COPY INTO`.
- Implement incremental data ingestion and change data capture where appropriate.
- Apply deduplication using reliable business keys.
- Use Snowflake clustering and query optimization where appropriate.
- Monitor pipeline execution, failures and data quality metrics.
- Design loads to be idempotent and support safe retries.
- Consider parallel processing for high-volume data ingestion.

## 13. Security

- Store Snowflake credentials in environment variables.
- Keep `.env` excluded from version control.
- Avoid committing sensitive data or credentials.
- Use appropriate Snowflake roles and permissions.

## 14. Conclusion

This project demonstrates an end-to-end data engineering workflow covering multi-format data extraction, transformation, data quality validation, Snowflake integration, country-wise member organization and semi-structured JSON processing.

It also demonstrates automated testing, SQL-based validation, duplicate handling and considerations for building scalable and reliable data pipelines.