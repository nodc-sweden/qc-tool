from bokeh.plotting import figure, show
from bokeh.layouts import layout
from bokeh.models import Div, RangeSlider, Spinner

x = list(range(11))
y = [i**2 for i in x]

p = figure(x_range=(1, 9), width=500, height=250)
points = p.circle(x=x, y=y, size=20, fill_color="red")

div = Div(
    text="""
    <p>Select the circle's size:</p>
    """,
    width=200,
    height=30,
)

spinner = Spinner(
    title="Circle Size",
    low=0,
    high=60,
    step=5,
    value=points.glyph.size,
    width=200,
)
spinner.js_link("value", points.glyph, "size")


range_slider = RangeSlider(
    title="Adjust X-axis range",
    start=0,
    end=10,
    step=1,
    value=(p.x_range.start, p.x_range.end),
)
range_slider.js_link("value", p.x_range, "start", attr_selector=0)
range_slider.js_link("value", p.x_range, "end", attr_selector=1)

my_layout = layout(
    [
        [div, spinner],
        [range_slider],
        [p],
    ]
)

show(my_layout)
