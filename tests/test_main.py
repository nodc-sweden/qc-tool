import os

import geopandas as gpd
import polars as pl
import pytest

from qc_tool.main import QcTool


@pytest.mark.skipif(os.getenv("CI") == "true", reason="Skipping test in CI environment")
def test_read_geopackage():
    qc_tool = QcTool()
    qc_tool._read_geo_info_file()

    assert isinstance(qc_tool._geo_info, gpd.GeoDataFrame)


def test_match_seabasin_to_position_with_polarsdf():
    pass


# Fixture: provides the test dataframe
@pytest.fixture
def given_pl_data():
    latitudes = [57.11562, 55.15002, 58.1559]
    longitudes = [11.39446, 15.59044, 11.26141]
    depths = [10, 50, 100]  # example DEPH values

    # Expand to multiple rows per position
    rows = []
    for lat, lon in zip(latitudes, longitudes):
        for dep in depths:
            rows.append(
                {
                    "sample_latitude_dd": lat,
                    "sample_longitude_dd": lon,
                    "SDATE": "2025-08-18",
                    "DEPH": dep,
                }
            )

    return pl.DataFrame(rows)


@pytest.mark.skipif(os.getenv("CI") == "true", reason="Skipping test in CI environment")
def test_match_sea_basin_to_position_with_polarsdf(given_pl_data):
    qc_tool = QcTool()

    # Run the method
    enriched_data = qc_tool._match_sea_basins(given_pl_data)

    # Check that 'sea_basin' column exists
    assert "sea_basin" in enriched_data.columns

    # Check that the three unique positions have different sea_basin values
    unique_positions = (
        enriched_data.unique(subset=["sample_latitude_dd", "sample_longitude_dd"])
        .select(["sea_basin"])
        .to_series()
        .to_list()
    )
    assert len(set(unique_positions)) == 3, (
        "Expected different sea_basins for each position"
    )
