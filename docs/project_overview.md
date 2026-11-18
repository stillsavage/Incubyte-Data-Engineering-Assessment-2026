
# Incubyte Data Engineering Assessment

## 1. Project Overview

This project implements an ETL pipeline to extract, transform, validate, and load loyalty program member and redemption data into Snowflake.

The pipeline processes member data from flat files and Excel workbooks, along with redemption transactions from JSON files.

## 2. Source Data

The pipeline uses the following input files:

| Source File | Format | Description |
|---|---|---|
| members_20240115.txt | TXT | Member records in pipe-delimited format |
| AUS.xlsx | Excel | Australian member records |
| USA.xlsx | Excel | US member records |
| IND.xlsx | Excel | Indian member records |
| redemptions_20240115.json | JSON | Member redemption transactions |

## 3. Technology Stack

- Python
- Pandas
- Snowflake
- SQL
- JSON
- Excel
- Pytest

## 4. ETL Pipeline Architecture

### Extract
- Read member records from pipe-delimited text files.
- Read country-specific member records from Excel workbooks.
- Extract redemption transactions from JSON files.
- Standardize source column names.

### Transform
- Clean and standardize member records.
- Convert source date fields into valid date formats.
- Calculate member age using date of birth.
- Identify stale members based on more than 90 days since the last flight.
- Validate mandatory fields and identify duplicate records.
- Flatten JSON redemption transactions.

### Load
- Load validated member and redemption records into Snowflake staging tables.
- Use MERGE operations to load records into target tables.
- Maintain country-specific member tables.
- Load flattened redemption transactions into a queryable table.

## 5. Snowflake Data Model

The project uses the following tables:

### Main Tables
- MEMBERS
- REDEMPTIONS
- FLATTENED_REDEMPTIONS

### Staging Tables
- STG_MEMBERS_LOAD
- STG_REDEMPTIONS_LOAD

### Country-Specific Tables
- MEMBERS_USA
- MEMBERS_IND
- MEMBERS_PHIL
- MEMBERS_CAN
- MEMBERS_AU

## 6. Data Quality and Validation

The pipeline performs the following validations:

- Mandatory member field validation.
- Duplicate member key detection.
- Duplicate redemption transaction detection.
- Date format validation.
- Negative miles validation.
- Member age validation.
- Stale member identification.
- Redemption-to-member relationship validation.
- Country-wise record count reconciliation.

## 7. Execution Results

Latest successful transformation and load run:

| Metric | Result |
|---|---:|
| Total member records extracted | 14 |
| Valid member records | 13 |
| Rejected member records | 1 |
| Redemption records processed | 2 |
| Country table records loaded | 13 |

One member record was rejected due to a missing enrollment date.

## 8. Project Structure

```text
Incubyte-Data-Engineering-Assessment/
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
├── README.md
└── requirements.txt
```

## 9. Scalability Considerations

For larger data volumes, the pipeline can be extended using:

- Incremental data ingestion.
- Snowflake bulk loading with COPY INTO.
- Batch processing and parallel execution.
- Partitioning and clustering strategies where appropriate.
- MERGE-based incremental upserts.
- Automated data quality checks and pipeline monitoring.

## 10. Conclusion

The project demonstrates an end-to-end data engineering workflow covering multi-format data extraction, transformation, data quality validation, Snowflake integration, country-wise data organization, and semi-structured JSON processing.
