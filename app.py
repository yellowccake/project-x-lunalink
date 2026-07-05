
"""Project X LunaLink TT&C wizard GUI.
Run with: python app.py
"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import font as tkfont

from link_budget import LinkConfig
from orbit_model import GroundStation, OrbitConfig
from ttc_model import TTCInputs, simulate_ttc

COLORS = {
    "bg": "#08111f", "panel": "#0c1728", "panel2": "#101d31", "panel3": "#152238",
    "line": "#a7b0bf", "line_dim": "#2c3a50", "text": "#ffffff", "black": "#05070b",
    "accent": "#45c7ff", "green": "#33d17a", "red": "#ff4d5e", "yellow": "#ffd166", "purple": "#b99cff",
}
FONT = "Computer Modern Roman"
PANEL_RADIUS = 34



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
    for family in ("Computer Modern Roman", "Latin Modern Roman", "Latin Modern Roman 10", "CMU Serif", "Modern No. 20", "Modern", "Times New Roman"):
        if family in available:
            return family
    return "Times New Roman"


def rounded_rect(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float, radius: float, **kwargs: object) -> int:
    points = [x1+radius,y1,x2-radius,y1,x2,y1,x2,y1+radius,x2,y2-radius,x2,y2,x2-radius,y2,x1+radius,y2,x1,y2,x1,y2-radius,x1,y1+radius,x1,y1]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class RoundedPanel(tk.Frame):
    def __init__(self, master: tk.Misc, fill: str = COLORS["panel"], outline: str = COLORS["line"], radius: int = PANEL_RADIUS) -> None:
        super().__init__(master, bg=COLORS["bg"], bd=0, highlightthickness=0)
        self.fill = fill
        self.outline = outline
        self.radius = radius
        self.background = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0, bd=0)
        self.background.place(x=0, y=0, relwidth=1, relheight=1)
        self.bind("<Configure>", self.draw_background)

    def draw_background(self, _event: tk.Event | None = None) -> None:
        self.background.delete("all")
        width = max(self.winfo_width(), 2)
        height = max(self.winfo_height(), 2)
        rounded_rect(self.background, 1, 1, width - 2, height - 2, self.radius, fill=self.fill, outline=self.outline, width=1)


class RoundedButton(tk.Canvas):
    def __init__(self, master: tk.Misc, text: str, command: object, width: int = 122, height: int = 44, circular: bool = False, icon: str | None = None) -> None:
        super().__init__(master, width=width, height=height, bg=COLORS["bg"], highlightthickness=0, cursor="hand2")
        self.text, self.command, self.circular, self.icon = text, command, circular, icon
        self.enabled, self.spinner_angle, self.spinner_job = True, 0, None
        self.bind("<Button-1>", self._click)
        self.draw()

    def configure(self, cnf: object | None = None, **kwargs: object) -> None:  # type: ignore[override]
        if "text" in kwargs: self.text = str(kwargs.pop("text"))
        if "command" in kwargs: self.command = kwargs.pop("command")
        if "state" in kwargs: self.enabled = kwargs.pop("state") != "disabled"
        if "icon" in kwargs: self.icon = kwargs.pop("icon")
        if "circular" in kwargs: self.circular = bool(kwargs.pop("circular"))
        if "width" in kwargs or "height" in kwargs:
            super().configure(width=int(kwargs.pop("width", self.cget("width"))), height=int(kwargs.pop("height", self.cget("height"))))
        if kwargs: super().configure(**kwargs)
        self.draw()
    config = configure

    def _click(self, _event: tk.Event) -> None:
        if self.enabled and self.command:
            self.command()

    def draw(self) -> None:
        self.delete("all")
        w, h = int(float(self.cget("width"))), int(float(self.cget("height")))
        fill = COLORS["black"] if self.enabled else COLORS["panel3"]
        if self.circular:
            self.create_oval(2, 2, w-2, h-2, fill=fill, outline=COLORS["line"], width=1)
        else:
            rounded_rect(self, 1, 1, w-1, h-1, 22, fill=fill, outline=COLORS["line"], width=1)
        if self.icon == "play":
            cx, cy = w/2+2, h/2
            self.create_polygon(cx-7, cy-10, cx-7, cy+10, cx+11, cy, fill=COLORS["text"], outline="")
        elif self.icon == "spinner":
            self.create_arc(13, 13, w-13, h-13, start=self.spinner_angle, extent=270, style="arc", outline=COLORS["text"], width=3)
        else:
            self.create_text(w/2, h/2, text=self.text, fill=COLORS["text"], font=(FONT, 14, "bold"))

    def start_spinner(self) -> None:
        self.icon, self.enabled = "spinner", False
        def tick() -> None:
            self.spinner_angle = (self.spinner_angle + 18) % 360
            self.draw()
            self.spinner_job = self.after(45, tick)
        tick()

    def stop_spinner(self) -> None:
        if self.spinner_job is not None:
            self.after_cancel(self.spinner_job)
        self.spinner_job, self.icon, self.enabled = None, None, True
        self.draw()


class ToggleSwitch(tk.Canvas):
    def __init__(self, master: tk.Misc, variable: tk.BooleanVar, text: str) -> None:
        super().__init__(master, width=340, height=52, bg=COLORS["panel"], highlightthickness=0, cursor="hand2")
        self.variable, self.text = variable, text
        self.variable.trace_add("write", lambda *_: self.draw())
        self.bind("<Button-1>", self.toggle)
        self.draw()

    def toggle(self, _event: tk.Event) -> None:
        self.variable.set(not self.variable.get())

    def draw(self) -> None:
        self.delete("all")
        active = self.variable.get()
        rounded_rect(self, 16, 10, 82, 42, 16, fill=COLORS["accent"] if active else COLORS["panel3"], outline=COLORS["line"])
        x = 66 if active else 32
        self.create_oval(x-12, 14, x+12, 38, fill=COLORS["text"], outline="")
        self.create_text(100, 26, text=self.text, anchor="w", fill=COLORS["text"], font=(FONT, 14, "bold"))


class RotaryKnob(tk.Canvas):
    def __init__(self, master: tk.Misc, label: str, variable: tk.DoubleVar, low: float, high: float, unit: str) -> None:
        super().__init__(master, width=200, height=210, bg=COLORS["panel"], highlightthickness=0, cursor="hand2")
        self.label, self.variable, self.low, self.high, self.unit = label, variable, low, high, unit
        self.resolution = 0.1 if unit in {"dB", "dBi"} else 1.0
        self.start_deg, self.sweep_deg = 225.0, 270.0
        self.variable.trace_add("write", lambda *_: self.draw())
        self.bind("<Button-1>", self.set_from_event)
        self.bind("<B1-Motion>", self.set_from_event)
        self.draw()

    def format_value(self) -> str:
        decimals = 1 if self.unit in {"dB", "dBi"} else 0
        return f"{self.variable.get():.{decimals}f} {self.unit}"

    def set_from_event(self, event: tk.Event) -> None:
        cx, cy = 100.0, 86.0
        angle = math.degrees(math.atan2(cy - event.y, event.x - cx)) % 360.0
        if angle >= self.start_deg: pos = (angle - self.start_deg) / self.sweep_deg
        elif angle <= 135.0: pos = (angle + 360.0 - self.start_deg) / self.sweep_deg
        else: pos = 0.0 if angle < 180.0 else 1.0
        value = self.low + max(0.0, min(1.0, pos)) * (self.high - self.low)
        value = round(value / self.resolution) * self.resolution
        self.variable.set(max(self.low, min(self.high, value)))

    def draw(self) -> None:
        self.delete("all")
        cx, cy, r = 100.0, 88.0, 58.0
        pos = (self.variable.get() - self.low) / max(0.0001, self.high - self.low)
        active = self.sweep_deg * pos
        for i in range(11):
            deg = self.start_deg + self.sweep_deg * (i / 10)
            rad = math.radians(deg)
            r1, r2 = r + 9, r + (16 if i in {0, 5, 10} else 13)
            self.create_line(cx+math.cos(rad)*r1, cy-math.sin(rad)*r1, cx+math.cos(rad)*r2, cy-math.sin(rad)*r2, fill=COLORS["line"])
        self.create_arc(cx-r, cy-r, cx+r, cy+r, start=self.start_deg, extent=self.sweep_deg, style="arc", outline=COLORS["line_dim"], width=8)
        self.create_arc(cx-r, cy-r, cx+r, cy+r, start=self.start_deg, extent=active, style="arc", outline=COLORS["accent"], width=8)
        self.create_oval(cx-39, cy-39, cx+39, cy+39, fill=COLORS["black"], outline=COLORS["line"], width=1)
        rad = math.radians(self.start_deg + active)
        self.create_line(cx, cy, cx+math.cos(rad)*33, cy-math.sin(rad)*33, fill=COLORS["text"], width=3)
        self.create_text(cx, cy+29, text=self.format_value(), fill=COLORS["text"], font=(FONT, 14, "bold"))
        self.create_text(30, 162, text=f"{self.low:g}", fill=COLORS["text"], font=(FONT, 14))
        self.create_text(170, 162, text=f"{self.high:g}", fill=COLORS["text"], font=(FONT, 14))
        self.create_text(cx, 194, text=self.label, fill=COLORS["text"], font=(FONT, 14, "bold"), width=180)

class PlotCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc, title: str, y_label: str, x_label: str = "Time [h]", height: int = 230) -> None:
        super().__init__(master, height=height, bg=COLORS["bg"], highlightthickness=0, bd=0)
        self.title, self.y_label, self.x_label = title, y_label, x_label
        self.series: list[tuple[list[float], list[float | None], str, str]] = []
        self.bind("<Configure>", lambda _event: self.draw())

    def set_series(self, series: list[tuple[list[float], list[float | None], str, str]]) -> None:
        self.series = series
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        w, h = max(self.winfo_width(), 320), max(self.winfo_height(), 180)
        rounded_rect(self, 1, 1, w - 2, h - 2, PANEL_RADIUS, fill=COLORS["panel"], outline=COLORS["line"], width=1)
        left, right, top, bottom = 62, 22, 38, 42
        pw, ph = w - left - right, h - top - bottom
        self.create_text(left, 16, text=self.title, anchor="w", fill=COLORS["text"], font=(FONT, 14, "bold"))
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
            ymin, ymax = ymin - 1.0, ymax + 1.0
        pad = 0.08 * (ymax - ymin)
        ymin, ymax = ymin - pad, ymax + pad
        for i in range(5):
            frac = i / 4
            y = top + ph - frac * ph
            val = ymin + frac * (ymax - ymin)
            self.create_line(left, y, left + pw, y, fill=COLORS["line_dim"])
            self.create_text(left - 8, y, text=f"{val:.0f}", anchor="e", fill=COLORS["text"], font=(FONT, 14))
        for xv, yv, color, _label in self.series:
            seg: list[float] = []
            for xval, yval in zip(xv, yv):
                if yval is None:
                    if len(seg) >= 4:
                        self.create_line(*seg, fill=color, width=2)
                    seg = []
                    continue
                x = left + (xval - xmin) / max(0.001, xmax - xmin) * pw
                y = top + ph - (yval - ymin) / max(0.001, ymax - ymin) * ph
                seg.extend([x, y])
            if len(seg) >= 4:
                self.create_line(*seg, fill=color, width=2)
        lx = left + pw - 146
        for i, (_x, _y, color, label) in enumerate(self.series):
            y = 18 + i * 17
            self.create_line(lx, y, lx + 18, y, fill=color, width=3)
            self.create_text(lx + 24, y, text=label, anchor="w", fill=COLORS["text"], font=(FONT, 14))
        self.create_text(left + pw / 2, h - 12, text=self.x_label, fill=COLORS["text"], font=(FONT, 17))
        self.create_text(16, top + ph / 2, text=self.y_label, angle=90, fill=COLORS["text"], font=(FONT, 17))


class GroundTrackCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, bg=COLORS["bg"], highlightthickness=0, bd=0, height=310)
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

    def draw(self) -> None:
        self.delete("all")
        w, h = max(self.winfo_width(), 520), max(self.winfo_height(), 260)
        rounded_rect(self, 1, 1, w - 2, h - 2, PANEL_RADIUS, fill=COLORS["panel"], outline=COLORS["line"], width=1)
        left, top, right, bottom = 58, 42, 22, 44
        pw, ph = w - left - right, h - top - bottom
        self.create_text(left, 18, text="Ground Track", anchor="w", fill=COLORS["text"], font=(FONT, 14, "bold"))
        for lon in range(-180, 181, 30):
            x, _ = self.xy(0, lon, left, top, pw, ph)
            self.create_line(x, top, x, top + ph, fill=COLORS["line_dim"])
            if lon % 60 == 0:
                self.create_text(x, top + ph + 14, text=str(lon), fill=COLORS["text"], font=(FONT, 14))
        for lat in range(-60, 61, 30):
            _, y = self.xy(lat, 0, left, top, pw, ph)
            self.create_line(left, y, left + pw, y, fill=COLORS["line_dim"])
            self.create_text(left - 8, y, text=str(lat), anchor="e", fill=COLORS["text"], font=(FONT, 14))
        self.create_rectangle(left, top, left + pw, top + ph, outline=COLORS["line"], width=1)
        if len(self.lats) >= 2:
            for i in range(1, len(self.lats)):
                if abs(self.lons[i] - self.lons[i - 1]) > 180.0:
                    continue
                x1, y1 = self.xy(self.lats[i-1], self.lons[i-1], left, top, pw, ph)
                x2, y2 = self.xy(self.lats[i], self.lons[i], left, top, pw, ph)
                self.create_line(x1, y1, x2, y2, fill=COLORS["accent"] if self.contact[i] else "#7f8da3", width=2)
        gx, gy = self.xy(self.gs.lat_deg, self.gs.lon_deg, left, top, pw, ph)
        self.create_oval(gx-6, gy-6, gx+6, gy+6, fill=COLORS["yellow"], outline=COLORS["black"], width=2)
        self.create_text(gx+10, gy, text="Ottobrunn GS", anchor="w", fill=COLORS["text"], font=(FONT, 9, "bold"))
        self.create_text(left + pw / 2, h - 12, text="Longitude [deg]", fill=COLORS["text"], font=(FONT, 17))
        self.create_text(14, top + ph / 2, text="Latitude [deg]", angle=90, fill=COLORS["text"], font=(FONT, 17))
        self.create_line(w-170, 21, w-148, 21, fill=COLORS["accent"], width=3)
        self.create_text(w-142, 21, text="contact", anchor="w", fill=COLORS["text"], font=(FONT, 14))
        self.create_line(w-92, 21, w-70, 21, fill="#7f8da3", width=3)
        self.create_text(w-64, 21, text="no contact", anchor="w", fill=COLORS["text"], font=(FONT, 14))


class TimelineCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, bg=COLORS["bg"], highlightthickness=0, bd=0, height=130)
        self.time_h: list[float] = []
        self.earth: list[bool] = []
        self.moon: list[bool] = []
        self.bind("<Configure>", lambda _event: self.draw())

    def set_data(self, time_h: list[float], earth: list[bool], moon: list[bool]) -> None:
        self.time_h, self.earth, self.moon = time_h, earth, moon
        self.draw()

    def draw_bar(self, y: int, active: list[bool], color: str, label: str, left: int, width: int) -> None:
        self.create_text(left, y, text=label, anchor="w", fill=COLORS["text"], font=(FONT, 9, "bold"))
        if not self.time_h:
            return
        tmax = max(self.time_h)
        span = width - left - 130
        rounded_rect(self, left+96, y-8, left+96+span, y+8, 10, fill=COLORS["panel3"], outline=COLORS["line_dim"])
        for i in range(1, len(self.time_h)):
            if active[i]:
                x1 = left + 96 + self.time_h[i-1] / tmax * span
                x2 = left + 96 + self.time_h[i] / tmax * span
                rounded_rect(self, x1, y-8, x2, y+8, 9, fill=color, outline=color)

    def draw(self) -> None:
        self.delete("all")
        w, left = max(self.winfo_width(), 520), 18
        rounded_rect(self, 1, 1, w - 2, 128, PANEL_RADIUS, fill=COLORS["panel"], outline=COLORS["line"], width=1)
        self.create_text(left, 18, text="Communication Windows", anchor="w", fill=COLORS["text"], font=(FONT, 14, "bold"))
        self.draw_bar(58, self.earth, COLORS["accent"], "Earth GS", left, w)
        self.draw_bar(90, self.moon, COLORS["green"], "Moon relay", left, w)
        self.create_text(w/2 + 35, 118, text="Time [h]", fill=COLORS["text"], font=(FONT, 17))


class SatelliteHeroCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, bg=COLORS["bg"], highlightthickness=0, bd=0, height=300)
        self.bind("<Configure>", lambda _event: self.draw())

    def draw(self) -> None:
        self.delete("all")
        w, h = max(self.winfo_width(), 520), max(self.winfo_height(), 260)
        rounded_rect(self, 1, 1, w - 2, h - 2, PANEL_RADIUS, fill=COLORS["panel"], outline=COLORS["line"], width=1)
        cx, cy = w * 0.72, h * 0.52
        silver, soft, glow = "#34435a", "#1c2a42", "#19344d"
        self.create_oval(cx-165, cy-165, cx+165, cy+165, outline=soft, width=2)
        self.create_arc(cx-215, cy-110, cx+235, cy+125, start=190, extent=145, style="arc", outline=glow, width=2)
        self.create_rectangle(cx-36, cy-28, cx+36, cy+28, fill="#132139", outline=silver, width=1)
        self.create_line(cx-78, cy, cx-36, cy, fill=silver, width=2)
        self.create_line(cx+36, cy, cx+78, cy, fill=silver, width=2)
        for side in (-1, 1):
            x0, x1 = cx + side * 82, cx + side * 156
            self.create_rectangle(min(x0, x1), cy-31, max(x0, x1), cy+31, fill="#10233a", outline=silver, width=1)
            for j in range(1, 4):
                x = min(x0, x1) + j * abs(x1 - x0) / 4
                self.create_line(x, cy-31, x, cy+31, fill="#223750")
            self.create_line(min(x0, x1), cy, max(x0, x1), cy, fill="#223750")
        self.create_oval(cx-18, cy-18, cx+18, cy+18, outline=COLORS["accent"], width=1)
        self.create_line(cx, cy+28, cx+42, cy+72, fill=silver, width=1)
        self.create_oval(cx+36, cy+66, cx+48, cy+78, outline=silver, width=1)
        self.create_text(34, 48, text="LunaLink", anchor="w", fill=COLORS["text"], font=(FONT, 38, "bold"))
        self.create_text(36, 92, text="TT&C simulation wizard", anchor="w", fill=COLORS["text"], font=(FONT, 17))
        self.create_text(36, 132, text="Adjust link assumptions, run the simulation, and inspect communication performance over three orbits.", anchor="w", fill=COLORS["text"], font=(FONT, 15), width=470)

class WizardApp(tk.Frame):
    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root, bg=COLORS["bg"])
        self.root = root
        self.root.title("Project X LunaLink - TT&C Wizard")
        self.root.geometry("1260x800")
        self.root.minsize(1100, 720)
        self.pack(fill="both", expand=True)
        self.page_index = 0
        self.pages = ["Welcome", "Mission", "Earth Link", "Moon Relay", "Data", "Review", "Results"]
        self.simulation_data: dict[str, object] | None = None
        self.tx_power = tk.DoubleVar(value=8.0)
        self.tx_gain = tk.DoubleVar(value=18.0)
        self.rx_gain = tk.DoubleVar(value=42.0)
        self.losses = tk.DoubleVar(value=3.0)
        self.data_rate = tk.DoubleVar(value=512.0)
        self.required_ebn0 = tk.DoubleVar(value=9.6)
        self.min_elevation = tk.DoubleVar(value=5.0)
        self.min_margin = tk.DoubleVar(value=3.0)
        self.moon_enabled = tk.BooleanVar(value=True)
        self.moon_tx_power = tk.DoubleVar(value=12.0)
        self.moon_tx_gain = tk.DoubleVar(value=8.0)
        self.moon_rx_gain = tk.DoubleVar(value=10.0)
        self.moon_losses = tk.DoubleVar(value=4.0)
        self.moon_data_rate = tk.DoubleVar(value=64.0)
        self.data_generation = tk.DoubleVar(value=180.0)
        self.storage_capacity = tk.DoubleVar(value=8000.0)
        self.initial_storage = tk.DoubleVar(value=1200.0)
        self._build_shell()
        self.show_page(0)

    def _build_shell(self) -> None:
        self.sidebar = tk.Frame(self, bg=COLORS["panel"], width=260, highlightthickness=1, highlightbackground=COLORS["line_dim"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.main = tk.Frame(self, bg=COLORS["bg"])
        self.main.pack(side="right", fill="both", expand=True)
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)
        self.content_canvas = tk.Canvas(self.main, bg=COLORS["bg"], highlightthickness=0)
        self.content_canvas.grid(row=0, column=0, sticky="nsew", padx=(28, 0), pady=(24, 12))
        self.content_scrollbar = tk.Scrollbar(self.main, orient="vertical", command=self.content_canvas.yview, bg=COLORS["black"], troughcolor=COLORS["bg"], activebackground=COLORS["line"], relief="flat")
        self.content_scrollbar.grid(row=0, column=1, sticky="ns", pady=(24, 12))
        self.content_canvas.configure(yscrollcommand=self.content_scrollbar.set)
        self.content = tk.Frame(self.content_canvas, bg=COLORS["bg"])
        self.content_window = self.content_canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._on_content_configure)
        self.content_canvas.bind("<Configure>", self._on_canvas_configure)
        self.content_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.nav = tk.Frame(self.main, bg=COLORS["bg"])
        self.nav.grid(row=1, column=0, columnspan=2, sticky="ew", padx=28, pady=(0, 22))
        self.back_button = RoundedButton(self.nav, "Back", self.previous_page)
        self.back_button.pack(side="left")
        self.next_button = RoundedButton(self.nav, "Next", self.next_page)
        self.next_button.pack(side="right")
        self._draw_sidebar()

    def _on_content_configure(self, _event: tk.Event) -> None:
        self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.content_canvas.itemconfigure(self.content_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.content_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _draw_sidebar(self) -> None:
        for child in self.sidebar.winfo_children():
            child.destroy()
        tk.Label(self.sidebar, text="LunaLink", bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 26, "bold")).pack(anchor="w", padx=24, pady=(28, 2))
        tk.Label(self.sidebar, text="TT&C simulation wizard", bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 17)).pack(anchor="w", padx=24, pady=(0, 28))
        for i, name in enumerate(self.pages):
            active = i == self.page_index
            row = tk.Frame(self.sidebar, bg=COLORS["panel"])
            row.pack(fill="x", padx=18, pady=5)
            tk.Label(row, text="●", bg=COLORS["panel"], fg=COLORS["accent"] if active else COLORS["line"], font=(FONT, 17)).pack(side="left")
            tk.Label(row, text=f" {i + 1}. {name}", bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 14, "bold" if active else "normal")).pack(side="left")

    def clear_content(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        self.content_canvas.yview_moveto(0)

    def show_page(self, index: int) -> None:
        self.page_index = max(0, min(index, len(self.pages) - 1))
        self.clear_content()
        self._draw_sidebar()
        [self.welcome_page, self.mission_page, self.earth_link_page, self.moon_page, self.data_page, self.review_page, self.results_page][self.page_index]()
        self.back_button.configure(state="disabled" if self.page_index == 0 else "normal", circular=False, icon=None, text="Back", width=122, height=44)
        if self.page_index == len(self.pages) - 2:
            self.next_button.configure(text="", command=self.run_simulation, circular=True, icon="play", width=54, height=54)
        elif self.page_index == len(self.pages) - 1:
            self.next_button.configure(text="Restart", command=lambda: self.show_page(0), circular=False, icon=None, width=128, height=44)
        else:
            self.next_button.configure(text="Next", command=self.next_page, circular=False, icon=None, width=122, height=44)

    def next_page(self) -> None:
        self.show_page(self.page_index + 1)

    def previous_page(self) -> None:
        self.show_page(self.page_index - 1)

    def title(self, heading: str, subheading: str) -> None:
        tk.Label(self.content, text=heading, bg=COLORS["bg"], fg=COLORS["text"], font=(FONT, 34, "bold")).pack(anchor="w")
        tk.Label(self.content, text=subheading, bg=COLORS["bg"], fg=COLORS["text"], font=(FONT, 17), wraplength=920, justify="left").pack(anchor="w", pady=(7, 22))

    def panel(self, parent: tk.Misc | None = None) -> tk.Frame:
        return RoundedPanel(parent or self.content)

    def card(self, parent: tk.Misc, title: str, value: str, color: str = COLORS["accent"]) -> tk.Frame:
        frame = self.panel(parent)
        tk.Label(frame, text=title, bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 14, "bold")).pack(anchor="w", padx=16, pady=(14, 2))
        tk.Label(frame, text=value, bg=COLORS["panel"], fg=color, font=(FONT, 20, "bold"), wraplength=360, justify="left").pack(anchor="w", padx=16, pady=(0, 14))
        return frame

    def note(self, text: str) -> None:
        frame = self.panel()
        frame.pack(fill="x", pady=(0, 18))
        tk.Label(frame, text=text, bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 14), wraplength=900, justify="left").pack(anchor="w", padx=18, pady=14)

    def knob_grid(self, parent: tk.Misc, specs: list[tuple[str, tk.DoubleVar, float, float, str]]) -> None:
        for i, (label, var, low, high, unit) in enumerate(specs):
            RotaryKnob(parent, label, var, low, high, unit).grid(row=i // 4, column=i % 4, padx=16, pady=16, sticky="n")
        for col in range(4):
            parent.columnconfigure(col, weight=1)

    def welcome_page(self) -> None:
        self.title("Project X LunaLink", "A compact TT&C simulator for exploring communication performance over the fixed Project X orbit.")
        hero = self.panel()
        hero.pack(fill="both", expand=True)
        SatelliteHeroCanvas(hero).pack(fill="both", expand=True, padx=1, pady=1)

    def mission_page(self) -> None:
        self.title("Mission Setup", "Fixed values from the project brief. These define the orbit and ground station used by the simulation.")
        self.note("Interpretation: these values are not design knobs here. The later pages change the communication system assumptions while this mission geometry stays fixed.")
        grid = tk.Frame(self.content, bg=COLORS["bg"])
        grid.pack(fill="x")
        fixed = [("Orbit", "500 x 36,000 km"), ("Inclination", "63.4 deg"), ("Orbit type", "Molniya-type HEO"), ("Spacecraft mass", "500 kg"), ("Ground station", "Ottobrunn, Germany"), ("Location", "48.07 N, 11.65 E"), ("Simulation length", "3 orbits"), ("Min elevation", "Adjusted on Earth Link page")]
        for i, (name, value) in enumerate(fixed):
            self.card(grid, name, value, COLORS["text"]).grid(row=i // 2, column=i % 2, sticky="ew", padx=6, pady=6)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

    def earth_link_page(self) -> None:
        self.title("Earth Link Budget", "Adjust the Earth downlink assumptions. More transmit power or antenna gain raises link margin; more losses or higher data rate lowers it.")
        self.note("How to read it later: on the results page, the Earth margin curve must stay above the required margin line during usable contact windows.")
        form = self.panel()
        form.pack(fill="x")
        self.knob_grid(form, [("Transmitter power", self.tx_power, 1, 30, "W"), ("Spacecraft antenna gain", self.tx_gain, 0, 30, "dBi"), ("Ground antenna gain", self.rx_gain, 15, 55, "dBi"), ("System losses", self.losses, 0, 10, "dB"), ("Downlink data rate", self.data_rate, 32, 2048, "kbps"), ("Required Eb/N0", self.required_ebn0, 3, 14, "dB"), ("Minimum elevation", self.min_elevation, 0, 20, "deg"), ("Required link margin", self.min_margin, 0, 10, "dB")])

    def moon_page(self) -> None:
        self.title("Moon Relay", "Adjust the simplified Moon relay assumptions. This model treats the relay as available near apogee and evaluates a separate UHF link budget.")
        self.note("Interpretation: if the Moon relay margin stays below the required margin, the relay contributes no useful data transfer in this simplified model.")
        form = self.panel()
        form.pack(fill="x")
        ToggleSwitch(form, self.moon_enabled, "Enable simplified Moon relay").grid(row=0, column=0, columnspan=4, sticky="w", padx=16, pady=(16, 4))
        specs = [("Relay TX power", self.moon_tx_power, 1, 40, "W"), ("Relay TX antenna", self.moon_tx_gain, 0, 30, "dBi"), ("Relay RX antenna", self.moon_rx_gain, 0, 30, "dBi"), ("Relay system losses", self.moon_losses, 0, 12, "dB"), ("Relay data rate", self.moon_data_rate, 8, 512, "kbps")]
        for i, (label, var, low, high, unit) in enumerate(specs):
            RotaryKnob(form, label, var, low, high, unit).grid(row=1 + i // 4, column=i % 4, padx=16, pady=16, sticky="n")
        for col in range(4):
            form.columnconfigure(col, weight=1)

    def data_page(self) -> None:
        self.title("Data Handling", "Adjust how much data is generated onboard and how much memory is available between communication windows.")
        self.note("How to read it later: stored data rises when data is generated and drops during successful downlink. Reaching storage capacity indicates a poor data-handling design.")
        form = self.panel()
        form.pack(fill="x")
        self.knob_grid(form, [("Data generated", self.data_generation, 0, 800, "Mbit/h"), ("Storage capacity", self.storage_capacity, 1000, 20000, "Mbit"), ("Initial stored data", self.initial_storage, 0, 8000, "Mbit")])

    def review_page(self) -> None:
        self.title("Review and Run", "Check the assumptions. Press the circular play button to run the simulation and open the results page.")
        self.note("The play button does not change the model. It only sends the current GUI values into the existing TT&C simulation backend.")
        grid = tk.Frame(self.content, bg=COLORS["bg"])
        grid.pack(fill="x")
        rows = [("Earth downlink", f"{self.tx_power.get():.0f} W, {self.tx_gain.get():.1f} dBi spacecraft, {self.rx_gain.get():.1f} dBi ground"), ("Data rate", f"{self.data_rate.get():.0f} kbps, required Eb/N0 {self.required_ebn0.get():.1f} dB"), ("Contact rule", f"Elevation >= {self.min_elevation.get():.0f} deg and margin >= {self.min_margin.get():.1f} dB"), ("Moon relay", "Enabled" if self.moon_enabled.get() else "Disabled"), ("Data handling", f"{self.data_generation.get():.0f} Mbit/h generated, {self.storage_capacity.get():.0f} Mbit storage"), ("Simulation", "3 orbits using the fixed Project X orbit")]
        for i, (name, value) in enumerate(rows):
            self.card(grid, name, value, COLORS["text"]).grid(row=i, column=0, sticky="ew", padx=4, pady=6)
        grid.columnconfigure(0, weight=1)

    def read_inputs(self) -> TTCInputs:
        earth = LinkConfig(name="Earth X-band downlink", frequency_mhz=8450.0, tx_power_w=self.tx_power.get(), tx_gain_dbi=self.tx_gain.get(), rx_gain_dbi=self.rx_gain.get(), system_losses_db=self.losses.get(), data_rate_kbps=self.data_rate.get(), required_ebn0_db=self.required_ebn0.get(), system_noise_temp_k=450.0)
        moon = LinkConfig(name="Moon UHF uplink", frequency_mhz=435.0, tx_power_w=self.moon_tx_power.get(), tx_gain_dbi=self.moon_tx_gain.get(), rx_gain_dbi=self.moon_rx_gain.get(), system_losses_db=self.moon_losses.get(), data_rate_kbps=self.moon_data_rate.get(), required_ebn0_db=8.0, system_noise_temp_k=650.0)
        return TTCInputs(earth_downlink=earth, moon_uplink=moon, data_generation_mbit_h=self.data_generation.get(), storage_capacity_mbit=self.storage_capacity.get(), initial_storage_mbit=min(self.initial_storage.get(), self.storage_capacity.get()), min_margin_db=self.min_margin.get(), moon_relay_enabled=self.moon_enabled.get())

    def run_simulation(self) -> None:
        self.clear_content()
        self.title("Simulation Running", "Computing orbit propagation, ground-station visibility, link margins, and data storage over 3 orbits.")
        self.next_button.start_spinner()
        self.back_button.configure(state="disabled")
        def finish() -> None:
            gs = GroundStation(min_elevation_deg=self.min_elevation.get())
            self.simulation_data = simulate_ttc(self.read_inputs(), OrbitConfig(), gs)
            self.next_button.stop_spinner()
            self.show_page(len(self.pages) - 1)
        self.root.after(650, finish)

    def results_page(self) -> None:
        if self.simulation_data is None:
            self.run_simulation()
            return
        data = self.simulation_data
        required = self.min_margin.get()
        capacity = self.storage_capacity.get()
        final_storage = float(data["final_storage_mbit"])
        best_margin = float(data["best_earth_margin_db"])
        self.title("Simulation Results", "Use these plots to check visibility, link margin, and data handling over the three-orbit simulation.")
        self.note("Interpretation: red margin segments are below the required threshold. Stored data should remain below capacity, and contact bars show when communication is available.")
        cards = tk.Frame(self.content, bg=COLORS["bg"])
        cards.pack(fill="x", pady=(0, 12))
        summary = [("Earth contact", f"{data['total_contact_min']:.0f} min", COLORS["accent"]), ("Moon contact", f"{data['moon_contact_min']:.0f} min", COLORS["green"]), ("Downlinked", f"{data['total_downlinked_mbit']:.0f} Mbit", COLORS["purple"]), ("Final storage", f"{data['final_storage_mbit']:.0f} Mbit", COLORS["red"] if final_storage >= 0.95 * capacity else COLORS["yellow"]), ("Best margin", f"{data['best_earth_margin_db']:.1f} dB", COLORS["red"] if best_margin < required else COLORS["green"]), ("Pass count", str(len(data["earth_windows"])), COLORS["accent"])]
        for i, (name, value, color) in enumerate(summary):
            self.card(cards, name, value, color).grid(row=0, column=i, sticky="ew", padx=4)
            cards.columnconfigure(i, weight=1)
        plots = tk.Frame(self.content, bg=COLORS["bg"])
        plots.pack(fill="both", expand=True)
        plots.columnconfigure(0, weight=1)
        plots.columnconfigure(1, weight=1)
        plots.rowconfigure(0, weight=3)
        plots.rowconfigure(1, weight=1)
        plots.rowconfigure(2, weight=2)
        map_canvas = GroundTrackCanvas(plots)
        map_canvas.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        map_canvas.set_data(data["lat_deg"], data["lon_deg"], data["earth_contact"], GroundStation(min_elevation_deg=self.min_elevation.get()))
        timeline = TimelineCanvas(plots)
        timeline.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        timeline.set_data(data["time_h"], data["earth_contact"], data["moon_contact"])
        t = data["time_h"]
        earth_margin = data["earth_margin_db"]
        earth_ok = [value if value >= required else None for value in earth_margin]
        earth_bad = [value if value < required else None for value in earth_margin]
        margin = PlotCanvas(plots, "Link Margin", "Margin [dB]", "Time [h]", height=230)
        margin.grid(row=2, column=0, sticky="nsew", padx=(0, 4))
        margin.set_series([(t, earth_ok, COLORS["accent"], "Earth ok"), (t, earth_bad, COLORS["red"], "Earth below req"), (t, data["moon_margin_db"], COLORS["green"], "Moon"), (t, [required for _ in t], COLORS["yellow"], "required")])
        storage = PlotCanvas(plots, "Onboard Data", "Data [Mbit]", "Time [h]", height=230)
        storage.grid(row=2, column=1, sticky="nsew", padx=(4, 0))
        storage.set_series([(t, data["data_storage_mbit"], COLORS["accent"], "stored"), (t, data["data_downlinked_mbit"], COLORS["purple"], "downlinked"), (t, [capacity for _ in t], COLORS["yellow"], "capacity")])


def main() -> None:
    root = tk.Tk()
    global FONT
    FONT = choose_font(root)
    WizardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()







