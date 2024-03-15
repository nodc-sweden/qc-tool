import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from bokeh.layouts import gridplot
from bokeh.plotting import figure, show


def main():
    data_path = Path(
        "/home/k000840/code/oceanografi/qc-tool/test_data/2023-06-18_2011-2023-LANDSKOD_77-FARTYGSKOD_10_row_format.txt"
    )
    data = parse_data(data_path)
    column_data = row_to_column(data)
    selected_data = {
        key: value
        for key, value in column_data.items()
        if key.startswith("2023-11-BPNX37-")
    }
    plot(selected_data.values())


def row_to_column(row_data):
    column_data = {}
    for row in row_data:
        key = f"{row['MYEAR']}-{row['CRUISE_NO']}-{row['STNCODE']}-{row['DEPH']}"
        if key not in column_data:
            column_data[key] = {
                column: row[column]
                for column in ("MYEAR", "CRUISE_NO", "STNCODE", "DEPH")
            }
        column_data[key][row["parameter"]] = row["value"]
    return column_data


def parse_data(data_path: Path):
    with data_path.open("r") as file:
        reader = csv.DictReader(file, delimiter="\t")
        data = [row for row in reader]
    return data


def plot(data):
    parameters = set()
    for row in data:
        parameters.update(row.keys())
    parameter_1 = "SIO3-SI"
    parameter_2 = "PHOS"
    parameter_3 = "PH"
    y = [int(row["DEPH"]) for row in data]
    x0 = [float(row.get(parameter_1, np.nan)) for row in data if parameter_1]
    x1 = [float(row.get(parameter_2, np.nan)) for row in data]
    x2 = [float(row.get(parameter_3, np.nan)) for row in data]

    # create a new plot
    plot_height = 400
    plot_width = 400
    circle_size = 7
    s1 = figure(width=plot_width, height=plot_height, title=parameter_1)
    s1.y_range.flipped = True
    s1.circle(x0, y, size=circle_size, color="navy", alpha=0.5)

    # create a new plot and share both ranges
    s2 = figure(
        width=plot_width, height=plot_height, y_range=s1.y_range, title=parameter_2
    )
    s2.y_range.flipped = True
    s2.circle(x1, y, size=circle_size, color="firebrick", alpha=0.5)

    # create a new plot and share only one range
    s3 = figure(
        width=plot_width, height=plot_height, y_range=s1.y_range, title=parameter_3
    )
    s3.y_range.flipped = True
    s3.circle(x2, y, size=circle_size, color="olive", alpha=0.5)

    p = gridplot([[s1, s2, s3]], toolbar_location=None)

    show(p)


if __name__ == "__main__":
    main()
