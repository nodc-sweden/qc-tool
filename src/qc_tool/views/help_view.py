from bokeh.models import Column, Div, Row
from ocean_data_qc.fyskem.qc_flag import QC_FLAG_CSS_COLORS, QcFlag
from ocean_data_qc.fyskem.qc_flag_tuple import QcField

from qc_tool.views.base_view import BaseView


class HelpView(BaseView):
    def __init__(self):
        # -----------------------
        # Header
        # -----------------------
        header = Div(
            text="<b>INFORMATION</b>",
            width=800,
        )

        # -----------------------
        # Information text (left side)
        # -----------------------
        header_left_top = Div(
            text="<b>Statistics used in plots</b>",
            width=500,
        )
        info_text = Div(
            text="""
            Statistics is based on data from 1993-2023 and is calculated per basin, month and standard depth.<br><br>

            Basins outside 12 nm follow HELCOM and OSPAR definitions.<br>
            Coastal data is aggregated by typology (type areas).<br><br>

            Profile plots show median values (grey line) and 25th and 75th percentiles (grey area).<br>
            This means 50% of the data lies within the grey area.<br><br>

            Orange area marks data flagged as 3 (bad data correctable).<br>
            Min and max values are shown as thin red lines.<br><br>
            """,  # noqa: E501
            width=500,
        )
        left_column_top = Column(children=[header_left_top, info_text])
        # -----------------------
        # Image (right side)
        # -----------------------
        info_statistic_test_text = Div(
            text="""Auto QC flags data as bad when:<br>
            value > max + 3*(75th percentile - median)<br>
            or value < min - 3*(median - 25th percentile)<br><br>

            Data is flagged as bad correctable when:<br>
            value > max + 1.5*(75th percentile - median)<br>
            or value < min - 1.5*(median - 25th percentile)"""
        )
        image_statistic_test = Div(
            text="""
            <img src="/qc_tool/static/images/explanation_statistic_test.png"
                 style="max-width: 100%; height: auto;">
            """,
            width=600,
        )

        top_row = Row(
            children=[left_column_top, info_statistic_test_text, image_statistic_test],
            sizing_mode="stretch_width",
        )

        # -----------------------
        # Separator
        # -----------------------
        divider = Div(
            text='<hr style="border: 1px solid #ccc; margin: 10px 0;">',
            width=800,
        )

        # -----------------------
        # Flag list (left)
        # -----------------------
        flag_items = ""
        for flag_number, flag_name, color in [
            (flag.value, str(flag), QC_FLAG_CSS_COLORS[flag]) for flag in QcFlag
        ]:
            if color != "gray":
                flag_items += f"""
                <li>
                    <span style="color:{color}; font-size:18px;">●</span>
                    {flag_number} - {flag_name}
                </li>
                """

        flag_list = Div(
            text=f"""
            <p><b>Flag descriptions:</b></p>
            <ol>
                {flag_items}
            </ol>
            <p>
                <span style="font-size:18px;">○</span>
                Flag changed by automatic or manual QC
            </p>
            """,
            width=400,
        )

        # -----------------------
        # QC steps (right)
        # -----------------------
        qc_steps = Div(
            text=f"""
            <p><b>Order of tests performed in automatic QC:</b></p>
            <ol>
                {"".join(f"<li>{qc_field.name}</li>" for qc_field in QcField)}
            </ol>
            """,
            width=400,
        )

        bottom_row = Row(
            children=[flag_list, qc_steps],
            sizing_mode="stretch_width",
        )

        # -----------------------
        # Final layout
        # -----------------------
        self._layout = Column(
            children=[
                header,
                top_row,
                divider,
                bottom_row,
            ],
            sizing_mode="stretch_width",
        )

    @property
    def layout(self):
        return self._layout
