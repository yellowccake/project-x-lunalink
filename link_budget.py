"""RF link budget equations for Project X TT&C."""

from __future__ import annotations

import math
from dataclasses import dataclass

BOLTZMANN_DBW_PER_HZ_K = -228.6


@dataclass(frozen=True)
class LinkConfig:
    name: str
    frequency_mhz: float
    tx_power_w: float
    tx_gain_dbi: float
    rx_gain_dbi: float
    system_losses_db: float
    data_rate_kbps: float
    required_ebn0_db: float
    system_noise_temp_k: float = 500.0
    implementation_loss_db: float = 2.0


def watt_to_dbw(power_w: float) -> float:
    return 10.0 * math.log10(max(power_w, 1.0e-12))


def free_space_path_loss_db(range_km: float, frequency_mhz: float) -> float:
    return 32.44 + 20.0 * math.log10(max(range_km, 1.0e-9)) + 20.0 * math.log10(frequency_mhz)


def received_power_dbw(config: LinkConfig, range_km: float) -> float:
    eirp_dbw = watt_to_dbw(config.tx_power_w) + config.tx_gain_dbi
    return eirp_dbw + config.rx_gain_dbi - free_space_path_loss_db(range_km, config.frequency_mhz) - config.system_losses_db


def noise_density_dbw_hz(config: LinkConfig) -> float:
    return BOLTZMANN_DBW_PER_HZ_K + 10.0 * math.log10(config.system_noise_temp_k)


def ebn0_db(config: LinkConfig, range_km: float) -> float:
    pr_dbw = received_power_dbw(config, range_km)
    data_rate_bps = max(config.data_rate_kbps * 1000.0, 1.0)
    return pr_dbw - noise_density_dbw_hz(config) - 10.0 * math.log10(data_rate_bps)


def link_margin_db(config: LinkConfig, range_km: float) -> float:
    return ebn0_db(config, range_km) - config.required_ebn0_db - config.implementation_loss_db


def link_summary(config: LinkConfig, range_km: float) -> dict[str, float]:
    return {
        "range_km": range_km,
        "fspl_db": free_space_path_loss_db(range_km, config.frequency_mhz),
        "received_power_dbw": received_power_dbw(config, range_km),
        "ebn0_db": ebn0_db(config, range_km),
        "margin_db": link_margin_db(config, range_km),
    }
