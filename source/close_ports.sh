#!/bin/bash

# Define the list of ports used by the P2P nodes
PORTS=("7998" "8000" "8765" "8766" "8767" "8768" "9000")

echo "Searching for processes using the specified ports..."

# Loop through each port and kill the process using it
for PORT in "${PORTS[@]}"; do
    # Find the process ID (PID) using the port
    PID=$(lsof -t -i :$PORT)

    if [ -z "$PID" ]; then
        echo "No process found using port $PORT."
    else
        echo "Killing process $PID using port $PORT..."
        kill -9 $PID
        echo "Closed port $PORT."
    fi
done

echo "All specified ports have been closed."
