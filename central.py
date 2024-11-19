import json
import math
import itertools
import random
import time

def haversine_distance(lat1, lon1, alt1, lat2, lon2, alt2):
    # Earth radius in kilometers
    R = 6371.0

    # Convert latitude and longitude from degrees to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Distance over Earth's surface
    surface_distance = R * c

    # Total distance including altitude difference
    altitude_diff = abs(alt1 - alt2) / 1000.0  # Convert meters to kilometers
    total_distance = math.sqrt(surface_distance ** 2 + altitude_diff ** 2)

    return total_distance

def load_data():
    with open('satellites.json', 'r') as f:
        data = json.load(f)
    satellites = data['info']
    robot = data['robot_info']
    return satellites, robot

def compute_total_distance(path, positions):
    total_distance = 0.0
    for i in range(len(path) -1):
        node1 = path[i]
        node2 = path[i +1]
        lat1, lon1, alt1 = positions[node1]
        lat2, lon2, alt2 = positions[node2]
        distance = haversine_distance(lat1, lon1, alt1, lat2, lon2, alt2)
        total_distance += distance
    return total_distance

def update_positions(satellites):
    # Randomly update positions
    for sat in satellites:
        # Randomly adjust latitude and longitude by up to +/- 0.1 degrees
        sat['location']['latitude'] += random.uniform(-20, 20)
        sat['location']['longitude'] += random.uniform(-20, 20)
        # Ensure latitude and longitude remain within valid bounds
        sat['location']['latitude'] = max(-90, min(90, sat['location']['latitude']))
        sat['location']['longitude'] = ((sat['location']['longitude'] + 180) % 360) - 180
    return satellites

def main():
    satellites, robot = load_data()

    while True:
        # Update positions
        satellites = update_positions(satellites)

        # Positions of satellites and robot
        positions = {}
        for sat in satellites:
            positions[sat['name']] = (
                sat['location']['latitude'],
                sat['location']['longitude'],
                sat['location']['altitude']
            )
        positions['Robot'] = (
            robot['location']['latitude'],
            robot['location']['longitude'],
            robot['location']['altitude']
        )

        # Save updated positions to 'positions.json'
        positions_data = {'positions': positions}
        with open('positions.json', 'w') as f:
            json.dump(positions_data, f)

        # Identify ground stations
        ground_stations = [sat for sat in satellites if "Ground Station" in sat['name']]
        if not ground_stations:
            print("No ground stations found.")
            return

        # Elect the ground station with the highest capability
        elected_ground_station = max(ground_stations, key=lambda x: len(x['ports']))

        print(f"Elected Ground Station: {elected_ground_station['name']} with {len(elected_ground_station['ports'])} channels.")

        start_node = elected_ground_station['name']
        end_node = 'Robot'

        # List of satellites excluding the ground stations
        satellite_names = [sat['name'] for sat in satellites if "Ground Station" not in sat['name']]

        # Generate all permutations of the satellites
        permutations = itertools.permutations(satellite_names)

        min_distance = float('inf')
        shortest_path = None

        # Evaluate each permutation
        for perm in permutations:
            # Construct the path
            path = [start_node] + list(perm) + [end_node]
            total_distance = compute_total_distance(path, positions)
            if total_distance < min_distance:
                min_distance = total_distance
                shortest_path = path

        print("Shortest path from {} to {} including all satellites:".format(start_node, end_node))
        print(" -> ".join(shortest_path))
        print("Total distance: {:.2f} km".format(min_distance))

        # Save the path to a JSON file
        with open('path.json', 'w') as f:
            json.dump({'path': shortest_path}, f)

        # Sleep for 30 seconds before recomputing
        time.sleep(30)

if __name__ == "__main__":
    main()

