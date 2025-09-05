import os

import geopandas as gpd
import polars as pl
import pytest

from qc_tool.main import QcTool


def test_read_geopackage():
    if os.getenv("CI") == "true":
        pytest.skip("No test in CI environment")
    qc_tool = QcTool()
    qc_tool._read_geo_info_file()

    assert isinstance(qc_tool._geo_info, gpd.GeoDataFrame)


def test_match_seabasin_to_position_with_polarsdf():
    pass


# Fixture: provides the test dataframe
@pytest.fixture
def given_pl_data():
    latitudes = [5711.562, 5515.002, 5815.59]
    longitudes = [1139.446, 1559.044, 1126.141]
    depths = [10, 50, 100]  # example DEPH values

    # Expand to multiple rows per position
    rows = []
    for lat, lon in zip(latitudes, longitudes):
        for dep in depths:
            rows.append({"LATIT": lat, "LONGI": lon, "SDATE": "2025-08-18", "DEPH": dep})

    return pl.DataFrame(rows)


def test_match_sea_basin_to_position_with_polarsdf(given_pl_data):
    if os.getenv("CI") == "true":
        pytest.skip("No test in CI environment")
    qc_tool = QcTool()

    # Run the method
    enriched_data = qc_tool._match_sea_basins(given_pl_data)

    # Check that 'sea_basin' column exists
    assert "sea_basin" in enriched_data.columns

    # Check that the three unique positions have different sea_basin values
    unique_positions = (
        enriched_data.unique(subset=["LATIT", "LONGI"])
        .select(["sea_basin"])
        .to_series()
        .to_list()
    )
    assert len(set(unique_positions)) == 3, (
        "Expected different sea_basins for each position"
    )
