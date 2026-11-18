# Data Dictionary

## 1. Member Data

| Column Name | Description | Data Type |
|---|---|---|
| Member_Id | Unique member identifier | STRING |
| Member_Name | Member full name | STRING |
| Enrollment_Date | Member enrollment date | DATE |
| Last_Flight_Date | Date of member's last flight | DATE |
| Tier_Code | Member loyalty tier | STRING |
| Agent_Name | Agent handling the member | STRING |
| State | Member's state | STRING |
| Country | Member's country | STRING |
| DOB | Member date of birth | DATE |
| Is_Active | Member active status | STRING |
| Age | Member age calculated from DOB | INTEGER |
| Stale_Member | Indicates no flight activity for more than 90 days | BOOLEAN |

## 2. Redemption Data

| Column Name | Description | Data Type |
|---|---|---|
| txn_id | Unique redemption transaction ID | STRING |
| txn_date | Redemption transaction date | DATE |
| partner | Redemption partner name | STRING |
| miles_redeemed | Number of miles redeemed | INTEGER |
| status | Redemption transaction status | STRING |
| member_id | Associated member identifier | STRING |
| feed_date | Date of source feed | DATE |

## 3. Data Quality Rules

- Member_Id must not be NULL.
- Member_Name must not be NULL.
- Enrollment_Date must be a valid date.
- Duplicate member records must be identified.
- Redemption transaction IDs must be unique.
- Miles_Redeemed must not be negative.
- Stale_Member is TRUE when days since Last_Flight_Date exceed 90.