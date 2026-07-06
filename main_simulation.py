"""Headless TT&C simulation launcher for the LunaLink submission."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

from orbit_model import GroundStation, OrbitConfig
from ttc_model import default_inputs, simulate_ttc

OUTPUT_DIR = Path("outputs")


def duration_minutes(windows: Iterable[tuple[float, float]]) -> float:
    return sum((end - start) * 60.0 for start, end in windows)


def min_visible_margin(results: dict[str, object]) -> float:
    margins = results["earth_margin_db"]
    visible = results["earth_visible"]
    values = [margin for margin, is_visible in zip(margins, visible) if is_visible]
    return min(values) if values else math.nan


def print_summary(results: dict[str, object], step_s: float) -> None:
    earth_windows = results["earth_windows"]
    print("LunaLink TT&C headless simulation")
    print("=" * 38)
    print(f"simulation duration [h]        : {results['duration_h']:.2f}")
    print(f"timestep [s]                  : {step_s:.0f}")
    print(f"Earth contact time [min]      : {results['total_contact_min']:.1f}")
    print(f"geometric visibility [min]    : {results['total_visibility_min']:.1f}")
    print(f"Earth contact windows         : {len(earth_windows)}")
    print(f"Moon contact time [min]       : {results['moon_contact_min']:.1f}")
    print(f"total downlinked data [Mbit]  : {results['total_downlinked_mbit']:.1f}")
    print(f"final onboard storage [Mbit]  : {results['final_storage_mbit']:.1f}")
    print(f"max onboard storage [Mbit]    : {results['max_storage_mbit']:.1f}")
    print(f"best link margin [dB]         : {results['best_earth_margin_db']:.2f}")
    print(f"min visible Earth margin [dB] : {min_visible_margin(results):.2f}")
    print()
    print("Earth contact diagnostic windows")
    print("start [h]   end [h]   duration [min]")
    if not earth_windows:
        print("none")
    for start, end in earth_windows:
        print(f"{start:8.2f}  {end:8.2f}  {(end - start) * 60.0:14.1f}")


def split_longitude_segments(lons: list[float]) -> list[list[int]]:
    segments: list[list[int]] = []
    current: list[int] = []
    for i, lon in enumerate(lons):
        if i > 0 and abs(lon - lons[i - 1]) > 180.0:
            if len(current) >= 2:
                segments.append(current)
            current = []
        current.append(i)
    if len(current) >= 2:
        segments.append(current)
    return segments


def contact_segments(base_segments: list[list[int]], contact: list[bool]) -> list[list[int]]:
    output: list[list[int]] = []
    for segment in base_segments:
        active: list[int] = []
        for i in segment:
            if contact[i]:
                active.append(i)
            else:
                if len(active) >= 2:
                    output.append(active)
                active = []
        if len(active) >= 2:
            output.append(active)
    return output


def export_plots(results: dict[str, object], inputs: object, output_dir: Path = OUTPUT_DIR) -> bool:
    output_dir.mkdir(exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print()
        print("Plot export skipped: matplotlib is not installed.")
        print("Install dependencies with: pip install -r requirements.txt")
        print(f"Output folder: {output_dir.resolve()}")
        return False
    time_h = results["time_h"]
    lats = results["lat_deg"]
    lons = results["lon_deg"]
    earth_contact = results["earth_contact"]
    moon_contact = results["moon_contact"]
    earth_margin = results["earth_margin_db"]
    moon_margin = results["moon_margin_db"]
    required = inputs.min_margin_db

    # Ground track.
    fig, ax = plt.subplots(figsize=(10.0, 5.4), dpi=140)
    segments = split_longitude_segments(lons)
    for segment in segments:
        ax.plot([lons[i] for i in segment], [lats[i] for i in segment], color="#6E6257", linewidth=1.8)
    for segment in contact_segments(segments, earth_contact):
        ax.plot([lons[i] for i in segment], [lats[i] for i in segment], color="#00A6B4", linewidth=2.8)
    gs = results["ground_station"]
    ax.scatter([gs.lon_deg], [gs.lat_deg], color="#00A6B4", edgecolor="#3A2416", s=60, zorder=4, label="Ottobrunn GS")
    ax.text(gs.lon_deg + 3.0, gs.lat_deg, "Ottobrunn GS", fontsize=9, fontweight="bold")
    ax.set_title("Ground Track", fontweight="bold")
    ax.set_xlabel("Longitude [deg]")
    ax.set_ylabel("Latitude [deg]")
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.grid(True, alpha=0.35)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(output_dir / "ground_track.png")
    plt.close(fig)

    # Link margin.
    earth_ok = [value if value >= required else math.nan for value in earth_margin]
    earth_fail = [value if value < required else math.nan for value in earth_margin]
    fig, ax = plt.subplots(figsize=(10.0, 5.0), dpi=140)
    ax.plot(time_h, earth_ok, color="#00A6B4", linewidth=2.5, label="Earth OK")
    ax.plot(time_h, earth_fail, color="#C1121F", linewidth=2.5, label="Earth FAIL")
    ax.plot(time_h, moon_margin, color="#2E7D32", linewidth=2.2, label="Moon relay")
    ax.axhline(required, color="#B8860B", linewidth=2.8, linestyle="--", label="Required margin")
    ax.set_title("Link Margin", fontweight="bold")
    ax.set_xlabel("Time [h]")
    ax.set_ylabel("Margin [dB]")
    ax.grid(True, alpha=0.35)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_dir / "link_margin.png")
    plt.close(fig)

    # Communication windows.
    fig, ax = plt.subplots(figsize=(10.0, 3.2), dpi=140)
    earth_windows = results["earth_windows"]
    moon_windows = results["moon_windows"]
    for start, end in earth_windows:
        ax.broken_barh([(start, end - start)], (18, 8), facecolors="#00A6B4")
    for start, end in moon_windows:
        ax.broken_barh([(start, end - start)], (6, 8), facecolors="#2E7D32")
    ax.set_title("Communication Windows", fontweight="bold")
    ax.set_xlabel("Time [h]")
    ax.set_yticks([22, 10])
    ax.set_yticklabels(["Earth GS", "Moon relay"])
    ax.set_xlim(0, results["duration_h"])
    ax.set_ylim(0, 32)
    ax.grid(True, axis="x", alpha=0.35)
    fig.tight_layout()
    fig.savefig(output_dir / "communication_windows.png")
    plt.close(fig)

    # Onboard storage.
    fig, ax = plt.subplots(figsize=(10.0, 5.0), dpi=140)
    ax.plot(time_h, results["data_storage_mbit"], color="#00A6B4", linewidth=2.4, label="Stored")
    ax.plot(time_h, results["data_downlinked_mbit"], color="#6F4A8E", linewidth=2.2, label="Downlinked")
    ax.axhline(inputs.storage_capacity_mbit, color="#3A2416", linewidth=2.2, linestyle="--", label="Capacity")
    ax.set_title("Onboard Data Storage", fontweight="bold")
    ax.set_xlabel("Time [h]")
    ax.set_ylabel("Data [Mbit]")
    ax.grid(True, alpha=0.35)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_dir / "onboard_storage.png")
    plt.close(fig)

    # Slant range and elevation.
    fig, ax1 = plt.subplots(figsize=(10.0, 5.0), dpi=140)
    ax2 = ax1.twinx()
    ax1.plot(time_h, results["earth_range_km"], color="#6E6257", linewidth=2.1, label="Slant range")
    ax2.plot(time_h, results["elevation_deg"], color="#00A6B4", linewidth=2.1, label="Elevation")
    ax2.axhline(results["ground_station"].min_elevation_deg, color="#B8860B", linewidth=2.0, linestyle="--", label="Min elevation")
    ax1.set_title("Slant Range and Elevation", fontweight="bold")
    ax1.set_xlabel("Time [h]")
    ax1.set_ylabel("Slant range [km]")
    ax2.set_ylabel("Elevation [deg]")
    ax1.grid(True, alpha=0.35)
    lines = ax1.get_lines() + ax2.get_lines()
    ax1.legend(lines, [line.get_label() for line in lines], loc="best")
    fig.tight_layout()
    fig.savefig(output_dir / "slant_range_elevation.png")
    plt.close(fig)

    print()
    print(f"Plots exported to: {output_dir.resolve()}")
    return True


def main() -> None:
    inputs = default_inputs()
    results = simulate_ttc(inputs, OrbitConfig(), GroundStation())
    print_summary(results, inputs.step_s)
    export_plots(results, inputs)


if __name__ == "__main__":
    main()
