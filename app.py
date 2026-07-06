
"""Project X LunaLink TT&C live dashboard GUI."""
from __future__ import annotations

import ctypes
import math
import tkinter as tk
from tkinter import font as tkfont

from link_budget import LinkConfig
from orbit_model import EARTH_RADIUS_KM, GroundStation, OrbitConfig, ground_station_ecef, spacecraft_eci
from ttc_model import TTCInputs, simulate_ttc

COLORS = {
    "bg": "#eadcc7",
    "panel": "#f4eadb",
    "panel2": "#ead7bf",
    "panel3": "#d5b999",
    "line": "#5d4632",
    "line_dim": "#b79b7d",
    "text": "#111111",
    "black": "#3a2416",
    "accent": "#146c78",
    "green": "#2f7d4b",
    "red": "#b3262e",
    "yellow": "#b88718",
    "purple": "#6f4a8e",
    "gray": "#6e6257",
}
FONT = "Segoe UI"
PANEL_RADIUS = 26


def enable_high_dpi() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def choose_font(root: tk.Tk) -> str:
    available = set(tkfont.families(root))
    for family in ("Segoe UI Semibold", "Segoe UI", "Arial", "Calibri", "Tahoma"):
        if family in available:
            return family
    return "Arial"


def rounded_rect(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float, radius: float, **kwargs: object) -> int:
    points = [x1+radius,y1,x2-radius,y1,x2,y1,x2,y1+radius,x2,y2-radius,x2,y2,x2-radius,y2,x1+radius,y2,x1,y2,x1,y2-radius,x1,y1+radius,x1,y1]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class Panel(tk.Frame):
    def __init__(self, master: tk.Misc, fill: str = COLORS["panel"], radius: int = PANEL_RADIUS) -> None:
        super().__init__(master, bg=COLORS["bg"], bd=0, highlightthickness=0)
        self.fill = fill
        self.radius = radius
        self.bg = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0, bd=0)
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)
        self.bind("<Configure>", self.draw)

    def draw(self, _event: tk.Event | None = None) -> None:
        try:
            self.bg.delete("all")
            w, h = max(self.winfo_width(), 2), max(self.winfo_height(), 2)
            rounded_rect(self.bg, 1, 1, w - 2, h - 2, self.radius, fill=self.fill, outline=COLORS["line"], width=1)
        except tk.TclError:
            pass


class RoundButton(tk.Canvas):
    def __init__(self, master: tk.Misc, text: str, command: object, width: int = 150, height: int = 46, icon: str | None = None) -> None:
        super().__init__(master, width=width, height=height, bg=COLORS["bg"], highlightthickness=0, cursor="hand2")
        self.text = text
        self.command = command
        self.icon = icon
        self.bind("<Button-1>", lambda _event: self.command())
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        w, h = int(float(self.cget("width"))), int(float(self.cget("height")))
        rounded_rect(self, 1, 1, w - 2, h - 2, 22, fill=COLORS["panel3"], outline=COLORS["line"], width=1)
        if self.icon == "play":
            cx, cy = w / 2 + 2, h / 2
            self.create_polygon(cx - 8, cy - 11, cx - 8, cy + 11, cx + 12, cy, fill=COLORS["text"], outline="")
        else:
            self.create_text(w / 2, h / 2, text=self.text, fill=COLORS["text"], font=(FONT, 14, "bold"))

class NavButton(tk.Frame):
    def __init__(self, master: tk.Misc, label: str, command: object, active: bool = False) -> None:
        super().__init__(master, bg=COLORS["bg"])
        fill = COLORS["panel3"] if active else COLORS["panel"]
        self.canvas = tk.Canvas(self, height=52, bg=COLORS["bg"], highlightthickness=0, cursor="hand2")
        self.canvas.pack(fill="x")
        self.canvas.bind("<Button-1>", lambda _event: command())
        self.canvas.bind("<Configure>", lambda event: self.draw(event.width, label, fill))

    def draw(self, width: int, label: str, fill: str) -> None:
        self.canvas.delete("all")
        rounded_rect(self.canvas, 1, 1, width - 2, 50, 18, fill=fill, outline=COLORS["line"], width=1)
        self.canvas.create_text(18, 26, text=label, anchor="w", fill=COLORS["text"], font=(FONT, 17, "bold"))

class ToggleSwitch(tk.Canvas):
    def __init__(self, master: tk.Misc, variable: tk.BooleanVar, text: str, command: object) -> None:
        super().__init__(master, width=330, height=50, bg=COLORS["panel"], highlightthickness=0, cursor="hand2")
        self.variable = variable
        self.text = text
        self.command = command
        self.variable.trace_add("write", lambda *_: self.draw())
        self.bind("<Button-1>", self.toggle)
        self.draw()

    def toggle(self, _event: tk.Event) -> None:
        self.variable.set(not self.variable.get())
        self.command()

    def draw(self) -> None:
        self.delete("all")
        active = self.variable.get()
        rounded_rect(self, 14, 10, 82, 42, 18, fill=COLORS["accent"] if active else COLORS["panel3"], outline=COLORS["line"])
        x = 66 if active else 30
        self.create_oval(x - 13, 13, x + 13, 39, fill=COLORS["text"], outline="")
        self.create_text(100, 26, text=self.text, anchor="w", fill=COLORS["text"], font=(FONT, 14, "bold"))


class Knob(tk.Canvas):
    def __init__(self, master: tk.Misc, label: str, variable: tk.DoubleVar, low: float, high: float, unit: str, command: object) -> None:
        super().__init__(master, width=178, height=218, bg=COLORS["panel"], highlightthickness=0, cursor="hand2")
        self.label = label
        self.variable = variable
        self.low = low
        self.high = high
        self.unit = unit
        self.command = command
        self.resolution = 0.1 if unit in {"dB", "dBi"} else 1.0
        self.start_deg = 225.0
        self.sweep_deg = 270.0
        self.cx = 89.0
        self.cy = 99.0
        self.radius = 43.0
        self.bind("<Button-1>", self.set_from_event)
        self.bind("<B1-Motion>", self.set_from_event)
        self.variable.trace_add("write", lambda *_: self.draw())
        self.draw()

    def value_decimals(self) -> int:
        if self.unit in {"dB", "dBi"}:
            return 1
        if self.high <= 50:
            return 1
        return 0

    def format_number(self, value: float) -> str:
        decimals = self.value_decimals()
        return f"{value:.{decimals}f}"

    def format_value(self) -> str:
        return self.format_number(self.variable.get())

    def display_unit(self) -> str:
        return f"[{self.unit}]"

    def set_from_event(self, event: tk.Event) -> None:
        cx, cy = self.cx, self.cy
        angle = math.degrees(math.atan2(cy - event.y, event.x - cx)) % 360.0
        if angle >= self.start_deg:
            pos = (angle - self.start_deg) / self.sweep_deg
        elif angle <= 135.0:
            pos = (angle + 360.0 - self.start_deg) / self.sweep_deg
        else:
            pos = 0.0 if angle < 180.0 else 1.0
        value = self.low + max(0.0, min(1.0, pos)) * (self.high - self.low)
        value = round(value / self.resolution) * self.resolution
        self.variable.set(max(self.low, min(self.high, value)))
        self.command()

    def draw_tick_label(self, cx: float, cy: float, r: float, frac: float, major: bool) -> None:
        deg = self.start_deg + self.sweep_deg * frac
        rad = math.radians(deg)
        value = self.low + frac * (self.high - self.low)
        label_r = r + (34 if major else 28)
        self.create_text(
            cx + math.cos(rad) * label_r,
            cy - math.sin(rad) * label_r,
            text=self.format_number(value),
            fill=COLORS["text"],
            font=(FONT, 11 if major else 10, "bold" if major else "normal"),
        )

    def draw(self) -> None:
        self.delete("all")
        cx, cy, r = self.cx, self.cy, self.radius
        raw_pos = (self.variable.get() - self.low) / max(0.001, self.high - self.low)
        pos = max(0.0, min(1.0, raw_pos))
        active = self.sweep_deg * pos
        self.create_text(cx, 16, text=self.label, fill=COLORS["text"], font=(FONT, 12, "bold"), width=160)
        self.create_text(cx, 36, text=self.display_unit(), fill=COLORS["text"], font=(FONT, 12))
        for i in range(5):
            frac = i / 4
            deg = self.start_deg + self.sweep_deg * frac
            rad = math.radians(deg)
            r1, r2 = r + 10, r + 21
            self.create_line(
                cx + math.cos(rad) * r1,
                cy - math.sin(rad) * r1,
                cx + math.cos(rad) * r2,
                cy - math.sin(rad) * r2,
                fill=COLORS["line"],
                width=2,
            )
        for frac in (0.0, 0.5, 1.0):
            self.draw_tick_label(cx, cy, r, frac, True)
        self.create_arc(cx-r, cy-r, cx+r, cy+r, start=self.start_deg, extent=self.sweep_deg, style="arc", outline=COLORS["line_dim"], width=8)
        self.create_arc(cx-r, cy-r, cx+r, cy+r, start=self.start_deg, extent=active, style="arc", outline="#5170ff", width=8)
        self.create_oval(cx-36, cy-36, cx+36, cy+36, fill="#4a2f1f", outline=COLORS["line"], width=1)
        self.create_oval(cx-29, cy-29, cx+29, cy+29, fill="#6f5038", outline="#5d4632")
        rad = math.radians(self.start_deg + active)
        self.create_line(cx, cy, cx + math.cos(rad) * 29, cy - math.sin(rad) * 29, fill=COLORS["text"], width=3)
        rounded_rect(self, cx - 32, 164, cx + 32, 188, 5, fill=COLORS["panel2"], outline=COLORS["line_dim"], width=1)
        value_color = COLORS["red"] if self.variable.get() >= self.high or self.variable.get() <= self.low else COLORS["text"]
        self.create_text(cx, 176, text=self.format_value(), fill=value_color, font=(FONT, 12, "bold"))
class LinePlot(tk.Canvas):
    def __init__(self, master: tk.Misc, title: str, y_label: str, height: int = 230) -> None:
        super().__init__(master, height=height, bg=COLORS["panel"], highlightthickness=0)
        self.title = title
        self.y_label = y_label
        self.series: list[tuple[list[float], list[float | None], str, str]] = []
        self.bind("<Configure>", lambda _event: self.draw())

    def set_series(self, series: list[tuple[list[float], list[float | None], str, str]]) -> None:
        self.series = series
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        w, h = max(self.winfo_width(), 340), max(self.winfo_height(), 190)
        rounded_rect(self, 1, 1, w - 2, h - 2, PANEL_RADIUS, fill=COLORS["panel"], outline=COLORS["line"], width=1)
        left, right, top, bottom = 66, 28, 42, 58
        if self.title == "Link Margin":
            top = 64
        pw, ph = w - left - right, h - top - bottom
        self.create_text(left, 18, text=self.title, anchor="w", fill=COLORS["text"], font=(FONT, 17, "bold"))
        self.create_line(left, top, left, top + ph, fill=COLORS["line"])
        self.create_line(left, top + ph, left + pw, top + ph, fill=COLORS["line"])
        if not self.series:
            return
        xs = [x for xv, _yv, _c, _l in self.series for x in xv]
        ys = [y for _xv, yv, _c, _l in self.series for y in yv if y is not None]
        if not xs or not ys:
            return
        xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
        if math.isclose(ymin, ymax):
            ymin -= 1.0
            ymax += 1.0
        pad = 0.08 * (ymax - ymin)
        ymin, ymax = ymin - pad, ymax + pad
        for i in range(5):
            frac = i / 4
            y = top + ph - frac * ph
            value = ymin + frac * (ymax - ymin)
            self.create_line(left, y, left + pw, y, fill=COLORS["line_dim"])
            self.create_text(left - 8, y, text=f"{value:.0f}", anchor="e", fill=COLORS["text"], font=(FONT, 12))
        for i in range(6):
            frac = i / 5
            x = left + frac * pw
            value = xmin + frac * (xmax - xmin)
            label = f"{value:.0f}" if (xmax - xmin) >= 5 else f"{value:.1f}"
            self.create_line(x, top, x, top + ph, fill=COLORS["line_dim"])
            self.create_line(x, top + ph, x, top + ph + 5, fill=COLORS["line"])
            self.create_text(x, top + ph + 18, text=label, fill=COLORS["text"], font=(FONT, 12, "bold"))
        for xv, yv, color, label in self.series:
            segment: list[float] = []
            line_width = 5 if self.title == "Link Margin" else 4
            dash = (8, 5) if self.title == "Link Margin" and label == "Required margin" else None
            for xval, yval in zip(xv, yv):
                if yval is None:
                    if len(segment) >= 4:
                        self.create_line(*segment, fill=color, width=line_width, dash=dash)
                    segment = []
                    continue
                x = left + (xval - xmin) / max(0.001, xmax - xmin) * pw
                y = top + ph - (yval - ymin) / max(0.001, ymax - ymin) * ph
                segment.extend([x, y])
            if len(segment) >= 4:
                self.create_line(*segment, fill=color, width=line_width, dash=dash)
        if self.title == "Onboard Data":
            lx = left + 116
            ly = 20
            for _x, _y, color, label in self.series:
                self.create_line(lx, ly, lx + 18, ly, fill=color, width=4)
                self.create_text(lx + 23, ly, text=label, anchor="w", fill=COLORS["text"], font=(FONT, 11, "bold"))
                lx += 96
        elif self.title == "Link Margin":
            legend_x = left + pw - 238
            legend_y = 18
            for i, (_x, _y, color, label) in enumerate(self.series):
                ly = legend_y + i * 16
                dash = (8, 5) if label == "Required margin" else None
                self.create_line(legend_x, ly, legend_x + 22, ly, fill=color, width=5, dash=dash)
                self.create_text(legend_x + 28, ly, text=label, anchor="w", fill=COLORS["text"], font=(FONT, 10, "bold"))
        else:
            lx = left + pw - 168
            for i, (_x, _y, color, label) in enumerate(self.series):
                y = 20 + i * 17
                self.create_line(lx, y, lx + 18, y, fill=color, width=4)
                self.create_text(lx + 24, y, text=label, anchor="w", fill=COLORS["text"], font=(FONT, 11, "bold"))
        self.create_text(left + pw / 2, h - 14, text="Time [h]", fill=COLORS["text"], font=(FONT, 13))
        self.create_text(16, top + ph / 2, text=self.y_label, angle=90, fill=COLORS["text"], font=(FONT, 13))


class GroundTrack(tk.Canvas):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, height=340, bg=COLORS["panel"], highlightthickness=0)
        self.lats: list[float] = []
        self.lons: list[float] = []
        self.contact: list[bool] = []
        self.gs = GroundStation()
        self.bind("<Configure>", lambda _event: self.draw())

    def set_data(self, lats: list[float], lons: list[float], contact: list[bool], gs: GroundStation) -> None:
        self.lats, self.lons, self.contact, self.gs = lats, lons, contact, gs
        self.draw()

    def xy(self, lat: float, lon: float, left: int, top: int, pw: int, ph: int) -> tuple[float, float]:
        return left + (lon + 180.0) / 360.0 * pw, top + (90.0 - lat) / 180.0 * ph

    def ground_track_segments(self) -> list[list[int]]:
        segments: list[list[int]] = []
        current: list[int] = []
        for i, lon in enumerate(self.lons):
            if i > 0 and abs(lon - self.lons[i - 1]) > 180.0:
                if len(current) >= 2:
                    segments.append(current)
                current = []
            current.append(i)
        if len(current) >= 2:
            segments.append(current)
        return segments

    def draw_polyline(self, indices: list[int], left: int, top: int, pw: int, ph: int, color: str, width: int) -> None:
        points: list[float] = []
        for i in indices:
            points.extend(self.xy(self.lats[i], self.lons[i], left, top, pw, ph))
        if len(points) >= 4:
            self.create_line(*points, fill=color, width=width, smooth=True)

    def draw_contact_overlay(self, segments: list[list[int]], left: int, top: int, pw: int, ph: int) -> None:
        for segment in segments:
            active: list[int] = []
            for i in segment:
                if self.contact[i]:
                    active.append(i)
                else:
                    if len(active) >= 2:
                        self.draw_polyline(active, left, top, pw, ph, COLORS["accent"], 4)
                    elif len(active) == 1:
                        x, y = self.xy(self.lats[active[0]], self.lons[active[0]], left, top, pw, ph)
                        self.create_oval(x - 2, y - 2, x + 2, y + 2, fill=COLORS["accent"], outline="")
                    active = []
            if len(active) >= 2:
                self.draw_polyline(active, left, top, pw, ph, COLORS["accent"], 4)
            elif len(active) == 1:
                x, y = self.xy(self.lats[active[0]], self.lons[active[0]], left, top, pw, ph)
                self.create_oval(x - 2, y - 2, x + 2, y + 2, fill=COLORS["accent"], outline="")

    def draw(self) -> None:
        self.delete("all")
        w, h = max(self.winfo_width(), 420), max(self.winfo_height(), 240)
        rounded_rect(self, 1, 1, w - 2, h - 2, PANEL_RADIUS, fill=COLORS["panel"], outline=COLORS["line"], width=1)
        left, top, right, bottom = 70, 44, 24, 52
        pw, ph = w - left - right, h - top - bottom
        self.create_text(left, 18, text="Ground Track", anchor="w", fill=COLORS["text"], font=(FONT, 17, "bold"))
        for lon in range(-180, 181, 60):
            x, _ = self.xy(0, lon, left, top, pw, ph)
            self.create_line(x, top, x, top + ph, fill=COLORS["line_dim"])
            self.create_text(x, top + ph + 18, text=str(lon), fill=COLORS["text"], font=(FONT, 12))
        for lat in range(-90, 91, 30):
            _, y = self.xy(lat, 0, left, top, pw, ph)
            self.create_line(left, y, left + pw, y, fill=COLORS["line_dim"])
            self.create_text(left - 10, y, text=str(lat), anchor="e", fill=COLORS["text"], font=(FONT, 12))
        segments = self.ground_track_segments()
        for segment in segments:
            self.draw_polyline(segment, left, top, pw, ph, COLORS["gray"], 2)
        self.draw_contact_overlay(segments, left, top, pw, ph)
        gx, gy = self.xy(self.gs.lat_deg, self.gs.lon_deg, left, top, pw, ph)
        self.create_oval(gx - 7, gy - 7, gx + 7, gy + 7, fill=COLORS["accent"], outline=COLORS["line"], width=2)
        rounded_rect(self, gx + 10, gy - 13, gx + 120, gy + 13, 7, fill=COLORS["panel2"], outline=COLORS["line_dim"])
        self.create_text(gx + 18, gy, text="Ottobrunn GS", anchor="w", fill=COLORS["text"], font=(FONT, 12, "bold"))
        self.create_text(left + pw / 2, h - 14, text="Longitude [deg]", fill=COLORS["text"], font=(FONT, 13))
        self.create_text(18, top + ph / 2, text="Latitude [deg]", angle=90, fill=COLORS["text"], font=(FONT, 13))
class Orbit3DView(tk.Canvas):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, height=300, bg=COLORS["panel"], highlightthickness=0)
        self.orbit = OrbitConfig()
        self.gs = GroundStation()
        self.view_elev = math.radians(25.0)
        self.view_az = math.radians(45.0)
        self.bind("<Configure>", lambda _event: self.draw())

    def set_data(self, orbit: OrbitConfig, gs: GroundStation) -> None:
        self.orbit = orbit
        self.gs = gs
        self.draw()

    def project(self, vec: tuple[float, float, float], cx: float, cy: float, scale: float) -> tuple[float, float]:
        x, y, z = vec
        ca, sa = math.cos(self.view_az), math.sin(self.view_az)
        ce, se = math.cos(self.view_elev), math.sin(self.view_elev)
        xr = ca * x - sa * y
        yr = sa * x + ca * y
        xp = xr
        yp = se * yr - ce * z
        return cx + xp * scale, cy + yp * scale

    def draw_axis(self, cx: float, cy: float, scale: float, label: str, vec: tuple[float, float, float]) -> None:
        x, y = self.project(vec, cx, cy, scale)
        self.create_line(cx, cy, x, y, fill=COLORS["line"], width=2)
        self.create_text(x + 4, y, text=label, fill=COLORS["text"], font=(FONT, 12, "bold"), anchor="w")

    def draw_polyline_3d(self, vectors: list[tuple[float, float, float]], cx: float, cy: float, scale: float, color: str, width: int = 1) -> None:
        points: list[float] = []
        for vec in vectors:
            points.extend(self.project(vec, cx, cy, scale))
        if len(points) >= 4:
            self.create_line(*points, fill=color, width=width, smooth=True)

    def draw_earth_grid(self, cx: float, cy: float, scale: float) -> None:
        r = EARTH_RADIUS_KM
        self.create_oval(cx - r * scale, cy - r * scale, cx + r * scale, cy + r * scale, fill="#9ed0e6", outline=COLORS["line"], width=2)
        for lat_deg in (-60, -30, 0, 30, 60):
            lat = math.radians(lat_deg)
            vectors = []
            for lon_deg in range(0, 361, 8):
                lon = math.radians(lon_deg)
                vectors.append((r * math.cos(lat) * math.cos(lon), r * math.cos(lat) * math.sin(lon), r * math.sin(lat)))
            self.draw_polyline_3d(vectors, cx, cy, scale, "#5b9fba", 1)
        for lon_deg in range(0, 180, 30):
            lon = math.radians(lon_deg)
            vectors = []
            for lat_deg in range(-90, 91, 5):
                lat = math.radians(lat_deg)
                vectors.append((r * math.cos(lat) * math.cos(lon), r * math.cos(lat) * math.sin(lon), r * math.sin(lat)))
            self.draw_polyline_3d(vectors, cx, cy, scale, "#5b9fba", 1)

    def draw_marker(self, vec: tuple[float, float, float], cx: float, cy: float, scale: float, color: str, label: str, r: int = 5) -> None:
        x, y = self.project(vec, cx, cy, scale)
        self.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=COLORS["line"], width=1)
        self.create_text(x + r + 5, y, text=label, anchor="w", fill=COLORS["text"], font=(FONT, 11, "bold"))

    def draw_legend(self, w: int) -> None:
        items = [(COLORS["accent"], "Orbit"), ("#9ed0e6", "Earth"), (COLORS["red"], "Spacecraft"), (COLORS["green"], "Perigee"), (COLORS["purple"], "Apogee"), (COLORS["accent"], "Ottobrunn")]
        start_x = max(22, w - 390)
        start_y = 22
        col_w = 122
        for i, (color, label) in enumerate(items):
            x = start_x + (i % 3) * col_w
            y = start_y + (i // 3) * 18
            self.create_line(x, y, x + 18, y, fill=color, width=4)
            self.create_text(x + 24, y, text=label, anchor="w", fill=COLORS["text"], font=(FONT, 10, "bold"))

    def draw(self) -> None:
        self.delete("all")
        w, h = max(self.winfo_width(), 440), max(self.winfo_height(), 280)
        rounded_rect(self, 1, 1, w - 2, h - 2, PANEL_RADIUS, fill=COLORS["panel"], outline=COLORS["line"], width=1)
        self.create_text(22, 22, text="3D Orbit View", anchor="w", fill=COLORS["text"], font=(FONT, 17, "bold"))
        self.draw_legend(w)
        cx, cy = w * 0.50, h * 0.55
        ra = EARTH_RADIUS_KM + self.orbit.apogee_alt_km
        scale = min((w - 78) / (2.0 * ra), (h - 88) / (1.34 * ra))

        self.draw_axis(cx, cy, scale, "X [km]", (ra * 0.48, 0.0, 0.0))
        self.draw_axis(cx, cy, scale, "Y [km]", (0.0, ra * 0.48, 0.0))
        self.draw_axis(cx, cy, scale, "Z [km]", (0.0, 0.0, ra * 0.42))
        self.draw_earth_grid(cx, cy, scale)

        orbit_vectors = [spacecraft_eci(self.orbit.period_s * i / 320, self.orbit) for i in range(321)]
        self.draw_polyline_3d(orbit_vectors, cx, cy, scale, COLORS["accent"], 4)
        self.draw_marker(spacecraft_eci(0.18 * self.orbit.period_s, self.orbit), cx, cy, scale, COLORS["red"], "S/C position", 6)
        self.draw_marker(spacecraft_eci(0.0, self.orbit), cx, cy, scale, COLORS["green"], "Perigee", 5)
        self.draw_marker(spacecraft_eci(self.orbit.period_s / 2.0, self.orbit), cx, cy, scale, COLORS["purple"], "Apogee", 5)
        self.draw_marker(ground_station_ecef(self.gs), cx, cy, scale, COLORS["accent"], "Ottobrunn", 5)
        self.create_text(22, h - 18, text="Static 3D view of the propagated orbit; red marker indicates spacecraft sample position.", anchor="w", fill=COLORS["gray"], font=(FONT, 10, "bold"))

class Timeline(tk.Canvas):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, height=135, bg=COLORS["panel"], highlightthickness=0)
        self.time_h: list[float] = []
        self.earth: list[bool] = []
        self.moon: list[bool] = []
        self.bind("<Configure>", lambda _event: self.draw())

    def set_data(self, time_h: list[float], earth: list[bool], moon: list[bool]) -> None:
        self.time_h, self.earth, self.moon = time_h, earth, moon
        self.draw()

    def summary(self, active: list[bool]) -> tuple[int, float]:
        if len(self.time_h) < 2:
            return 0, 0.0
        windows = 0
        active_prev = False
        minutes = 0.0
        for i in range(1, len(self.time_h)):
            if active[i] and not active_prev:
                windows += 1
            if active[i]:
                minutes += (self.time_h[i] - self.time_h[i - 1]) * 60.0
            active_prev = active[i]
        return windows, minutes

    def draw_bar(self, y: int, active: list[bool], color: str, label: str, width: int) -> None:
        left = 22
        bar_x = 118
        span = max(40, width - bar_x - 24)
        windows, minutes = self.summary(active)
        self.create_text(left, y, text=label, anchor="w", fill=COLORS["text"], font=(FONT, 12, "bold"))
        self.create_text(width - 28, y, text=f"{minutes:.0f} min / {windows} passes", anchor="e", fill=color, font=(FONT, 12, "bold"))
        if not self.time_h:
            return
        tmax = max(self.time_h)
        rounded_rect(self, bar_x, y - 8, bar_x + span, y + 8, 8, fill=COLORS["panel3"], outline=COLORS["line_dim"])
        for i in range(1, len(self.time_h)):
            if active[i]:
                x1 = bar_x + self.time_h[i - 1] / tmax * span
                x2 = bar_x + self.time_h[i] / tmax * span
                rounded_rect(self, x1, y - 8, x2, y + 8, 7, fill=color, outline=color)
        self.create_text(bar_x + 9, y, text=label, anchor="w", fill=COLORS["text"], font=(FONT, 11, "bold"))

    def draw(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 420)
        h = max(self.winfo_height(), 128)
        rounded_rect(self, 1, 1, w - 2, h - 2, PANEL_RADIUS, fill=COLORS["panel"], outline=COLORS["line"], width=1)
        self.create_text(22, 21, text="Communication Windows", anchor="w", fill=COLORS["text"], font=(FONT, 14, "bold"))
        self.draw_bar(58, self.earth, COLORS["accent"], "Earth GS", w)
        self.draw_bar(88, self.moon, COLORS["green"], "Moon relay", w)
        if self.time_h:
            bar_x = 118
            span = max(40, w - bar_x - 24)
            tmax = max(self.time_h)
            for i in range(5):
                frac = i / 4
                x = bar_x + frac * span
                self.create_line(x, 108, x, 113, fill=COLORS["line"])
                self.create_text(x, 123, text=f"{tmax * frac:.0f} h", fill=COLORS["text"], font=(FONT, 12, "bold"))


class SatelliteHeader(tk.Canvas):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, height=118, bg=COLORS["panel"], highlightthickness=0)
        self.bind("<Configure>", lambda _event: self.draw())

    def draw(self) -> None:
        self.delete("all")
        w, h = max(self.winfo_width(), 240), 118
        rounded_rect(self, 1, 1, w - 2, h - 2, 18, fill="#eadcc7", outline=COLORS["line"], width=1)
        self.create_text(18, 28, text="Luna Link", anchor="w", fill=COLORS["text"], font=(FONT, 25, "bold"))
        self.create_text(19, 54, text="Spacecraft Systems Simulator", anchor="w", fill=COLORS["text"], font=(FONT, 12, "bold"))
        cx, cy = w - 66, 82
        self.create_arc(cx - 70, cy - 34, cx + 38, cy + 34, start=198, extent=128, style="arc", outline=COLORS["line"], width=2)
        self.create_line(cx - 42, cy, cx - 16, cy, fill=COLORS["line"], width=1)
        self.create_line(cx + 16, cy, cx + 42, cy, fill=COLORS["line"], width=1)
        self.create_rectangle(cx - 15, cy - 12, cx + 15, cy + 12, fill="#c9ad8c", outline=COLORS["line"], width=1)
        self.create_rectangle(cx - 44, cy - 10, cx - 18, cy + 10, fill="#b8926e", outline=COLORS["line"], width=1)
        self.create_rectangle(cx + 18, cy - 10, cx + 44, cy + 10, fill="#b8926e", outline=COLORS["line"], width=1)
        self.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, outline=COLORS["accent"], width=1)


class DashboardApp(tk.Frame):
    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root, bg=COLORS["bg"])
        self.root = root
        self.root.title("Project X LunaLink - TT&C Simulator")
        self.root.geometry("1280x820")
        self.root.minsize(1120, 720)
        self.pack(fill="both", expand=True)
        self.page = "intro"
        self.update_job: str | None = None

        self.tx_power = tk.DoubleVar(value=50.0)
        self.tx_gain = tk.DoubleVar(value=35.0)
        self.rx_gain = tk.DoubleVar(value=52.0)
        self.losses = tk.DoubleVar(value=2.5)
        self.data_rate = tk.DoubleVar(value=100000.0)
        self.required_ebn0 = tk.DoubleVar(value=9.6)
        self.min_elevation = tk.DoubleVar(value=5.0)
        self.min_margin = tk.DoubleVar(value=3.0)
        self.moon_enabled = tk.BooleanVar(value=True)
        self.moon_tx_power = tk.DoubleVar(value=50.0)
        self.moon_tx_gain = tk.DoubleVar(value=30.0)
        self.moon_rx_gain = tk.DoubleVar(value=20.0)
        self.moon_losses = tk.DoubleVar(value=2.5)
        self.moon_data_rate = tk.DoubleVar(value=64.0)
        self.data_generation = tk.DoubleVar(value=180.0)
        self.storage_capacity = tk.DoubleVar(value=8000.0)
        self.initial_storage = tk.DoubleVar(value=1200.0)

        self.sidebar = tk.Frame(self, bg=COLORS["bg"], width=205)
        self.sidebar.pack(side="left", fill="y", padx=(8, 0), pady=8)
        self.sidebar.pack_propagate(False)
        self.main_shell = tk.Frame(self, bg=COLORS["bg"])
        self.main_shell.pack(side="right", fill="both", expand=True, padx=8, pady=8)
        self.main_shell.columnconfigure(0, weight=1)
        self.main_shell.rowconfigure(0, weight=1)
        self.main_canvas = tk.Canvas(self.main_shell, bg=COLORS["bg"], highlightthickness=0)
        self.main_canvas.grid(row=0, column=0, sticky="nsew")
        self.main_scrollbar = tk.Scrollbar(self.main_shell, orient="vertical", command=self.main_canvas.yview, bg=COLORS["black"], troughcolor=COLORS["bg"], relief="flat")
        self.main_scrollbar.grid(row=0, column=1, sticky="ns")
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        self.main = tk.Frame(self.main_canvas, bg=COLORS["bg"])
        self.main_window = self.main_canvas.create_window((0, 0), window=self.main, anchor="nw")
        self.main.bind("<Configure>", self._on_main_configure)
        self.main_canvas.bind("<Configure>", self._on_canvas_configure)
        self.main_canvas.bind("<Enter>", lambda _event: self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.main_canvas.bind("<Leave>", lambda _event: self.main_canvas.unbind_all("<MouseWheel>"))
        self.draw_sidebar()
        self.show_intro()

    def _on_main_configure(self, _event: tk.Event) -> None:
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.main_canvas.itemconfigure(self.main_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        delta = int(-1 * (event.delta / 120))
        self.main_canvas.yview_scroll(delta, "units")

    def draw_sidebar(self) -> None:
        for child in self.sidebar.winfo_children():
            child.destroy()
        SatelliteHeader(self.sidebar).pack(fill="x", pady=(0, 10))
        NavButton(self.sidebar, "1. Introduction", self.show_intro, self.page == "intro").pack(fill="x", pady=4)
        NavButton(self.sidebar, "2. TT&C Simulator", self.show_dashboard, self.page == "dash").pack(fill="x", pady=4)

    def clear_main(self) -> None:
        for child in self.main.winfo_children():
            child.destroy()

    def show_intro(self) -> None:
        self.page = "intro"
        self.draw_sidebar()
        self.clear_main()
        intro = Panel(self.main)
        intro.pack(fill="both", expand=True)
        canvas = tk.Canvas(intro, bg=COLORS["panel"], highlightthickness=0)
        canvas.configure(height=650)
        canvas.pack(fill="both", expand=True, padx=2, pady=2)
        canvas.bind("<Configure>", self.draw_intro_canvas)

    def draw_intro_canvas(self, event: tk.Event) -> None:
        c = event.widget
        c.delete("all")
        w, h = max(c.winfo_width(), 760), max(c.winfo_height(), 650)
        rounded_rect(c, 1, 1, w - 2, h - 2, PANEL_RADIUS, fill=COLORS["panel"], outline=COLORS["line"])

        card_w = min(w - 70, 1080)
        card_h = min(h - 46, 660)
        card_h = max(card_h, 610)
        card_x = (w - card_w) / 2
        card_y = max(22, (h - card_h) / 2)
        rounded_rect(c, card_x, card_y, card_x + card_w, card_y + card_h, 28, fill=COLORS["panel2"], outline=COLORS["line"], width=1)

        center_x = w / 2
        title_y = card_y + 46
        c.create_text(center_x, title_y, text="Project X LunaLink", anchor="center", fill=COLORS["text"], font=(FONT, 38, "bold"))
        c.create_text(center_x, title_y + 38, text="TT&C Mission Simulation Dashboard", anchor="center", fill=COLORS["text"], font=(FONT, 18, "bold"))

        art_top = card_y + 112
        art_h = 230
        art_cx = center_x
        art_cy = art_top + art_h * 0.52

        # Minimal mission sketch: centered satellite with quiet orbit arcs.
        c.create_arc(art_cx - 270, art_cy - 108, art_cx + 270, art_cy + 108, start=202, extent=136, style="arc", outline=COLORS["line"], width=2)
        c.create_arc(art_cx - 214, art_cy - 84, art_cx + 236, art_cy + 90, start=18, extent=132, style="arc", outline=COLORS["line_dim"], width=2)
        c.create_arc(art_cx - 310, art_cy - 132, art_cx + 310, art_cy + 132, start=28, extent=72, style="arc", outline=COLORS["accent"], width=2)

        sat_x, sat_y = art_cx, art_cy - 2
        panel_fill = "#b8926e"
        bus_fill = "#c9ad8c"
        c.create_line(sat_x - 126, sat_y, sat_x - 48, sat_y, fill=COLORS["line"], width=2)
        c.create_line(sat_x + 48, sat_y, sat_x + 126, sat_y, fill=COLORS["line"], width=2)
        c.create_rectangle(sat_x - 128, sat_y - 30, sat_x - 50, sat_y + 30, fill=panel_fill, outline=COLORS["line"], width=2)
        c.create_rectangle(sat_x + 50, sat_y - 30, sat_x + 128, sat_y + 30, fill=panel_fill, outline=COLORS["line"], width=2)
        for offset in (-108, -88, -68, 70, 90, 110):
            c.create_line(sat_x + offset, sat_y - 26, sat_x + offset, sat_y + 26, fill=COLORS["line_dim"], width=1)
        c.create_rectangle(sat_x - 42, sat_y - 36, sat_x + 42, sat_y + 36, fill=bus_fill, outline=COLORS["line"], width=2)
        c.create_rectangle(sat_x - 24, sat_y - 18, sat_x + 24, sat_y + 18, fill=COLORS["panel3"], outline=COLORS["line_dim"], width=1)
        c.create_oval(sat_x - 9, sat_y - 9, sat_x + 9, sat_y + 9, outline=COLORS["accent"], width=2)
        c.create_line(sat_x + 42, sat_y - 16, sat_x + 82, sat_y - 42, fill=COLORS["line"], width=2)
        c.create_oval(sat_x + 77, sat_y - 47, sat_x + 91, sat_y - 33, fill=COLORS["accent"], outline=COLORS["line"], width=1)

        sections = [
            ("Mission", "Molniya-type HEO - 500 kg spacecraft - Ottobrunn GS"),
            ("Links", "X-band Earth downlink >=100 Mbps - UHF Moon relay"),
            ("Outputs", "Ground track - Contact windows - Link margins - Data storage"),
        ]
        box_gap = 18
        box_w = min(320, (card_w - 88 - 2 * box_gap) / 3)
        box_h = 86
        boxes_y = art_top + art_h + 26
        start_x = (w - (3 * box_w + 2 * box_gap)) / 2
        for i, (title, body) in enumerate(sections):
            x = start_x + i * (box_w + box_gap)
            rounded_rect(c, x, boxes_y, x + box_w, boxes_y + box_h, 16, fill=COLORS["panel"], outline=COLORS["line"], width=1)
            c.create_text(x + 18, boxes_y + 24, text=title, anchor="w", fill=COLORS["text"], font=(FONT, 15, "bold"))
            c.create_text(x + 18, boxes_y + 50, text=body, anchor="nw", fill=COLORS["text"], font=(FONT, 12), width=box_w - 36)

        run_x, run_y, run_r = center_x, boxes_y + box_h + 54, 44
        c.create_oval(run_x - run_r, run_y - run_r, run_x + run_r, run_y + run_r, fill="#b69a78", outline=COLORS["line"], width=2, tags=("intro_run",))
        c.create_oval(run_x - run_r + 8, run_y - run_r + 8, run_x + run_r - 8, run_y + run_r - 8, fill="#ead7bf", outline="#5d4632", width=1, tags=("intro_run",))
        c.create_polygon(run_x - 10, run_y - 20, run_x - 10, run_y + 20, run_x + 23, run_y, fill=COLORS["text"], outline="", tags=("intro_run",))
        c.tag_bind("intro_run", "<Button-1>", lambda _event: self.show_dashboard())
        c.tag_bind("intro_run", "<Enter>", lambda _event: c.configure(cursor="hand2"))
        c.tag_bind("intro_run", "<Leave>", lambda _event: c.configure(cursor=""))
    def show_dashboard(self) -> None:
        self.page = "dash"
        self.draw_sidebar()
        self.clear_main()
        self.main.columnconfigure(0, weight=1, uniform="dashboard")
        self.main.columnconfigure(1, weight=1, uniform="dashboard")
        self.main.rowconfigure(2, weight=1)
        self.build_dashboard()
        self.refresh_dashboard()

    def label(self, parent: tk.Misc, text: str, size: int = 14, bold: bool = False) -> tk.Label:
        return tk.Label(parent, text=text, bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, size, "bold" if bold else "normal"))

    def build_dashboard(self) -> None:
        top = Panel(self.main)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 8))
        tk.Label(top, text="2. TT&C - Live Simulator", bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 28, "bold")).pack(anchor="w", padx=22, pady=(16, 4))
        tk.Label(top, text="Change the knobs below. Contact windows, margins, data storage, and ground track update immediately.", bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 15)).pack(anchor="w", padx=22, pady=(0, 16))

        params = Panel(self.main)
        params.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        knob_columns = 5
        tk.Label(params, text="Parameters", bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 17, "bold")).grid(row=0, column=0, columnspan=knob_columns, sticky="w", padx=18, pady=(12, 0))
        specs = [
            ("TX power", self.tx_power, 5, 100, "W"),
            ("SC antenna", self.tx_gain, 20, 45, "dBi"),
            ("GS antenna", self.rx_gain, 35, 65, "dBi"),
            ("Data rate", self.data_rate, 10000, 150000, "kbps"),
            ("Losses", self.losses, 0, 8, "dB"),
            ("Min margin", self.min_margin, 0, 10, "dB"),
            ("Data gen", self.data_generation, 0, 800, "Mbit/h"),
            ("Storage", self.storage_capacity, 1000, 20000, "Mbit"),
            ("Min elev", self.min_elevation, 0, 20, "deg"),
            ("Moon TX", self.moon_tx_power, 5, 100, "W"),
            ("Lunar TX gain", self.moon_tx_gain, 10, 40, "dBi"),
            ("SC UHF RX", self.moon_rx_gain, 5, 20, "dBi"),
            ("Moon losses", self.moon_losses, 0, 8, "dB"),
            ("Moon rate", self.moon_data_rate, 8, 512, "kbps"),
        ]
        for i, spec in enumerate(specs):
            Knob(params, *spec, self.schedule_refresh).grid(row=1 + i // knob_columns, column=i % knob_columns, padx=5, pady=(12, 8))
        ToggleSwitch(params, self.moon_enabled, "Moon relay", self.schedule_refresh).grid(row=3, column=4, padx=8, pady=10)
        for col in range(knob_columns):
            params.columnconfigure(col, weight=1)

        left = tk.Frame(self.main, bg=COLORS["bg"])
        left.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(0, weight=4)
        left.rowconfigure(1, weight=1)
        left.rowconfigure(2, weight=3)
        left.columnconfigure(0, weight=1)
        self.ground = GroundTrack(left)
        self.ground.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.timeline = Timeline(left)
        self.timeline.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.orbit_view = Orbit3DView(left)
        self.orbit_view.grid(row=2, column=0, sticky="nsew")

        right = tk.Frame(self.main, bg=COLORS["bg"])
        right.grid(row=2, column=1, sticky="nsew")
        right.columnconfigure(0, weight=3)
        right.columnconfigure(1, weight=1, minsize=220)
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        self.margin_plot = LinePlot(right, "Link Margin", "Margin [dB]")
        self.margin_plot.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        self.storage_plot = LinePlot(right, "Onboard Data", "Data [Mbit]")
        self.storage_plot.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.results_panel = Panel(right)
        self.results_panel.configure(width=220)
        self.results_panel.grid(row=1, column=1, sticky="nsew")
        self.results_panel.grid_propagate(False)

    def schedule_refresh(self) -> None:
        if self.page != "dash":
            return
        if self.update_job is not None:
            self.after_cancel(self.update_job)
        self.update_job = self.after(120, self.refresh_dashboard)

    def read_inputs(self) -> TTCInputs:
        earth = LinkConfig(
            name="Earth X-band downlink",
            frequency_mhz=8450.0,
            tx_power_w=self.tx_power.get(),
            tx_gain_dbi=self.tx_gain.get(),
            rx_gain_dbi=self.rx_gain.get(),
            system_losses_db=self.losses.get(),
            data_rate_kbps=self.data_rate.get(),
            required_ebn0_db=self.required_ebn0.get(),
            system_noise_temp_k=300.0,
        )
        moon = LinkConfig(
            name="Moon UHF uplink",
            frequency_mhz=435.0,
            tx_power_w=self.moon_tx_power.get(),
            tx_gain_dbi=self.moon_tx_gain.get(),
            rx_gain_dbi=self.moon_rx_gain.get(),
            system_losses_db=self.moon_losses.get(),
            data_rate_kbps=self.moon_data_rate.get(),
            required_ebn0_db=8.0,
            system_noise_temp_k=400.0,
        )
        return TTCInputs(
            earth_downlink=earth,
            moon_uplink=moon,
            data_generation_mbit_h=self.data_generation.get(),
            storage_capacity_mbit=self.storage_capacity.get(),
            initial_storage_mbit=min(self.initial_storage.get(), self.storage_capacity.get()),
            min_margin_db=self.min_margin.get(),
            moon_relay_enabled=self.moon_enabled.get(),
        )

    def refresh_dashboard(self) -> None:
        self.update_job = None
        gs = GroundStation(min_elevation_deg=self.min_elevation.get())
        data = simulate_ttc(self.read_inputs(), OrbitConfig(), gs)
        t = data["time_h"]
        required = self.min_margin.get()
        capacity = self.storage_capacity.get()
        earth_margin = data["earth_margin_db"]
        earth_ok = [value if value >= required else None for value in earth_margin]
        earth_bad = [value if value < required else None for value in earth_margin]

        self.ground.set_data(data["lat_deg"], data["lon_deg"], data["earth_contact"], gs)
        self.timeline.set_data(t, data["earth_contact"], data["moon_contact"])
        self.orbit_view.set_data(OrbitConfig(), gs)
        self.margin_plot.set_series([
            (t, earth_ok, "#00A6B4", "Earth OK"),
            (t, earth_bad, "#C1121F", "Earth FAIL"),
            (t, data["moon_margin_db"], "#2E7D32", "Moon relay"),
            (t, [required for _ in t], "#B8860B", "Required margin"),
        ])
        self.storage_plot.set_series([
            (t, data["data_storage_mbit"], COLORS["accent"], "stored"),
            (t, data["data_downlinked_mbit"], COLORS["purple"], "downlinked"),
            (t, [capacity for _ in t], COLORS["yellow"], "capacity"),
        ])
        self.update_results(data)

    def update_results(self, data: dict[str, object]) -> None:
        for child in self.results_panel.winfo_children():
            child.destroy()
        required = self.min_margin.get()
        capacity = self.storage_capacity.get()
        final_storage = float(data["final_storage_mbit"])
        max_storage = float(data["max_storage_mbit"])
        best_margin = float(data["best_earth_margin_db"])
        duration_min = float(data["duration_h"]) * 60.0
        visibility_min = float(data["total_visibility_min"])
        contact_min = float(data["total_contact_min"])
        visibility_pct = 100.0 * visibility_min / duration_min
        contact_pct = 100.0 * contact_min / duration_min
        earth_indices = [i for i, ok in enumerate(data["earth_contact"]) if ok]
        moon_indices = [i for i, ok in enumerate(data["moon_contact"]) if ok]
        earth_link_ok = bool(earth_indices) and min(data["earth_margin_db"][i] for i in earth_indices) >= required
        moon_link_ok = bool(moon_indices) and min(data["moon_margin_db"][i] for i in moon_indices) >= required
        storage_ok = max_storage <= capacity and final_storage < 0.95 * capacity
        requirements_ok = earth_link_ok and moon_link_ok and storage_ok

        title = tk.Label(self.results_panel, text="Results", bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 17, "bold"))
        title.pack(anchor="w", padx=16, pady=(14, 8))

        status = tk.Frame(self.results_panel, bg=COLORS["panel2"], highlightbackground=COLORS["line"], highlightthickness=1)
        status.pack(fill="x", padx=14, pady=(0, 10))
        tk.Label(status, text="Mission Status", bg=COLORS["panel2"], fg=COLORS["text"], font=(FONT, 13, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        status_items = [
            ("Earth link closes", earth_link_ok),
            ("Moon link closes", moon_link_ok),
            ("Storage OK", storage_ok),
            ("Requirements met", requirements_ok),
        ]
        for label, ok in status_items:
            mark = "[OK]" if ok else "[FAIL]"
            color = COLORS["green"] if ok else COLORS["red"]
            tk.Label(status, text=f"{mark} {label}", bg=COLORS["panel2"], fg=color, font=(FONT, 11, "bold")).pack(anchor="w", padx=10, pady=1)

        rows = [
            ("Geom visible", f"{visibility_min:.0f} min ({visibility_pct:.1f}%)", COLORS["accent"]),
            ("Comm valid", f"{contact_min:.0f} min ({contact_pct:.1f}%)", COLORS["green"] if earth_link_ok else COLORS["red"]),
            ("Earth windows", f"{len(data['earth_windows'])} of {len(data['earth_visibility_windows'])}", COLORS["accent"]),
            ("Moon contact", f"{data['moon_contact_min']:.0f} min", COLORS["green"] if moon_link_ok else COLORS["red"]),
            ("Downlinked", f"{data['total_downlinked_mbit']:.0f} Mbit", COLORS["purple"]),
            ("Final storage", f"{final_storage:.0f} Mbit", COLORS["green"] if storage_ok else COLORS["red"]),
            ("Best margin", f"{best_margin:.1f} dB", COLORS["green"] if best_margin >= required else COLORS["red"]),
        ]
        for name, value, color in rows:
            frame = tk.Frame(self.results_panel, bg=COLORS["panel"])
            frame.pack(fill="x", padx=16, pady=3)
            tk.Label(frame, text=name, bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 11, "bold")).pack(anchor="w")
            tk.Label(frame, text=value, bg=COLORS["panel"], fg=color, font=(FONT, 15, "bold")).pack(anchor="w")

        window_text = "\n".join(
            f"{idx}. {start:.2f}-{end:.2f} h ({(end - start) * 60.0:.0f} min)"
            for idx, (start, end) in enumerate(data["earth_windows"], start=1)
        )
        tk.Label(self.results_panel, text="Earth contact windows", bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 11, "bold")).pack(anchor="w", padx=16, pady=(8, 2))
        tk.Label(self.results_panel, text=window_text, bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 10), justify="left").pack(anchor="w", padx=16)
        note = "Long contact times are expected for a Molniya-type HEO when the apogee dwell region is visible from the high-latitude ground station."
        tk.Label(self.results_panel, text=note, bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 10), wraplength=185, justify="left").pack(anchor="w", padx=16, pady=(10, 14))


def main() -> None:
    enable_high_dpi()
    root = tk.Tk()
    root.tk.call("tk", "scaling", 1.0)
    global FONT
    FONT = choose_font(root)
    DashboardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
