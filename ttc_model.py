"""Mission-level TT&C simulation for Project X LunaLink."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from link_budget import LinkConfig, link_margin_db, link_summary
from orbit_model import GroundStation, OrbitConfig, eci_to_ecef, elevation_and_range, lat_lon_alt, orbit_phase, spacecraft_eci

MOON_RELAY_RANGE_KM = 384400.0


@dataclass(frozen=True)
class TTCInputs:
    earth_downlink: LinkConfig
    moon_uplink: LinkConfig
    data_generation_mbit_h: float = 180.0
    storage_capacity_mbit: float = 8000.0
    initial_storage_mbit: float = 1200.0
    min_margin_db: float = 3.0
    step_s: float = 180.0
    simulation_orbits: int = 3
    moon_relay_enabled: bool = True


def default_inputs() -> TTCInputs:
    return TTCInputs(
        earth_downlink=LinkConfig(
            name="Earth X-band downlink",
            frequency_mhz=8450.0,
            tx_power_w=50.0,
            tx_gain_dbi=35.0,
            rx_gain_dbi=52.0,
            system_losses_db=2.5,
            data_rate_kbps=100000.0,
            required_ebn0_db=9.6,
            system_noise_temp_k=300.0,
        ),
        moon_uplink=LinkConfig(
            name="Moon UHF uplink",
            frequency_mhz=435.0,
            tx_power_w=50.0,
            tx_gain_dbi=30.0,
            rx_gain_dbi=20.0,
            system_losses_db=2.5,
            data_rate_kbps=64.0,
            required_ebn0_db=8.0,
            system_noise_temp_k=400.0,
        ),
    )


def _contact_windows(times_h: list[float], active: list[bool]) -> list[tuple[float, float]]:
    windows: list[tuple[float, float]] = []
    start: float | None = None
    for time_h, is_active in zip(times_h, active):
        if is_active and start is None:
            start = time_h
        elif not is_active and start is not None:
            windows.append((start, time_h))
            start = None
    if start is not None:
        windows.append((start, times_h[-1]))
    return windows


def simulate_ttc(inputs: TTCInputs, orbit: OrbitConfig | None = None, gs: GroundStation | None = None) -> dict[str, Any]:
    orbit = orbit or OrbitConfig()
    gs = gs or GroundStation()
    duration_s = max(orbit.period_s * inputs.simulation_orbits, 36.0 * 3600.0)
    steps = max(2, int(duration_s / inputs.step_s) + 1)

    time_h: list[float] = []
    lat_deg: list[float] = []
    lon_deg: list[float] = []
    altitude_km: list[float] = []
    elevation_deg: list[float] = []
    earth_range_km: list[float] = []
    earth_margin_db: list[float] = []
    moon_margin_db: list[float] = []
    earth_contact: list[bool] = []
    earth_visible_flags: list[bool] = []
    moon_contact: list[bool] = []
    data_storage_mbit: list[float] = []
    data_downlinked_mbit: list[float] = []

    storage = inputs.initial_storage_mbit
    total_downlinked = 0.0
    dt_h = inputs.step_s / 3600.0

    for idx in range(steps):
        t_s = idx * inputs.step_s
        t_h = t_s / 3600.0
        eci = spacecraft_eci(t_s, orbit)
        ecef = eci_to_ecef(eci, t_s)
        lat, lon, alt = lat_lon_alt(ecef)
        elevation, range_km = elevation_and_range(ecef, gs)
        phase = orbit_phase(t_s, orbit)

        earth_margin = link_margin_db(inputs.earth_downlink, range_km)
        earth_visible = elevation >= gs.min_elevation_deg
        earth_ok = earth_visible and earth_margin >= inputs.min_margin_db

        # Simplified lunar relay assumption: relay is mainly useful near apogee.
        near_apogee = 0.38 <= phase <= 0.62
        moon_margin = link_margin_db(inputs.moon_uplink, MOON_RELAY_RANGE_KM)
        moon_ok = inputs.moon_relay_enabled and near_apogee and moon_margin >= inputs.min_margin_db

        generated = inputs.data_generation_mbit_h * dt_h
        storage = min(inputs.storage_capacity_mbit, storage + generated)

        downlink_rate_mbit_h = inputs.earth_downlink.data_rate_kbps * 3.6
        relay_rate_mbit_h = inputs.moon_uplink.data_rate_kbps * 3.6
        possible_downlink = 0.0
        if earth_ok:
            possible_downlink += downlink_rate_mbit_h * dt_h
        if moon_ok:
            possible_downlink += relay_rate_mbit_h * dt_h
        downlinked = min(storage, possible_downlink)
        storage -= downlinked
        total_downlinked += downlinked

        time_h.append(t_h)
        lat_deg.append(lat)
        lon_deg.append(lon)
        altitude_km.append(alt)
        elevation_deg.append(elevation)
        earth_range_km.append(range_km)
        earth_margin_db.append(earth_margin)
        moon_margin_db.append(moon_margin if near_apogee else -30.0)
        earth_contact.append(earth_ok)
        earth_visible_flags.append(earth_visible)
        moon_contact.append(moon_ok)
        data_storage_mbit.append(storage)
        data_downlinked_mbit.append(total_downlinked)

    earth_visibility_windows = _contact_windows(time_h, earth_visible_flags)
    earth_windows = _contact_windows(time_h, earth_contact)
    moon_windows = _contact_windows(time_h, moon_contact)
    visibility_minutes = sum((end - start) * 60.0 for start, end in earth_visibility_windows)
    contact_minutes = sum((end - start) * 60.0 for start, end in earth_windows)
    moon_minutes = sum((end - start) * 60.0 for start, end in moon_windows)

    earth_summary = link_summary(inputs.earth_downlink, max(earth_range_km))
    moon_summary = link_summary(inputs.moon_uplink, MOON_RELAY_RANGE_KM)

    return {
        "time_h": time_h,
        "lat_deg": lat_deg,
        "lon_deg": lon_deg,
        "altitude_km": altitude_km,
        "elevation_deg": elevation_deg,
        "earth_range_km": earth_range_km,
        "earth_margin_db": earth_margin_db,
        "moon_margin_db": moon_margin_db,
        "earth_contact": earth_contact,
        "earth_visible": earth_visible_flags,
        "moon_contact": moon_contact,
        "data_storage_mbit": data_storage_mbit,
        "data_downlinked_mbit": data_downlinked_mbit,
        "earth_visibility_windows": earth_visibility_windows,
        "earth_windows": earth_windows,
        "moon_windows": moon_windows,
        "earth_summary": earth_summary,
        "moon_summary": moon_summary,
        "total_visibility_min": visibility_minutes,
        "total_contact_min": contact_minutes,
        "moon_contact_min": moon_minutes,
        "total_downlinked_mbit": total_downlinked,
        "max_storage_mbit": max(data_storage_mbit),
        "final_storage_mbit": data_storage_mbit[-1],
        "min_earth_margin_db": min(earth_margin_db),
        "best_earth_margin_db": max(earth_margin_db),
        "moon_margin_db_constant": moon_margin_db,
        "period_h": orbit.period_s / 3600.0,
        "duration_h": duration_s / 3600.0,
        "ground_station": gs,
        "orbit": orbit,
    }

def format_earth_contact_diagnostics(results: dict[str, Any]) -> str:
    duration_h = float(results["duration_h"])
    duration_min = duration_h * 60.0
    visibility_min = float(results["total_visibility_min"])
    contact_min = float(results["total_contact_min"])
    visibility_pct = 100.0 * visibility_min / duration_min
    contact_pct = 100.0 * contact_min / duration_min
    lines = [
        "Earth contact diagnostic",
        f"Geometric visibility: {visibility_min:.1f} min ({visibility_pct:.1f} % of {duration_h:.1f} h)",
        f"Communication-valid: {contact_min:.1f} min ({contact_pct:.1f} % of {duration_h:.1f} h)",
        f"Geometric windows: {len(results['earth_visibility_windows'])}",
        f"Communication windows: {len(results['earth_windows'])}",
    ]
    for idx, (start, end) in enumerate(results["earth_windows"], start=1):
        lines.append(f"Comm {idx}: {start:.2f}-{end:.2f} h, {(end - start) * 60.0:.1f} min")
    return "\n".join(lines)


def print_earth_contact_diagnostics(results: dict[str, Any]) -> None:
    print(format_earth_contact_diagnostics(results))


