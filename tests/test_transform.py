
import pandas as pd

from python.extract import extract_member_data, extract_redemption_data
from python.transform import transform_member_data, transform_redemption_data


def test_transform_member_data_returns_valid_records():
    raw_df = extract_member_data()
    valid_df = transform_member_data(raw_df)

    assert valid_df is not None
    assert len(valid_df) == 5
    assert "Age" in valid_df.columns
    assert "Stale_Member" in valid_df.columns


def test_transform_redemption_data_returns_valid_records():
    raw_df = extract_redemption_data()
    transformed_df = transform_redemption_data(raw_df)

    assert transformed_df is not None
    assert len(transformed_df) == 2
    assert "txn_id" in transformed_df.columns
