"""Orbit and visibility helpers for the Project X TT&C simulator.

This is a deliberately compact two-body model. It is good enough for a
student trade study and clear enough to explain in the report.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

EARTH_RADIUS_KM = 6378.137
EARTH_MU_KM3_S2 = 398600.4418
EARTH_ROT_RATE_RAD_S = 7.2921159e-5


@dataclass(frozen=True)
class OrbitConfig:
    perigee_alt_km: float = 500.0
    apogee_alt_km: float = 36000.0
    inclination_deg: float = 63.4
    raan_deg: float = 20.0
    arg_perigee_deg: float = 270.0
    true_anomaly0_deg: float = 0.0

    @property
    def semi_major_axis_km(self) -> float:
        rp = EARTH_RADIUS_KM + self.perigee_alt_km
        ra = EARTH_RADIUS_KM + self.apogee_alt_km
        return 0.5 * (rp + ra)

    @property
    def eccentricity(self) -> float:
        rp = EARTH_RADIUS_KM + self.perigee_alt_km
        ra = EARTH_RADIUS_KM + self.apogee_alt_km
        return (ra - rp) / (ra + rp)

    @property
    def period_s(self) -> float:
        return 2.0 * math.pi * math.sqrt(self.semi_major_axis_km**3 / EARTH_MU_KM3_S2)


@dataclass(frozen=True)
class GroundStation:
    name: str = "Ottobrunn, Germany"
    lat_deg: float = 48.07
    lon_deg: float = 11.65
    min_elevation_deg: float = 5.0


def _rot_z(vec: tuple[float, float, float], angle_rad: float) -> tuple[float, float, float]:
    x, y, z = vec
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return c * x - s * y, s * x + c * y, z


def _rot_x(vec: tuple[float, float, float], angle_rad: float) -> tuple[float, float, float]:
    x, y, z = vec
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return x, c * y - s * z, s * y + c * z


def solve_kepler(mean_anomaly_rad: float, eccentricity: float) -> float:
    eccentric_anomaly = mean_anomaly_rad
    for _ in range(12):
        f = eccentric_anomaly - eccentricity * math.sin(eccentric_anomaly) - mean_anomaly_rad
        fp = 1.0 - eccentricity * math.cos(eccentric_anomaly)
        eccentric_anomaly -= f / fp
    return eccentric_anomaly


def spacecraft_eci(time_s: float, orbit: OrbitConfig) -> tuple[float, float, float]:
    a = orbit.semi_major_axis_km
    e = orbit.eccentricity
    n = math.sqrt(EARTH_MU_KM3_S2 / a**3)

    e0 = 2.0 * math.atan2(
        math.sqrt(1.0 - e) * math.sin(math.radians(orbit.true_anomaly0_deg) / 2.0),
        math.sqrt(1.0 + e) * math.cos(math.radians(orbit.true_anomaly0_deg) / 2.0),
    )
    m0 = e0 - e * math.sin(e0)
    mean_anomaly = (m0 + n * time_s) % (2.0 * math.pi)
    eccentric_anomaly = solve_kepler(mean_anomaly, e)

    x_orb = a * (math.cos(eccentric_anomaly) - e)
    y_orb = a * math.sqrt(1.0 - e**2) * math.sin(eccentric_anomaly)
    r_orb = (x_orb, y_orb, 0.0)

    vec = _rot_z(r_orb, math.radians(orbit.arg_perigee_deg))
    vec = _rot_x(vec, math.radians(orbit.inclination_deg))
    vec = _rot_z(vec, math.radians(orbit.raan_deg))
    return vec


def eci_to_ecef(eci: tuple[float, float, float], time_s: float) -> tuple[float, float, float]:
    return _rot_z(eci, -EARTH_ROT_RATE_RAD_S * time_s)


def lat_lon_alt(ecef: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = ecef
    radius = math.sqrt(x * x + y * y + z * z)
    lat = math.degrees(math.asin(z / radius))
    lon = math.degrees(math.atan2(y, x))
    alt = radius - EARTH_RADIUS_KM
    return lat, lon, alt


def ground_station_ecef(gs: GroundStation) -> tuple[float, float, float]:
    lat = math.radians(gs.lat_deg)
    lon = math.radians(gs.lon_deg)
    r = EARTH_RADIUS_KM
    return r * math.cos(lat) * math.cos(lon), r * math.cos(lat) * math.sin(lon), r * math.sin(lat)


def elevation_and_range(ecef_sc: tuple[float, float, float], gs: GroundStation) -> tuple[float, float]:
    sx, sy, sz = ecef_sc
    gx, gy, gz = ground_station_ecef(gs)
    rx, ry, rz = sx - gx, sy - gy, sz - gz
    range_km = math.sqrt(rx * rx + ry * ry + rz * rz)

    lat = math.radians(gs.lat_deg)
    lon = math.radians(gs.lon_deg)
    up = (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))
    dot_up = rx * up[0] + ry * up[1] + rz * up[2]
    elevation = math.degrees(math.asin(dot_up / range_km))
    return elevation, range_km


def orbit_phase(time_s: float, orbit: OrbitConfig) -> float:
    return (time_s % orbit.period_s) / orbit.period_s
