# Project X LunaLink - TT&C Simulator

## About

This is a small university project for Spacecraft Design Fundamentals. It focuses on the TT&C subsystem of the Project X LunaLink mission and turns the communication analysis into a simple Python GUI.

The GUI is built with Tkinter and was developed with help from OpenAI Codex. The app lets the user adjust communication parameters, run a simplified simulation, and inspect the results through plots and summary values.

## Install and Run

Requirements:

- Python 3
- Tkinter, included with the standard Python installation on Windows/macOS

No external Python packages are needed, so there is no `pip install` step.

Run the app from the project folder:

```bash
python app.py
```

## What It Shows

The adjustable inputs include transmitter power, antenna gains, data rate, system losses, minimum elevation, required link margin, and onboard data storage.

The outputs include the ground track, communication windows, link margin, stored data, and downlinked data.
