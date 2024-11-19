import json
import sys
import socket
import threading
import time
import math
import os  # For file modification times
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def load_data():
    with open('satellites.json', 'r') as f:
        data = json.load(f)
    satellites = data['info']
    robot = data['robot_info']
    return satellites, robot

def load_path():
    with open('path.json', 'r') as f:
        data = json.load(f)
    return data['path']

def get_satellite_info(satellites, robot, name):
    if name == 'Robot':
        return robot
    for sat in satellites:
        if sat['name'] == name:
            return sat
    return None

def get_port_by_usage(sat_info, usage):
    for port_info in sat_info['ports']:
        if port_info['usage'] == usage:
            return port_info['port']
    return None

def haversine_distance(lat1, lon1, alt1, lat2, lon2, alt2):
    # Existing code...
    # Earth radius in kilometers
    R = 6371.0

    # Convert latitude and longitude from degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Distance over Earth's surface
    surface_distance = R * c

    # Total distance including altitude difference
    altitude_diff = abs(alt1 - alt2) / 1000.0  # Convert meters to kilometers
    total_distance = math.sqrt(surface_distance ** 2 + altitude_diff ** 2)

    return total_distance

def derive_key(password):
    # Existing code...
    salt = b'static_salt_value'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # AES-256
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(password.encode())
    return key

def encrypt_message(key, plaintext):
    # Existing code...
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()

    iv = os.urandom(16)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    return iv + ciphertext

def decrypt_message(key, ciphertext):
    # Existing code...
    iv = ciphertext[:16]
    actual_ciphertext = ciphertext[16:]

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(actual_ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

    return plaintext

class SatelliteNode:
    def __init__(self, name, sat_info, prev_sat_info, next_sat_infos, positions, key, satellites, robot):
        self.name = name
        self.sat_info = sat_info
        self.prev_sat_info = prev_sat_info
        self.next_sat_infos = next_sat_infos
        self.positions = positions
        self.key = key

        self.satellites = satellites
        self.robot = robot

        self.ip = sat_info['ip']

        self.prev_ip = None
        self.prev_port = None
        if prev_sat_info:
            self.prev_ip = prev_sat_info['ip']

        self.server_sockets = {}
        self.failed_ports = set()  # Keep track of failed ports

        self.path_last_modified = None
        self.positions_last_modified = None
        self.lock = threading.Lock()

        # Start the monitor thread
        threading.Thread(target=self.monitor_updates, daemon=True).start()

    def monitor_updates(self):
        while True:
            time.sleep(5)  # Check every 5 seconds

            try:
                path_mtime = os.path.getmtime('path.json')
                if self.path_last_modified is None or path_mtime > self.path_last_modified:
                    self.update_path()
                    self.path_last_modified = path_mtime

                positions_mtime = os.path.getmtime('positions.json')
                if self.positions_last_modified is None or positions_mtime > self.positions_last_modified:
                    self.update_positions()
                    self.positions_last_modified = positions_mtime
            except Exception as e:
                print(f"{self.name}: Error monitoring updates: {e}")

    def update_path(self):
        with self.lock:
            path = load_path()
            try:
                idx = path.index(self.name)
            except ValueError:
                print(f"{self.name} is not in the updated communication path.")
                return

            # Update prev_sat_info
            if idx > 0:
                prev_name = path[idx - 1]
                self.prev_sat_info = get_satellite_info(self.satellites, self.robot, prev_name)
            else:
                self.prev_sat_info = None

            # Update next_sat_infos
            self.next_sat_infos = []
            for next_name in path[idx + 1:]:
                next_sat_info = get_satellite_info(self.satellites, self.robot, next_name)
                if next_sat_info:
                    self.next_sat_infos.append(next_sat_info)

            print(f"{self.name}: Updated path information.")

    def update_positions(self):
        with self.lock:
            # Load updated positions
            with open('positions.json', 'r') as f:
                positions_data = json.load(f)
            self.positions = positions_data['positions']
            print(f"{self.name}: Updated positions.")

    # Modify methods to use self.lock where necessary
    def start_servers(self):
        # Existing code...
        ports = [port_info['port'] for port_info in self.sat_info['ports']]
        for port in ports:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind((self.ip, port))
            server_socket.listen(5)
            self.server_sockets[port] = server_socket
            print(f"{self.name} listening on {self.ip}:{port}")
            # Accept connections in a separate thread
            threading.Thread(target=self.accept_connections, args=(server_socket, port)).start()

    def accept_connections(self, server_socket, port):
        while True:
            try:
                conn, addr = server_socket.accept()
                print(f"{self.name} accepted connection on port {port} from {addr}")
                threading.Thread(target=self.handle_connection, args=(conn, port)).start()
            except OSError:
                # Socket has been closed, exit the loop
                print(f"{self.name}: Stopped listening on port {port}")
                break

    def handle_connection(self, conn, port):
        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    break

                # Decrypt the message
                plaintext = decrypt_message(self.key, data)
                message = plaintext.decode()

                print(f"{self.name} received message on port {port}: {message}")

                # Send the message to the next available node on the same channel
                self.send_to_next_available(plaintext, port)
            except ConnectionResetError:
                break
            except Exception as e:
                print(f"{self.name}: Error decrypting message: {e}")
                break
        conn.close()

    def send_to_next_available(self, data, port):
        with self.lock:
            # Find the usage corresponding to the port
            usage = None
            for port_info in self.sat_info['ports']:
                if port_info['port'] == port:
                    usage = port_info['usage']
                    break
            if not usage:
                print(f"{self.name} could not find usage for port {port}")
                return

            ciphertext = encrypt_message(self.key, data)

            # Try to connect to the next available satellite in the path using the same usage
            for next_sat_info in self.next_sat_infos:
                next_ip = next_sat_info['ip']
                next_port = get_port_by_usage(next_sat_info, usage)

                try:
                    # Calculate the distance and delay
                    current_pos = self.positions[self.name]
                    next_pos = self.positions[next_sat_info['name']]
                    distance = haversine_distance(
                        current_pos[0], current_pos[1], current_pos[2],
                        next_pos[0], next_pos[1], next_pos[2]
                    )
                    SPEED_OF_LIGHT = 299792.458  # km/s
                    delay_ms = (distance / SPEED_OF_LIGHT) * 1000  # in milliseconds

                    # Print the handover message
                    print(f"Handover initiated: {self.name} ({port}) -> {next_sat_info['name']} ({next_port})")
                    print(f"Distance between satellites: {distance:.2f} km")
                    print(f"Calculated delay: {delay_ms:.4f} ms")

                    # Simulate the delay
                    time.sleep(delay_ms / 10)  # Convert ms to seconds

                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(5)
                    client_socket.connect((next_ip, next_port))
                    client_socket.sendall(ciphertext)
                    print(f"{self.name} sent encrypted message to {next_sat_info['name']} at {next_ip}:{next_port}")
                    client_socket.close()
                    return
                except (ConnectionRefusedError, socket.timeout):
                    print(f"{self.name} could not connect to {next_sat_info['name']} at {next_ip}:{next_port}")
                    continue  # Try the next satellite
            # If all connections fail, print an error
            if (self.name!='Robot'):
                print(f"{self.name} could not send message: All subsequent satellites are unavailable.")

    def fail_port(self, port):
        with self.lock:
            if port in self.server_sockets:
                self.server_sockets[port].close()
                del self.server_sockets[port]
                self.failed_ports.add(port)
                print(f"{self.name}: Port {port} has been failed.")
            else:
                print(f"{self.name}: Port {port} is not active or already failed.")

    def command_listener(self):
        while True:
            cmd = input(f"{self.name}: Enter command ('fail <port>' to fail a port): ")
            if cmd.startswith('fail'):
                try:
                    _, port_str = cmd.strip().split()
                    port = int(port_str)
                    self.fail_port(port)
                except ValueError:
                    print(f"{self.name}: Invalid command format. Use 'fail <port>'.")
            else:
                print(f"{self.name}: Unknown command.")

    def run(self):
        self.start_servers()
        if not self.prev_sat_info:
            # First node (Ground Station)
            print(f"{self.name} is the first node. Waiting for user input to send messages.")
            while True:
                print("Available channels:")
                for idx, port_info in enumerate(self.sat_info['ports'], start=1):
                    print(f"Channel {idx}: {port_info['usage']} (Port {port_info['port']})")
                
                # Prompt the user to select multiple channels
                channels_input = input("Select channel numbers to use for communication (e.g., 1,3,4) or 'exit' to quit: ")
                if channels_input.lower() == 'exit':
                    sys.exit(0)
                channel_numbers = [int(num.strip()) for num in channels_input.split(',') if num.strip().isdigit()]
                selected_ports_info = []
                for channel_number in channel_numbers:
                    if 1 <= channel_number <= len(self.sat_info['ports']):
                        selected_ports_info.append(self.sat_info['ports'][channel_number - 1])
                    else:
                        print(f"Invalid channel number: {channel_number}")
                
                if not selected_ports_info:
                    print("No valid channels selected.")
                    continue  # Go back to the start of the loop
                
                # Collect messages for each selected channel
                messages = {}
                for port_info in selected_ports_info:
                    msg = input(f"Enter message to send on channel {port_info['usage']} (Port {port_info['port']}) or 'skip' to skip: ")
                    if msg.lower() == 'exit':
                        sys.exit(0)
                    elif msg.lower() == 'skip':
                        continue  # Skip this channel
                    messages[port_info['port']] = msg.encode()
                
                # Send messages over selected channels simultaneously
                if not messages:
                    print("No messages to send.")
                    continue  # Go back to the start of the loop
                threads = []
                for port_info in selected_ports_info:
                    if port_info['port'] in messages:
                        data = messages[port_info['port']]
                        t = threading.Thread(target=self.send_to_next_available, args=(data, port_info['port']))
                        t.start()
                        threads.append(t)
                
                # Wait for all threads to finish
                for t in threads:
                    t.join()
        elif self.name == 'Robot':
            # Robot
            threading.Event().wait()
        else:
            # Other satellites
            threading.Thread(target=self.command_listener).start()
            threading.Event().wait()

def main():
    satellites, robot = load_data()
    path = load_path()

    # Load positions from 'positions.json'
    with open('positions.json', 'r') as f:
        positions_data = json.load(f)
    positions = positions_data['positions']

    if len(sys.argv) < 2:
        print("Usage: python satellite.py <Node Name>")
        sys.exit(1)

    input_name = sys.argv[1]

    # Check if input_name is 'Ground Station'
    if input_name == "Ground Station":
        # Read the first node from path.json
        start_node = path[0]
        if "Ground Station" in start_node:
            name = start_node  # Use the actual ground station name
            print(f"Using elected ground station: {name}")
        else:
            print("Error: No ground station found in the communication path.")
            sys.exit(1)
    else:
        name = input_name

    sat_info = get_satellite_info(satellites, robot, name)
    if not sat_info:
        print(f"{name} not found")
        sys.exit(1)

    try:
        idx = path.index(name)
    except ValueError:
        print(f"{name} is not in the communication path.")
        sys.exit(1)

    prev_sat_info = None
    if idx > 0:
        prev_name = path[idx - 1]
        prev_sat_info = get_satellite_info(satellites, robot, prev_name)

    # Get the list of next satellites in the path
    next_sat_infos = []
    for next_name in path[idx + 1:]:
        next_sat_info = get_satellite_info(satellites, robot, next_name)
        if next_sat_info:
            next_sat_infos.append(next_sat_info)

    # Derive the key
    passphrase = 'my_secure_passphrase'
    key = derive_key(passphrase)

    node = SatelliteNode(name, sat_info, prev_sat_info, next_sat_infos, positions, key, satellites, robot)
    node.run()

if __name__ == "__main__":
    main()
