"""Charts of the TBEM results as SVG (pure Python).

The charts need no script: they show in the pyRevit output (whose chart library does not load in the CPython
engine) and in the HTML report saved next to the results (``report``).
"""
import math

FONT = "font-family='Segoe UI, Arial, sans-serif' font-size='12'"
GRID = "#dddddd"
TEXT = "#333333"


def _escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _rgb(rgb):
    return "rgb(%d,%d,%d)" % tuple(rgb)


def nice_ticks(high, count=5):
    """Round tick values from 0 to at least ``high``."""
    if high <= 0:
        return [0, 1]
    raw = high / float(count)
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    return [round(i * step, 10) for i in range(int(math.ceil(high / step - 1e-9)) + 1)]


def _number(value):
    return ("%.0f" if abs(value) >= 100 or value == int(value) else "%.1f") % value


def bar_chart(labels, series, unit="", stacked=False, width=900, height=340):
    """SVG bar chart of ``series`` [(name, values, rgb)] over ``labels``, grouped or ``stacked``.
    Series that are zero everywhere are left out and named under the chart."""
    shown = [s for s in series if any(v for v in s[1])]
    omitted = [s[0] for s in series if s not in shown]
    left, right, top = 64, 16, 40
    plot_w = width - left - right
    # labels rotated when they do not fit their slot (about 7 px per character at 12 px)
    rotate = max([len(str(x)) for x in labels] or [0]) * 7 > plot_w / float(max(len(labels), 1)) * 0.9
    bottom = 96 if rotate else 40
    plot_h = height - top - bottom
    totals = [sum(s[1][i] for s in shown) for i in range(len(labels))] if stacked else \
        [max([s[1][i] for s in shown] or [0]) for i in range(len(labels))]
    ticks = nice_ticks(max(totals or [0]))
    top_value = float(ticks[-1])

    def y(value):
        return top + plot_h - plot_h * value / top_value

    out = ["<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %d %d' style='width:100%%;max-width:%dpx' %s>"
           % (width, height, width, FONT)]
    for tick in ticks:
        out.append("<line x1='%d' x2='%d' y1='%.1f' y2='%.1f' stroke='%s'/>" % (left, left + plot_w, y(tick), y(tick),
                                                                              GRID))
        out.append("<text x='%d' y='%.1f' text-anchor='end' fill='%s'>%s</text>" % (left - 6, y(tick) + 4, TEXT,
                                                                                   _number(tick)))
    if unit:
        out.append("<text x='12' y='%d' fill='%s' transform='rotate(-90 12 %d)' text-anchor='middle'>%s</text>"
                   % (top + plot_h // 2, TEXT, top + plot_h // 2, _escape(unit)))
    group = plot_w / float(max(len(labels), 1))
    for i, label in enumerate(labels):
        x0 = left + i * group
        if stacked:
            base = 0.0
            for name, values, rgb in shown:
                out.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' fill='%s'><title>%s %s: %s</title>"
                           "</rect>" % (x0 + group * 0.2, y(base + values[i]), group * 0.6,
                                        y(base) - y(base + values[i]), _rgb(rgb), _escape(label), _escape(name),
                                        _number(values[i])))
                base += values[i]
        else:
            bar = group * 0.8 / max(len(shown), 1)
            for j, (name, values, rgb) in enumerate(shown):
                out.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' fill='%s'><title>%s %s: %s</title>"
                           "</rect>" % (x0 + group * 0.1 + j * bar, y(values[i]), bar * 0.92,
                                        y(0) - y(values[i]), _rgb(rgb), _escape(label), _escape(name),
                                        _number(values[i])))
        cx, cy = x0 + group / 2, top + plot_h + 16
        if rotate:
            out.append("<text x='%.1f' y='%d' fill='%s' text-anchor='end' transform='rotate(-40 %.1f %d)'>%s</text>"
                       % (cx, cy, TEXT, cx, cy, _escape(label)))
        else:
            out.append("<text x='%.1f' y='%d' fill='%s' text-anchor='middle'>%s</text>" % (cx, cy, TEXT,
                                                                                         _escape(label)))
    out.append("<line x1='%d' x2='%d' y1='%.1f' y2='%.1f' stroke='%s'/>" % (left, left + plot_w, y(0), y(0), TEXT))
    x = left
    for name, _, rgb in shown:
        out.append("<rect x='%d' y='12' width='12' height='12' fill='%s'/>" % (x, _rgb(rgb)))
        out.append("<text x='%d' y='22' fill='%s'>%s</text>" % (x + 17, TEXT, _escape(name)))
        x += 30 + 7 * len(str(name))
    if omitted:
        out.append("<text x='%d' y='22' fill='#888888'>(zero all year: %s)</text>" % (x, _escape(", ".join(omitted))))
    out.append("</svg>")
    return "".join(out)


def table(columns, rows):
    """HTML table."""
    head = "".join("<th>%s</th>" % _escape(c) for c in columns)
    body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % _escape(v) for v in row) for row in rows)
    return "<table><tr>%s</tr>%s</table>" % (head, body)


def report(title, sections):
    """Standalone HTML page with a heading and the (heading, html) ``sections``."""
    style = ("body{font-family:'Segoe UI',Arial,sans-serif;color:#333;margin:24px;max-width:960px}"
             "table{border-collapse:collapse;margin:8px 0}td,th{border:1px solid #ccc;padding:4px 10px;"
             "text-align:right}th{background:#f2f2f2}h2{margin-top:28px;font-size:16px}")
    parts = ["<!DOCTYPE html><html><head><meta charset='utf-8'><title>%s</title><style>%s</style></head><body>"
             % (_escape(title), style), "<h1>%s</h1>" % _escape(title)]
    parts += ["<h2>%s</h2>%s" % (_escape(heading), html) for heading, html in sections]
    return "".join(parts) + "</body></html>"
