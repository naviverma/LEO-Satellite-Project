import socket
import json
import math
import threading
import signal
import sys
import time
import random
import itertools

# Welcome message
def print_welcome_message():
    print("****************************************")
    print("*     Welcome to the LEO Portal!      *")
    print("* Establishing seamless connections... *")
    print("****************************************\n")
    time.sleep(1)

# Load satellite configuration
with open("config.json", "r") as file:
    config = json.load(file)

# Extract data from the configuration
satellites = config["info"]
robot_info = config["robot_info"]

# Track failed ports for each satellite
failed_ports = {}

# Global shortest path and next_hop mapping
shortest_path = []
next_hop = {}

# Function to calculate Euclidean distance
def euclidean_distance(loc1, loc2):
    return math.sqrt(
        (loc1["latitude"] - loc2["latitude"])**2 +
        (loc1["longitude"] - loc2["longitude"])**2 +
        (loc1["altitude"] - loc2["altitude"])**2
    )

# Function to build the shortest path dynamically
def build_shortest_path():
    satellites = config["info"]
    robot_location = config["robot_info"]["location"]

    # Create a dictionary for distances
    distances = {
        (sat1["name"], sat2["name"]): euclidean_distance(sat1["location"], sat2["location"])
        for sat1, sat2 in itertools.permutations(satellites, 2)
    }

    # print("Pairwise distances:")
    # for (s1, s2), dist in distances.items():
    #     print(f"{s1} -> {s2}: {dist:.2f}")

    # Start with the first satellite (or any arbitrary satellite)
    unvisited = {sat["name"]: sat for sat in satellites}
    current = next(iter(unvisited))  # Arbitrarily pick the first satellite
    path_order = [current]
    del unvisited[current]

    # Greedy approach to find the nearest satellite
    while unvisited:
        next_satellite = min(unvisited, key=lambda sat: distances[(current, sat)])
        path_order.append(next_satellite)
        current = next_satellite
        del unvisited[current]

    # Add the robot as the final destination
    path_order.append("Robot")
    return path_order

# Function to recalculate the shortest path dynamically
def recalculate_shortest_path():
    """Recomputes the shortest path based on updated satellite locations."""
    global shortest_path, next_hop
    shortest_path = build_shortest_path()

    # Update next_hop mapping
    next_hop = {shortest_path[i]: shortest_path[i + 1] for i in range(len(shortest_path) - 1)}
    print(f"Shortest path recalculated: {shortest_path}")

# Simulates dynamic satellite movement
def update_satellite_locations():
    """Simulates dynamic satellite movement by updating their locations."""
    while True:
        for satellite in config["info"]:
            # Increase randomness for more dynamic changes
            satellite["location"]["latitude"] += random.uniform(-50.0, 50.0)
            satellite["location"]["longitude"] += random.uniform(-50.0, 50.0)
            satellite["location"]["altitude"] += random.uniform(-50.0, 50.0)

        # Log updated locations
        # for sat in config["info"]:
        #     print(f"Updated {sat['name']} location: {sat['location']}")

        # print("Satellite locations updated.")
        # Trigger shortest path recalculation
        recalculate_shortest_path()

        # Wait for 30 seconds before the next update
        time.sleep(30)

# UDP Communication
def handle_satellite(satellite):
    ip = satellite["ip"]
    ports = satellite["ports"]
    failed_ports[satellite["name"]] = set()

    for port_info in ports:
        threading.Thread(
            target=handle_port,
            args=(satellite["name"], ip, port_info["port"], port_info["usage"])
        ).start()

def handle_port(satellite_name, ip, port, usage):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.bind((ip, port))
            print(f"{satellite_name} listening on port {port} for {usage}")

            while True:
                data, addr = sock.recvfrom(1024)
                message = data.decode()
                print(f"{satellite_name} ({usage}) received message: {message}")

                # Add a small delay for visual clarity
                time.sleep(0.5)

                # Forward messages based on port usage
                forward_message_with_skip(satellite_name, message, usage)
        except OSError as e:
            print(f"{satellite_name} failed to bind on port {port} ({usage}). Error: {e}")
            failed_ports[satellite_name].add(port)

# Function to forward a message with port skipping
def forward_message_with_skip(current_node, message, usage):
    global next_hop
    next_node = next_hop.get(current_node)
    while next_node:
        if next_node == "Robot":
            # Forward to the robot for the specific usage
            robot_port = next(
                (port["port"] for port in robot_info["ports"] if port["usage"] == usage),
                None
            )
            if robot_port:
                success = send_message(robot_info["ip"], robot_port, message, final_destination=True)
                if success:
                    return
            print(f"Robot ({usage}) port unavailable. Skipping.")
            return

        satellite = next((sat for sat in satellites if sat["name"] == next_node), None)
        if not satellite:
            print(f"Satellite {next_node} not found. Skipping.")
            return

        ip = satellite["ip"]
        ports = {port["usage"]: port["port"] for port in satellite["ports"]}
        target_port = ports.get(usage)

        if target_port and target_port not in failed_ports[next_node]:
            success = send_message(ip, target_port, message)
            if success:
                return  # Stop forwarding once successfully sent
            else:
                print(f"{next_node} {usage} port unavailable. Marking as failed.")
                failed_ports[next_node].add(target_port)
        else:
            print(f"{next_node} {usage} port unavailable. Skipping.")
        next_node = next_hop.get(next_node)  # Move to the next satellite

# Function to send a message to a specific IP and port
def send_message(ip, port, message, final_destination=False):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(message.encode(), (ip, port))
            if not final_destination:
                print(f"Message sent to {ip}:{port}")

            # Add a small delay for visual clarity
            time.sleep(0.5)

            return True
    except Exception as e:
        print(f"Failed to send message to {ip}:{port}. Error: {e}")
        return False

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    print("\nShutting down...")
    import os
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Print welcome message
print_welcome_message()

# Initialize the shortest path
recalculate_shortest_path()

# Start threads for each satellite
threads = []
for satellite in satellites:
    threads.append(threading.Thread(target=handle_satellite, args=(satellite,)))
    threads[-1].start()

# Handle robot communication
def handle_robot():
    robot_ip = robot_info["ip"]

    for port_info in robot_info["ports"]:
        threading.Thread(
            target=robot_port_handler,
            args=(robot_ip, port_info["port"], port_info["usage"])
        ).start()

def robot_port_handler(ip, port, usage):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((ip, port))
        print(f"Robot listening on port {port} for {usage}")

        while True:
            data, addr = sock.recvfrom(1024)
            message = data.decode()
            print(f"Robot ({usage}) received message: {message}")

            # Add a small delay for visual clarity
            time.sleep(0.5)

            print(f"Robot ({usage}) stops forwarding the message: {message}")

robot_thread = threading.Thread(target=handle_robot)
robot_thread.start()

# Start dynamic location updates
location_update_thread = threading.Thread(target=update_satellite_locations, daemon=True)
location_update_thread.start()

# Wait for all threads to finish
for thread in threads:
    thread.join()
robot_thread.join()
