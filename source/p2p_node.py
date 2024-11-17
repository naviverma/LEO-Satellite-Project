import socket
import threading
import time
import json
import argparse
import numpy as np
from pickle import dumps, loads

class SatelliteNode:
    def __init__(self, config, base, destination, next_neighbour):
        self.server_addr = (config['ip'], config['port'])
        self.location = np.array([
            config['location']['latitude'],
            config['location']['longitude'],
            config['location']['altitude']
        ])
        self.peers = config['peers']
        self.base = base
        self.destination = destination
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_conn = None
        self.next_neighbor = next_neighbour
        self.prev_neighbor = None

        # Bind and listen as a server
        self.server_socket.bind(self.server_addr)
        self.server_socket.listen(5)
        print(f"[INFO] Listening on {self.server_addr}")

        # Find the two closest neighbors
        # self.find_closest_neighbors()

        # Start threads for server and client functions
        threading.Thread(target=self.accept_connections).start()
        threading.Thread(target=self.connect_to_next_neighbor).start()

    def calculate_distance(self, loc1, loc2):
        return np.linalg.norm(np.array(loc1) - np.array(loc2))

    def accept_connections(self):
        while True:
            conn, addr = self.server_socket.accept()
            print(f"[INFO] Accepted connection from {addr}")
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()

    def connect_to_next_neighbor(self):
        while self.next_neighbor:
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((self.next_neighbor['ip'], self.next_neighbor['port']))
                self.client_conn = client_socket
                print(f"[INFO] Connected to next neighbor {self.next_neighbor['ip']}:{self.next_neighbor['port']}")
                break
            except Exception as e:
                print(f"[ERROR] Could not connect to next neighbor - {e}")
                time.sleep(5)

    def handle_client(self, conn, addr):
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                message = loads(data)
                print(f"[INFO] Received message from {addr}: {message}")

                # Relay message if not the final destination
                # if message['dest'] != self.server_addr:
                self.relay_message(message)
                # else:
                #     print(f"[INFO] Message reached destination: {message}")
                #     self.handle_destination(message)
            except Exception as e:
                print(f"[ERROR] Error handling client {addr}: {e}")
                break
        conn.close()

    def relay_message(self, message):
        time.sleep(3)
        try:
            # Exclude the sender from neighbor selection
            # last_sender = message['source']
            # self.find_closest_neighbors(last_sender=last_sender)

            if self.next_neighbor:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                    client_socket.connect((self.next_neighbor['ip'], self.next_neighbor['port']))
                    client_socket.send(dumps(message))
                    print(f"[INFO] Relayed message to {self.next_neighbor['ip']}:{self.next_neighbor['port']}")
            else:
                print(f"[WARNING] No valid neighbor found to relay message from {self.server_addr}")
        except Exception as e:
            print(f"[ERROR] Failed to relay message from {self.server_addr}: {e}")

    def send_message(self, dest, data):
        message = {
            "source": self.server_addr,
            "dest": dest,
            "data": data
        }
        self.relay_message(message)

    
    def handle_destination(self, message):
        # Handle the final message at the destination (e.g., send to Pygame)
        print(f"[INFO] Processing final message: {message['data']}")

class BaseNode:
    def __init__(self, base_config, satellite_info):
        self.server_addr = (base_config['ip'], base_config['port'])
        self.location = np.array([
            base_config['latitude'],
            base_config['longitude'],
            base_config['altitude']
        ])
        self.satellite_info = satellite_info
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(self.server_addr)
        self.server_socket.listen(5)
        print(f"[INFO] Base node listening at {self.server_addr}")

        # Start thread to accept incoming connections
        threading.Thread(target=self.accept_connections).start()

    def accept_connections(self):
        while True:
            conn, addr = self.server_socket.accept()
            print(f"[INFO] Base received connection from {addr}")
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()

    def handle_client(self, conn, addr):
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"[INFO] Base received raw data: {data}")
                message = data.decode('utf-8').strip()
                # message = loads(data)
                print(f"[INFO] Base received message: {message}")
                self.relay_message(message, closest_satellite)
            except Exception as e:
                print(f"[ERROR] Base error handling client: {e}")
                break
        conn.close()

    def find_closest_satellite(self):
        distances = [
            (sat, np.linalg.norm(self.location -
                                 np.array([sat['location']['latitude'], sat['location']['longitude'], sat['location']['altitude']])))
            for sat in self.satellite_info
        ]
        distances.sort(key=lambda x: x[1])
        closest_satellite = distances[0][0]
        print(f"[INFO] Closest satellite to base: {closest_satellite['ip']}:{closest_satellite['port']}")
        return closest_satellite

    def send_message(self, data, closest_satellite):
        # closest_satellite = self.find_closest_satellite()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            try:
                client_socket.connect((closest_satellite['ip'], closest_satellite['port']))
                message = {
                    "source": self.server_addr,
                    "dest": (self.server_addr[0], self.server_addr[1]),
                    "data": data
                }
                client_socket.send(dumps(message))
                print(f"[INFO] Base sent message to {closest_satellite['ip']}:{closest_satellite['port']}")
            except Exception as e:
                print(f"[ERROR] Base failed to send message: {e}")
    
    def relay_message(self, data, closest_satellite):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            try:
                client_socket.connect((closest_satellite['ip'], closest_satellite['port']))
                relay_message = {
                    "source": self.server_addr,
                    "dest": (closest_satellite['ip'], closest_satellite['port']),
                    "data": data
                }
                client_socket.send(dumps(relay_message))
                print(f"[INFO] Base relayed message to {closest_satellite['ip']}:{closest_satellite['port']}")
            except Exception as e:
                print(f"[ERROR] Base failed to relay message: {e}")

# Function to calculate Euclidean distance
def calculate_distance(location1, location2):
    loc1 = np.array(location1)
    loc2 = np.array(location2)
    return np.linalg.norm(loc1 - loc2)

# Function to find the closest neighbor
def find_closest_node(current_node, nodes, visited):
    current_location = [
        current_node["latitude"],
        current_node["longitude"],
        current_node["altitude"]
    ]
    min_distance = float("inf")
    closest_node = None

    for node in nodes:
        if node in visited:
            continue
        node_location = [
            node["location"]["latitude"],
            node["location"]["longitude"],
            node["location"]["altitude"]
        ]
        distance = calculate_distance(current_location, node_location)
        if distance < min_distance:
            min_distance = distance
            closest_node = node

    return closest_node

# Build the linear path
def build_path(config):
    path = []
    visited = []

    # Add base node to the path
    base = {
        "ip": config["base"]["ip"],
        "port": config["base"]["port"],
        "location": {
            "latitude": config["base"]["latitude"],
            "longitude": config["base"]["longitude"],
            "altitude": config["base"]["altitude"]
        }
    }
    path.append(base)
    visited.append(base)

    # Start with the base node
    current_node = base
    nodes = config["info"]

    # Find and append the closest nodes
    while len(visited) <= len(nodes):
        closest_node = find_closest_node(current_node["location"], nodes, visited)
        if not closest_node:
            break
        path.append(closest_node)
        visited.append(closest_node)
        current_node = closest_node

    # Add destination node to the path
    destination = {
        "ip": config["destination"]["ip"],
        "port": config["destination"]["port"],
        "location": {
            "latitude": config["destination"]["latitude"],
            "longitude": config["destination"]["longitude"],
            "altitude": config["destination"]["altitude"]
        }
    }
    path.append(destination)

    return path
    
if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run a satellite or base node.")
    parser.add_argument('--server-ip', required=True, help="IP address of the node")
    parser.add_argument('--server-port', required=True, type=int, help="Port number of the node")
    parser.add_argument('--node-type', required=True, choices=['base', 'satellite'], help="Node type (base or satellite)")
    args = parser.parse_args()

    server_ip = args.server_ip
    server_port = args.server_port

    # Load configuration from JSON file
    with open('config.json') as f:
        config_data = json.load(f)

    # Generate the path
    path = build_path(config_data)
    index = 0
    for item in path:
        print(item)
        index = index + 1
        if item.get('port') == server_port:
            break
    if server_port!=9000:
        next_neighbour = path[index]
    print("Next", next_neighbour)
    base_config = config_data['base']
    destination_config = config_data['destination']

    if args.node_type == "base":
        # Initialize the base node
        base = BaseNode(base_config, config_data['info'])
        closest_satellite = base.find_closest_satellite()
        # Interactive loop to send messages
        while True:
            msg = input("Enter a message to send (or 'exit' to quit): ")
            if msg.lower() == 'exit':
                break
            base.send_message(msg, closest_satellite)

    else:
        # Find the configuration for this satellite node
        my_config = None
        for node in config_data['info']:
            if node['ip'] == server_ip and node['port'] == server_port:
                my_config = node
                break
        print(my_config)
        if not my_config:
            print(f"[ERROR] Configuration not found for {server_ip}:{server_port}.")
            exit(1)

        # Add the list of peers (excluding the current node)
        my_config['peers'] = [peer for peer in config_data['info'] if peer['ip'] != server_ip or peer['port'] != server_port]

        node = SatelliteNode(my_config, base_config, destination_config, next_neighbour)
        print(f"[INFO] Satellite node started at {server_ip}:{server_port}")