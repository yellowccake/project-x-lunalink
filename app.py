"""Project X LunaLink TT&C wizard GUI.

Run with: python app.py
"""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from link_budget import LinkConfig
from orbit_model import GroundStation, OrbitConfig
from ttc_model import TTCInputs, simulate_ttc


COLORS = {
    "bg": "#0f172a",
    "panel": "#111827",
    "panel2": "#1f2937",
    "line": "#334155",
    "text": "#e5e7eb",
    "muted": "#9ca3af",
    "accent": "#38bdf8",
    "green": "#22c55e",
    "red": "#ef4444",
    "yellow": "#facc15",
    "purple": "#a78bfa",
}
FONT = "Segoe UI"


class PlotCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc, title: str, y_label: str, height: int = 230) -> None:
        super().__init__(master, height=height, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
        self.title = title
        self.y_label = y_label
        self.series: list[tuple[list[float], list[float], str, str]] = []
        self.bind("<Configure>", lambda _event: self.draw())

    def set_series(self, series: list[tuple[list[float], list[float], str, str]]) -> None:
        self.series = series
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 320)
        height = max(self.winfo_height(), 180)
        left, right, top, bottom = 58, 18, 36, 36
        plot_w = width - left - right
        plot_h = height - top - bottom
        self.create_text(left, 16, text=self.title, anchor="w", fill=COLORS["text"], font=(FONT, 11, "bold"))
        self.create_line(left, top, left, top + plot_h, fill=COLORS["line"])
        self.create_line(left, top + plot_h, left + plot_w, top + plot_h, fill=COLORS["line"])
        if not self.series:
            return
        xs = [x for x_values, _y_values, _color, _label in self.series for x in x_values]
        ys = [y for _x_values, y_values, _color, _label in self.series for y in y_values]
        if not xs or not ys:
            return
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        if math.isclose(ymin, ymax):
            ymin -= 1.0
            ymax += 1.0
        pad = 0.08 * (ymax - ymin)
        ymin -= pad
        ymax += pad
        for i in range(5):
            frac = i / 4
            y = top + plot_h - frac * plot_h
            value = ymin + frac * (ymax - ymin)
            self.create_line(left, y, left + plot_w, y, fill="#223047")
            self.create_text(left - 8, y, text=f"{value:.0f}", anchor="e", fill=COLORS["muted"], font=(FONT, 8))
        for x_values, y_values, color, _label in self.series:
            points: list[float] = []
            for x_value, y_value in zip(x_values, y_values):
                x = left + (x_value - xmin) / max(0.001, xmax - xmin) * plot_w
                y = top + plot_h - (y_value - ymin) / max(0.001, ymax - ymin) * plot_h
                points.extend([x, y])
            if len(points) >= 4:
                self.create_line(*points, fill=color, width=2)
        legend_x = left + plot_w - 136
        for index, (_x, _y, color, label) in enumerate(self.series):
            y = 18 + index * 17
            self.create_line(legend_x, y, legend_x + 18, y, fill=color, width=3)
            self.create_text(legend_x + 24, y, text=label, anchor="w", fill=COLORS["text"], font=(FONT, 8))
        self.create_text(left + plot_w / 2, height - 12, text="Time [h]", fill=COLORS["muted"], font=(FONT, 8))
        self.create_text(14, top + plot_h / 2, text=self.y_label, angle=90, fill=COLORS["muted"], font=(FONT, 8))


class GroundTrackCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"], height=300)
        self.lats: list[float] = []
        self.lons: list[float] = []
        self.contact: list[bool] = []
        self.gs = GroundStation()
        self.bind("<Configure>", lambda _event: self.draw())

    def set_data(self, lats: list[float], lons: list[float], contact: list[bool], gs: GroundStation) -> None:
        self.lats = lats
        self.lons = lons
        self.contact = contact
        self.gs = gs
        self.draw()

    def xy(self, lat: float, lon: float, width: int, height: int) -> tuple[float, float]:
        return (lon + 180.0) / 360.0 * width, (90.0 - lat) / 180.0 * height

    def draw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 500)
        height = max(self.winfo_height(), 240)
        self.create_rectangle(0, 0, width, height, fill=COLORS["panel"], outline="")
        for lon in range(-180, 181, 30):
            x, _ = self.xy(0, lon, width, height)
            self.create_line(x, 0, x, height, fill="#223047")
        for lat in range(-60, 61, 30):
            _, y = self.xy(lat, 0, width, height)
            self.create_line(0, y, width, y, fill="#223047")
        self.create_text(18, 18, text="Ground Track", anchor="w", fill=COLORS["text"], font=(FONT, 12, "bold"))
        if len(self.lats) < 2:
            return
        for index in range(1, len(self.lats)):
            if abs(self.lons[index] - self.lons[index - 1]) > 180.0:
                continue
            x1, y1 = self.xy(self.lats[index - 1], self.lons[index - 1], width, height)
            x2, y2 = self.xy(self.lats[index], self.lons[index], width, height)
            color = COLORS["accent"] if self.contact[index] else "#64748b"
            self.create_line(x1, y1, x2, y2, fill=color, width=2)
        gx, gy = self.xy(self.gs.lat_deg, self.gs.lon_deg, width, height)
        self.create_oval(gx - 6, gy - 6, gx + 6, gy + 6, fill=COLORS["yellow"], outline=COLORS["bg"], width=2)
        self.create_text(gx + 10, gy, text="Ottobrunn GS", anchor="w", fill=COLORS["text"], font=(FONT, 9, "bold"))


class TimelineCanvas(tk.Canvas):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"], height=120)
        self.time_h: list[float] = []
        self.earth: list[bool] = []
        self.moon: list[bool] = []
        self.bind("<Configure>", lambda _event: self.draw())

    def set_data(self, time_h: list[float], earth: list[bool], moon: list[bool]) -> None:
        self.time_h = time_h
        self.earth = earth
        self.moon = moon
        self.draw()

    def draw_bar(self, y: int, active: list[bool], color: str, label: str, width: int) -> None:
        left = 18
        self.create_text(left, y, text=label, anchor="w", fill=COLORS["text"], font=(FONT, 9, "bold"))
        if not self.time_h:
            return
        tmax = max(self.time_h)
        span = width - left - 130
        for index in range(1, len(self.time_h)):
            if active[index]:
                x1 = left + 96 + self.time_h[index - 1] / tmax * span
                x2 = left + 96 + self.time_h[index] / tmax * span
                self.create_rectangle(x1, y - 8, x2, y + 8, fill=color, outline=color)

    def draw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 500)
        self.create_text(18, 18, text="Communication Windows", anchor="w", fill=COLORS["text"], font=(FONT, 12, "bold"))
        self.draw_bar(56, self.earth, COLORS["accent"], "Earth GS", width)
        self.draw_bar(88, self.moon, COLORS["green"], "Moon relay", width)


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
        self.sidebar = tk.Frame(self, bg=COLORS["panel"], width=260)
        self.sidebar.pack(side="left", fill="y")

        self.main = tk.Frame(self, bg=COLORS["bg"])
        self.main.pack(side="right", fill="both", expand=True)
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(0, weight=1)

        self.content_canvas = tk.Canvas(self.main, bg=COLORS["bg"], highlightthickness=0)
        self.content_canvas.grid(row=0, column=0, sticky="nsew", padx=(28, 0), pady=(24, 12))
        self.content_scrollbar = tk.Scrollbar(self.main, orient="vertical", command=self.content_canvas.yview, bg=COLORS["panel"], troughcolor=COLORS["bg"], activebackground=COLORS["accent"], relief="flat")
        self.content_scrollbar.grid(row=0, column=1, sticky="ns", pady=(24, 12))
        self.content_canvas.configure(yscrollcommand=self.content_scrollbar.set)

        self.content = tk.Frame(self.content_canvas, bg=COLORS["bg"])
        self.content_window = self.content_canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._on_content_configure)
        self.content_canvas.bind("<Configure>", self._on_canvas_configure)
        self.content_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.nav = tk.Frame(self.main, bg=COLORS["bg"])
        self.nav.grid(row=1, column=0, columnspan=2, sticky="ew", padx=28, pady=(0, 22))
        self.back_button = self._button(self.nav, "Back", self.previous_page, bg=COLORS["panel2"])
        self.back_button.pack(side="left")
        self.next_button = self._button(self.nav, "Next", self.next_page, bg=COLORS["accent"], fg="#06121f")
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
        tk.Label(self.sidebar, text="LunaLink", bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 20, "bold")).pack(anchor="w", padx=22, pady=(24, 2))
        tk.Label(self.sidebar, text="TT&C simulation wizard", bg=COLORS["panel"], fg=COLORS["muted"], font=(FONT, 10)).pack(anchor="w", padx=22, pady=(0, 24))
        for index, name in enumerate(self.pages):
            active = index == self.page_index
            color = COLORS["accent"] if active else COLORS["muted"]
            marker = "●" if active else "○"
            text = f"{marker}  {index + 1}. {name}"
            tk.Label(self.sidebar, text=text, bg=COLORS["panel"], fg=color, font=(FONT, 11, "bold" if active else "normal")).pack(anchor="w", padx=22, pady=9)

    def _button(self, parent: tk.Misc, text: str, command: object, bg: str, fg: str = COLORS["text"]) -> tk.Button:
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=bg, activeforeground=fg, relief="flat", bd=0, padx=20, pady=10, font=(FONT, 10, "bold"), cursor="hand2")

    def clear_content(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        self.content_canvas.yview_moveto(0)

    def show_page(self, index: int) -> None:
        self.page_index = max(0, min(index, len(self.pages) - 1))
        self.clear_content()
        self._draw_sidebar()
        renderers = [self.welcome_page, self.mission_page, self.earth_link_page, self.moon_page, self.data_page, self.review_page, self.results_page]
        renderers[self.page_index]()
        self.back_button.configure(state="disabled" if self.page_index == 0 else "normal")
        if self.page_index == len(self.pages) - 2:
            self.next_button.configure(text="Run Simulation", command=self.run_simulation, bg=COLORS["green"], fg="#04130a")
        elif self.page_index == len(self.pages) - 1:
            self.next_button.configure(text="Restart", command=lambda: self.show_page(0), bg=COLORS["panel2"], fg=COLORS["text"])
        else:
            self.next_button.configure(text="Next", command=self.next_page, bg=COLORS["accent"], fg="#06121f")

    def next_page(self) -> None:
        self.show_page(self.page_index + 1)

    def previous_page(self) -> None:
        self.show_page(self.page_index - 1)

    def title(self, heading: str, subheading: str) -> None:
        tk.Label(self.content, text=heading, bg=COLORS["bg"], fg=COLORS["text"], font=(FONT, 24, "bold")).pack(anchor="w")
        tk.Label(self.content, text=subheading, bg=COLORS["bg"], fg=COLORS["muted"], font=(FONT, 11), wraplength=850, justify="left").pack(anchor="w", pady=(6, 22))

    def panel(self, parent: tk.Misc | None = None) -> tk.Frame:
        frame = tk.Frame(parent or self.content, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
        return frame

    def card(self, parent: tk.Misc, title: str, value: str, color: str = COLORS["accent"]) -> tk.Frame:
        frame = self.panel(parent)
        tk.Label(frame, text=title, bg=COLORS["panel"], fg=COLORS["muted"], font=(FONT, 9, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(frame, text=value, bg=COLORS["panel"], fg=color, font=(FONT, 17, "bold")).pack(anchor="w", padx=14, pady=(0, 12))
        return frame

    def slider(self, parent: tk.Misc, label: str, var: tk.DoubleVar, low: float, high: float, unit: str, row: int) -> None:
        tk.Label(parent, text=label, bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 10, "bold")).grid(row=row, column=0, sticky="w", padx=18, pady=(12, 0))
        value_label = tk.Label(parent, bg=COLORS["panel"], fg=COLORS["accent"], font=(FONT, 10, "bold"), width=14, anchor="e")
        value_label.grid(row=row, column=1, sticky="e", padx=18, pady=(12, 0))

        def refresh(*_args: object) -> None:
            decimals = 1 if unit in {"dB", "dBi"} else 0
            value_label.configure(text=f"{var.get():.{decimals}f} {unit}")

        refresh()
        var.trace_add("write", refresh)
        scale = tk.Scale(parent, from_=low, to=high, resolution=0.1 if unit in {"dB", "dBi"} else 1, variable=var, orient="horizontal", showvalue=False, bg=COLORS["panel"], fg=COLORS["text"], troughcolor=COLORS["panel2"], activebackground=COLORS["accent"], highlightthickness=0, bd=0)
        scale.grid(row=row + 1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 8))

    def welcome_page(self) -> None:
        self.title("Project X LunaLink", "A guided TT&C simulator for the project brief: define link assumptions, run the orbit/contact simulation, and inspect communication performance.")
        hero = self.panel()
        hero.pack(fill="both", expand=True)
        tk.Label(hero, text="Telemetry, Tracking, and Command", bg=COLORS["panel"], fg=COLORS["accent"], font=(FONT, 24, "bold")).pack(anchor="w", padx=28, pady=(34, 8))
        tk.Label(hero, text="This app will walk through the exact TT&C workflow: mission setup, Earth downlink budget, Moon relay assumptions, data handling, and final simulation results.", bg=COLORS["panel"], fg=COLORS["text"], font=(FONT, 13), wraplength=760, justify="left").pack(anchor="w", padx=28, pady=(0, 24))
        points = ["Ground track and contact windows", "Free-space link budget and link margin", "Data generated, stored, and downlinked over 3 orbits"]
        for point in points:
            tk.Label(hero, text=f"  {point}", bg=COLORS["panel"], fg=COLORS["muted"], font=(FONT, 12)).pack(anchor="w", padx=34, pady=6)

    def mission_page(self) -> None:
        self.title("Mission Setup", "These are fixed values from the PDF brief. You mainly tune the TT&C design choices in the next pages.")
        grid = tk.Frame(self.content, bg=COLORS["bg"])
        grid.pack(fill="x")
        fixed = [("Orbit", "500 x 36,000 km"), ("Inclination", "63.4 deg"), ("Orbit type", "Molniya-type HEO"), ("Spacecraft mass", "500 kg"), ("Ground station", "Ottobrunn, Germany"), ("Location", "48.07 N, 11.65 E"), ("Simulation length", "3 orbits"), ("Min elevation", "Adjustable, default 5 deg")]
        for index, (name, value) in enumerate(fixed):
            c = self.card(grid, name, value, COLORS["text"])
            c.grid(row=index // 2, column=index % 2, sticky="ew", padx=6, pady=6)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

    def earth_link_page(self) -> None:
        self.title("Earth Link Budget", "Choose the main Earth downlink assumptions. Higher power and antenna gain improve margin; higher data rate makes the link harder.")
        form = self.panel()
        form.pack(fill="x")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        self.slider(form, "Transmitter power", self.tx_power, 1, 30, "W", 0)
        self.slider(form, "Spacecraft antenna gain", self.tx_gain, 0, 30, "dBi", 2)
        self.slider(form, "Ground antenna gain", self.rx_gain, 15, 55, "dBi", 4)
        self.slider(form, "System losses", self.losses, 0, 10, "dB", 6)
        self.slider(form, "Downlink data rate", self.data_rate, 32, 2048, "kbps", 8)
        self.slider(form, "Required Eb/N0", self.required_ebn0, 3, 14, "dB", 10)
        self.slider(form, "Minimum elevation", self.min_elevation, 0, 20, "deg", 12)
        self.slider(form, "Required link margin", self.min_margin, 0, 10, "dB", 14)

    def moon_page(self) -> None:
        self.title("Moon Relay", "The brief mentions Moon communication windows. This version uses a simplified relay assumption near apogee, with its own UHF link budget.")
        form = self.panel()
        form.pack(fill="x")
        tk.Checkbutton(form, text="Enable simplified Moon relay", variable=self.moon_enabled, bg=COLORS["panel"], fg=COLORS["text"], selectcolor=COLORS["panel2"], activebackground=COLORS["panel"], activeforeground=COLORS["text"], font=(FONT, 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=14)
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        self.slider(form, "Relay TX power", self.moon_tx_power, 1, 40, "W", 1)
        self.slider(form, "Relay TX antenna", self.moon_tx_gain, 0, 30, "dBi", 3)
        self.slider(form, "Relay RX antenna", self.moon_rx_gain, 0, 30, "dBi", 5)
        self.slider(form, "Relay system losses", self.moon_losses, 0, 12, "dB", 7)
        self.slider(form, "Relay data rate", self.moon_data_rate, 8, 512, "kbps", 9)

    def data_page(self) -> None:
        self.title("Data Handling", "Now choose how much data the spacecraft creates and how much storage it has between communication windows.")
        form = self.panel()
        form.pack(fill="x")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        self.slider(form, "Data generated", self.data_generation, 0, 800, "Mbit/h", 0)
        self.slider(form, "Storage capacity", self.storage_capacity, 1000, 20000, "Mbit", 2)
        self.slider(form, "Initial stored data", self.initial_storage, 0, 8000, "Mbit", 4)

    def review_page(self) -> None:
        self.title("Review and Run", "Check the assumptions. Then run the simulation and the results page will open automatically.")
        grid = tk.Frame(self.content, bg=COLORS["bg"])
        grid.pack(fill="x")
        rows = [
            ("Earth downlink", f"{self.tx_power.get():.0f} W, {self.tx_gain.get():.1f} dBi spacecraft, {self.rx_gain.get():.1f} dBi ground"),
            ("Data rate", f"{self.data_rate.get():.0f} kbps, required Eb/N0 {self.required_ebn0.get():.1f} dB"),
            ("Contact rule", f"Elevation >= {self.min_elevation.get():.0f} deg and margin >= {self.min_margin.get():.1f} dB"),
            ("Moon relay", "Enabled" if self.moon_enabled.get() else "Disabled"),
            ("Data handling", f"{self.data_generation.get():.0f} Mbit/h generated, {self.storage_capacity.get():.0f} Mbit storage"),
            ("Simulation", "3 orbits using the fixed Project X orbit"),
        ]
        for index, (name, value) in enumerate(rows):
            c = self.card(grid, name, value, COLORS["text"])
            c.grid(row=index, column=0, sticky="ew", padx=4, pady=6)
        grid.columnconfigure(0, weight=1)
        tk.Label(self.content, text="When you press Run Simulation, the backend calls simulate_ttc(...) and fills the result plots.", bg=COLORS["bg"], fg=COLORS["muted"], font=(FONT, 11)).pack(anchor="w", pady=(18, 0))

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
            system_noise_temp_k=450.0,
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
            system_noise_temp_k=650.0,
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

    def run_simulation(self) -> None:
        self.clear_content()
        self.title("Simulation Running", "Computing orbit propagation, ground-station visibility, link margins, and data storage over 3 orbits.")
        bar = ttk.Progressbar(self.content, mode="indeterminate")
        bar.pack(fill="x", pady=24)
        bar.start(12)
        self.next_button.configure(state="disabled")
        self.back_button.configure(state="disabled")

        def finish() -> None:
            gs = GroundStation(min_elevation_deg=self.min_elevation.get())
            self.simulation_data = simulate_ttc(self.read_inputs(), OrbitConfig(), gs)
            bar.stop()
            self.next_button.configure(state="normal")
            self.show_page(len(self.pages) - 1)

        self.root.after(650, finish)

    def results_page(self) -> None:
        if self.simulation_data is None:
            self.run_simulation()
            return
        data = self.simulation_data
        self.title("Simulation Results", "These plots and summary numbers are the final outputs for the TT&C analysis.")
        cards = tk.Frame(self.content, bg=COLORS["bg"])
        cards.pack(fill="x", pady=(0, 12))
        summary = [
            ("Earth contact", f"{data['total_contact_min']:.0f} min", COLORS["accent"]),
            ("Moon contact", f"{data['moon_contact_min']:.0f} min", COLORS["green"]),
            ("Downlinked", f"{data['total_downlinked_mbit']:.0f} Mbit", COLORS["purple"]),
            ("Final storage", f"{data['final_storage_mbit']:.0f} Mbit", COLORS["yellow"]),
            ("Best margin", f"{data['best_earth_margin_db']:.1f} dB", COLORS["green"]),
            ("Pass count", str(len(data["earth_windows"])), COLORS["accent"]),
        ]
        for index, (name, value, color) in enumerate(summary):
            self.card(cards, name, value, color).grid(row=0, column=index, sticky="ew", padx=4)
            cards.columnconfigure(index, weight=1)

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

        margin = PlotCanvas(plots, "Link Margin", "Margin [dB]", height=220)
        margin.grid(row=2, column=0, sticky="nsew", padx=(0, 4))
        t = data["time_h"]
        margin.set_series([
            (t, data["earth_margin_db"], COLORS["accent"], "Earth"),
            (t, data["moon_margin_db"], COLORS["green"], "Moon"),
            (t, [self.min_margin.get() for _ in t], COLORS["yellow"], "required"),
        ])

        storage = PlotCanvas(plots, "Onboard Data", "Mbit", height=220)
        storage.grid(row=2, column=1, sticky="nsew", padx=(4, 0))
        storage.set_series([
            (t, data["data_storage_mbit"], COLORS["accent"], "stored"),
            (t, data["data_downlinked_mbit"], COLORS["purple"], "downlinked"),
            (t, [self.storage_capacity.get() for _ in t], COLORS["yellow"], "capacity"),
        ])


def main() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TProgressbar", background=COLORS["accent"], troughcolor=COLORS["panel2"], bordercolor=COLORS["line"], lightcolor=COLORS["accent"], darkcolor=COLORS["accent"])
    WizardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

