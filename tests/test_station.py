import pandas as pd
import numpy as np
import pytest

from qc_tool.station import Station

def test_index_returns_match_to_originaldata():
    data = {
    'SERNO_STN': ['A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A', 'A',  # SERNO_STN A
                  'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B', 'B',  # SERNO_STN B
                  'C', 'C', 'C', 'C', 'C', 'C', 'C', 'C', 'C', 'C'],  # SERNO_STN C
    'parameter': ['param1', 'param1', 'param1', 'param2', 'param2', 'param2', 'param1', 'param1', 'param2', 'param2',
                  'param1', 'param1', 'param1', 'param2', 'param2', 'param2', 'param1', 'param1', 'param2', 'param2',
                  'param1', 'param1', 'param1', 'param2', 'param2', 'param2', 'param1', 'param1', 'param2', 'param2'],
    'depth': [0, 10, 20, 0, 10, 20, 5, 15, 5, 15,
              0, 10, 20, 0, 10, 20, 5, 15, 5, 15,
              0, 10, 20, 0, 10, 20, 5, 15, 5, 15],
    'value': np.random.rand(30) * 100
    }
    given_data = pd.DataFrame(data)
    station_series = sorted(given_data["SERNO_STN"].unique())
    stations = {
            series: Station(series, given_data[given_data["SERNO_STN"] == series])
            for series in station_series
        }
    
    assert stations['A'].indices.tolist() == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert stations['B'].indices.tolist() == [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    assert stations['C'].indices.tolist() == [20, 21, 22, 23, 24, 25, 26, 27, 28, 29]