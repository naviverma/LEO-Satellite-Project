import socket
import threading
import time
import json
import argparse
import numpy as np
from pickle import dumps, loads

class SatelliteNode:
    def __init__(self, config):
        self.server_addr = (config['ip'], config['port'])
        self.location = np.array([
            config['location']['latitude'],
            config['location']['longitude'],
            config['location']['altitude']
        ])
        self.peers = config['peers']
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_conn = None
        self.next_neighbor = None
        self.prev_neighbor = None  # Initialize prev_neighbor to avoid AttributeError

        # Bind and listen as a server
        self.server_socket.bind(self.server_addr)
        self.server_socket.listen(5)
        print(f"[INFO] Listening on {self.server_addr}")

        # Find the two closest neighbors
        self.find_closest_neighbors()

        # Start threads for server and client functions
        threading.Thread(target=self.accept_connections).start()
        threading.Thread(target=self.connect_to_next_neighbor).start()

    def calculate_distance(self, loc1, loc2):
        return np.linalg.norm(np.array(loc1) - np.array(loc2))

    def find_closest_neighbors(self):
        distances = []
        for peer in self.peers:
            peer_location = np.array([
                peer['location']['latitude'],
                peer['location']['longitude'],
                peer['location']['altitude']
            ])
            dist = self.calculate_distance(self.location, peer_location)
            distances.append((peer, dist))

        # Sort by distance and select the closest neighbors
        distances.sort(key=lambda x: x[1])
        
        if distances:
            # Select the closest peer as the next neighbor
            self.next_neighbor = distances[0][0]
            
            # Avoid circular loops: Make sure that the selected next neighbor
            # doesn't assign the current node as its next neighbor.
            if len(distances) > 1:
                for peer in distances[1:]:
                    if peer[0] != self.next_neighbor:
                        self.prev_neighbor = peer[0]
                        break

        print(f"[INFO] Next Neighbor: {self.next_neighbor}")
        print(f"[INFO] Previous Neighbor: {self.prev_neighbor}")

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

                # If message is intended for this node, deliver it
                if message['dest'] == self.server_addr:
                    print(f"[INFO] Message reached destination: {message}")
                    break  # Exit after successfully delivering the message

                # Relay message to the next neighbor (if it's not the destination)
                if self.next_neighbor:
                    self.relay_message(message)
                else:
                    print("[INFO] No next neighbor to forward message.")
                    break
            except Exception as e:
                print(f"[ERROR] Error handling client {addr}: {e}")
                break
        conn.close()

    def relay_message(self, message):
        try:
            if self.client_conn:
                self.client_conn.send(dumps(message))
                print(f"[INFO] Relayed message to {self.next_neighbor['ip']}:{self.next_neighbor['port']}")
        except Exception as e:
            print(f"[ERROR] Failed to relay message: {e}")

    def send_message(self, dest, data):
        message = {
            "source": self.server_addr,
            "dest": dest,
            "data": data
        }
        self.relay_message(message)

if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run a satellite node with specified IP and port.")
    parser.add_argument('--server-ip', required=True, help="IP address of the satellite node")
    parser.add_argument('--server-port', required=True, type=int, help="Port number of the satellite node")
    args = parser.parse_args()

    server_ip = args.server_ip
    server_port = args.server_port

    # Load configuration from JSON file
    with open('config2.json') as f:
        config_data = json.load(f)

    # Find the configuration for this node
    my_config = None
    for node in config_data['info']:
        if node['ip'] == server_ip and node['port'] == server_port:
            my_config = node
            break

    if not my_config:
        print(f"[ERROR] Configuration not found for {server_ip}:{server_port}.")
        exit(1)

    # Add the list of peers (excluding the current node)
    my_config['peers'] = [peer for peer in config_data['info'] if peer['ip'] != server_ip or peer['port'] != server_port]

    node = SatelliteNode(my_config)
    print(f"[INFO] Node started at {server_ip}:{server_port}")

    # Simple user input loop for sending messages
    while True:
        msg = input("Enter a message to send (or 'exit' to quit): ")
        if msg.lower() == 'exit':
            break
        dest_ip = input("Enter destination IP: ")
        dest_port = int(input("Enter destination Port: "))
        node.send_message((dest_ip, dest_port), msg)

    print("[INFO] Shutting down.")
