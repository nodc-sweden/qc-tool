import polars as pl
import pytest

from qc_tool import data_transformation
from qc_tool.controllers.file_controller import FileController


@pytest.mark.parametrize(
    "given_serno, expected_serno",
    (
        (0, "0000"),
        (1, "0001"),
        (99, "0099"),
        (100, "0100"),
        (1001, "1001"),
    ),
)
def test_prepare_data_makes_series_number_zero_padded_string(given_serno, expected_serno):
    # Given data where data has a given serial number
    given_data = pl.DataFrame(
        (
            {"STATN": "Fladen", "SERNO": given_serno},
            {"STATN": "Fladen", "SERNO": given_serno},
            {"STATN": "Fladen", "SERNO": given_serno},
        )
    )

    # When preparing data
    transformed_data = data_transformation.prepare_data(given_data)

    # Then all sernos are changed
    all_serno = transformed_data["SERNO"].unique()
    assert len(all_serno) == 1

    # And serno is the expected string
    transformed_serno = all_serno[0]
    assert transformed_serno == expected_serno


@pytest.mark.parametrize(
    "given_quality_flag",
    (
        "0",
        "1",
        "2",
        "3",
        "4",
        "6",
        "7",
        "8",
        "9",
    ),
)
def test_prepare_data_adds_quality_flag_long_column_with_input_from_quality_flag(
    given_quality_flag,
):
    # Given data
    given_data = pl.DataFrame(
        (
            {"STATN": "FLADEN", "SERNO": 1, "quality_flag": given_quality_flag},
            {"STATN": "ANHOLT E", "SERNO": 2, "quality_flag": given_quality_flag},
            {"STATN": "BY31 LANDSORTSDJ", "SERNO": 3, "quality_flag": given_quality_flag},
        )
    )

    # Given there is a column named 'quality_flag'
    assert "quality_flag" in given_data.columns

    # Given there is no column named 'quality_flag_long'
    assert "quality_flag_long" not in given_data.columns

    # When preparing the data
    transformed_data = data_transformation.prepare_data(given_data)

    # Then the column 'quality_flag_long' is added
    assert "quality_flag_long" in transformed_data.columns

    # And all rows have the same value
    all_quality_flag_long = transformed_data["quality_flag_long"].unique()
    assert len(all_quality_flag_long) == 1

    # And the value starts with the value from 'quality_flag'
    quality_flag_long = all_quality_flag_long[0]
    assert quality_flag_long.startswith(f"{given_quality_flag}_")

    # And the value ends with the value from 'quality_flag'
    quality_flag_long = all_quality_flag_long[-1]
    assert quality_flag_long.endswith(f"_{given_quality_flag}")


def test_change_report_filters_rows_with_manual_qc():
    # Given a polars dataset which both include rows with and without manual qc flags.
    given_data = pl.DataFrame(
        {
            "quality_flag_long": [
                "1_000000000_Q_Q",  # Manual QC
                "1_000000000_0_1",
                "2_000000000_B_B",  # Manual QC
                "2_000000000_0_2",
                "3_000000000_A_A",  # Manual QC
                "3_000000000_0_3",
                "4_000000000_9_9",  # Manual QC
                "4_000000000_0_4",
                "5_000000000_8_8",  # Manual QC
                "5_000000000_0_5",
                "6_000000000_7_7",  # Manual QC
                "6_000000000_0_6",
                "7_000000000_6_6",  # Manual QC
                "7_000000000_0_7",
                "8_000000000_5_5",  # Manual QC
                "8_000000000_0_8",
                "9_000000000_4_4",  # Manual QC
                "9_000000000_0_9",
                "Q_000000000_3_3",  # Manual QC
                "Q_000000000_0_Q",
                "B_000000000_2_2",  # Manual QC
                "B_000000000_0_B",
                "A_000000000_1_1",  # Manual QC
                "A_000000000_0_A",
            ],
            "visit_key": [f"visit_{n}" for n in range(24)],
            "reported_visit_date": ["2024-01-01"] * 24,
            "reported_sample_depth_m": [10.0] * 24,
            "reported_value": [1.0] * 24,
        }
    )
    given_data = FileController._expand_quality_flag_long(given_data)

    # When calling change_report
    report = data_transformation.changes_report(given_data)

    # Then only the rows with manual qc are returned
    assert len(report) < len(given_data)
    assert len(report) == 12
    assert all(value != "0" for value in report["MANUAL_QC"])
