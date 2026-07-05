# Project X LunaLink - TT&C Simulator

This project follows the **TT&C option** from `ProjectX_LunaLink_Brief_v2.pdf`.

TT&C means **Telemetry, Tracking, and Command**. The app is now a minimalist step-by-step wizard: the user enters assumptions page by page, runs the simulation, then views the outputs and graphs.

## Run

```powershell
cd C:\Users\Negar\Desktop\TUM_1st_sem\Spacecraft_Design_Fundamentals\project_x
python app.py
```

## Files

- `app.py` - Minimal dark-themed Tkinter GUI wizard.
- `orbit_model.py` - Simplified two-body Molniya orbit and Ottobrunn ground-station visibility.
- `link_budget.py` - Free-space RF link budget equations.
- `ttc_model.py` - Mission simulation combining orbit, contact windows, link margin, and data volume.

## Wizard Flow

1. **Welcome** - introduces the TT&C simulator.
2. **Mission** - shows fixed values from the PDF brief.
3. **Earth Link** - user chooses transmitter power, antenna gains, losses, data rate, Eb/N0, elevation, and required margin.
4. **Moon Relay** - user enables/disables the simplified Moon relay and chooses relay link assumptions.
5. **Data** - user chooses data generation rate, storage capacity, and initial stored data.
6. **Review** - user checks assumptions and starts the simulation.
7. **Results** - app shows ground track, contact windows, link margin, data storage, and summary metrics.

## What the PDF asks for in TT&C

The brief says the TT&C subsystem should:

- assume gains, losses, and antenna position
- define a link budget for Earth and Moon communication links
- simulate contact windows and data volume
- show ground track and communication windows
- provide a GUI where parameters are adjustable and plots update

## Fixed Mission Values

- Orbit: 500 x 36,000 km Molniya-type HEO
- Inclination: 63.4 deg
- Spacecraft mass: 500 kg
- Ground station: Ottobrunn, Germany, 48.07 N, 11.65 E
- Minimum elevation: adjustable, default 5 deg
- Simulation duration: 3 orbits

## Simplifications

- Two-body Keplerian orbit, no perturbations
- Spherical Earth visibility model
- Earth downlink uses X-band, default 8450 MHz
- Moon relay uses a simplified UHF link and is assumed available near apogee
- Link margin is based on free-space path loss and Eb/N0
- Data storage increases continuously and decreases during valid communication windows

## Report Notes

Useful wording for the report: the GUI separates user inputs from the calculation backend. The backend propagates the spacecraft orbit, checks ground-station visibility, evaluates the RF link budget, and integrates generated/downlinked data over three orbits.
