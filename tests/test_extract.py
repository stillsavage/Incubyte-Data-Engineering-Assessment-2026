
import pytest

from python.extract import extract_member_data, extract_redemption_data


def test_extract_member_data_returns_records():
    df = extract_member_data()

    assert df is not None
    assert len(df) == 5
    assert "Member_Id" in df.columns
    assert "Member_Name" in df.columns


def test_extract_redemption_data_returns_records():
    df = extract_redemption_data()

    assert df is not None
    assert len(df) == 2
    assert "txn_id" in df.columns
    assert "member_id" in df.columns
