Project X LunaLink

Chosen subsystem: TT&C (Telemetry, Tracking, and Command).
This university project models the LunaLink communication subsystem with a Tkinter GUI and a headless simulation script. The simulation covers 36 h with a 180 s timestep.

Install
pip install -r requirements.txt

Run
Headless simulation:
python main_simulation.py

GUI:
python main_gui.py

The original GUI entry point still works:
python app.py

Outputs
main_simulation.py prints the numerical TT&C summary and Earth contact windows in the terminal. If matplotlib is installed, it also exports PNG plots to the outputs/ folder:
- ground_track.png
- link_margin.png
- communication_windows.png
- onboard_storage.png
- slant_range_elevation.png

GUI controls
The GUI lets the user adjust transmitter power, antenna gains, data rate, losses, storage capacity, minimum elevation, and Moon relay assumptions. The plots show the ground track, communication windows, link margins, onboard storage, and orbit visualization.
