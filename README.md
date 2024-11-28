GROUP 18

Members :-
Aakhil Anvar
Navdeep Singh
Sara Shaikh

Project: CRAWLER Protocol Simulation

Table of Contents=>
-> Introduction
-> Prerequisites
-> Installation
-> Running the Project - Using the runme.bat Script OR - Manual Execution
-> Notes

Introduction=>

This project simulates a secure and dynamic Low Earth Orbit (LEO) satellite communication network using the CRAWLER protocol. The system relays secure instructions via satellites to a robot in challenging environments, such as warzones, with the ability to switch infrastructure gateways based on channel availability.

Prerequisites=>

Python 3.6 or higher is required.
Ensure that pip (Python package installer) is installed for Python 3.
The following Python libraries are required:
cryptography
A WINDOWS operating system is recommended.


Installation=>

Download the Project Files

Ensure that all the project files are present in the same directory:

leo-link.py
satellite.py
satellites.json
positions.json (will be generated automatically)
path.json (will be generated automatically)
requirements.txt
runme.bat
Install Required Python Libraries

Open a terminal, navigate to the project directory, and run:

pip3 install -r requirements.txt

=>Running the Project

* IP Addresses in satellite.json are set to run on local host for a single machine. If multiple machines need to be connected, then IP Addresses need to be changed accordingly.

-> Using the runme.bat Script
We have provided a runme.bat script to automate the execution of all components in separate terminals.

Make the Script Executable

In the terminal, navigate to the project directory and run:

Run:

./runme.bat
This script will:

Install the required Python packages.
Open multiple terminal windows, each running a different part of the project.
Terminals and Commands:

Terminal 1: python3 leo-link.py
Terminal 2: python3 satellite.py 'Robot'
Terminal 3: python3 satellite.py 'Satellite A'
Terminal 4: python3 satellite.py 'Satellite B'
Terminal 5: python3 satellite.py 'Satellite C'
Terminal 6: python3 satellite.py 'Satellite D'
Terminal 7: python3 satellite.py 'Satellite E'
Terminal 8: python3 satellite.py 'Ground Station'

-> Manual Execution

If you prefer to run the project manually or encounter issues with the script, follow these steps:

Open Multiple Terminals

Open eight separate terminal windows.

Run the Commands in Each Terminal

In each terminal, navigate to the project directory and execute the corresponding command:

Terminal 1: python3 leo-link.py

Terminal 2: python3 satellite.py 'Robot'

Terminal 3: python3 satellite.py 'Satellite A'

Terminal 4: python3 satellite.py 'Satellite B'

Terminal 5: python3 satellite.py 'Satellite C'

Terminal 6: python3 satellite.py 'Satellite D'

Terminal 7: python3 satellite.py 'Satellite E'

Terminal 8: python3 satellite.py 'Ground Station'

Notes
Ground Station Interaction:

In the Ground Station terminal, you will be prompted to select communication channels and enter messages to send.
You can select multiple channels by entering their numbers separated by commas (e.g., 1,2,3).

Port Configuration:

The system uses specific port numbers defined in satellites.json. Ensure that these ports are not blocked by your firewall or used by other applications.

Path and Position Updates:

The leo-link.py script updates satellite positions and computes the shortest communication path every 30 seconds.
Satellite nodes monitor these updates and adjust their routing accordingly.

Simulation of Failures:

In satellite terminals (other than the robot and ground station), you can simulate port failures by entering commands like fail <port>.
