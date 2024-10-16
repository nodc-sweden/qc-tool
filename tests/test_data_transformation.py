import pandas as pd
import pytest

from qc_tool import data_transformation


@pytest.mark.parametrize(
    "given_serno, expected_serno",
    (
        (0, "000"),
        (1, "001"),
        (99, "099"),
        (100, "100"),
        (1001, "1001"),
    ),
)
def test_prepare_data_makes_series_number_zero_padded_string(given_serno, expected_serno):
    # Given data where data has a given serial number
    given_data = pd.DataFrame(
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
    given_data = pd.DataFrame(
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
    assert "quality_flag_long" in given_data.columns

    # And all rows have the same value
    all_quality_flag_long = transformed_data["quality_flag_long"].unique()
    assert len(all_quality_flag_long) == 1

    # And the value ends with the value from 'quality_flag'
    quality_flag_long = all_quality_flag_long[0]
    assert quality_flag_long.startswith(f"{given_quality_flag}_")
