import asyncio
import websockets
import pygame
import socket
import threading
import pickle
import time

# Initialize Pygame
pygame.init()
window = pygame.display.set_mode((500, 500))
pygame.display.set_caption("Remote Planet Exploration")
clock = pygame.time.Clock()

# Character properties
x, y = 250, 250
speed = 20

# Custom Pygame events
MOVE_FORWARD_EVENT = pygame.USEREVENT + 1
MOVE_BACKWARD_EVENT = pygame.USEREVENT + 2
TURN_LEFT_EVENT = pygame.USEREVENT + 3
TURN_RIGHT_EVENT = pygame.USEREVENT + 4

# Function to move character based on event with boundary checks
def move_character(event):
    global x, y
    if event.type == MOVE_FORWARD_EVENT and y > 0:
        y -= speed
        print("Moving Forward")
    elif event.type == MOVE_BACKWARD_EVENT and y < 480:
        y += speed
        print("Moving Backward")
    elif event.type == TURN_LEFT_EVENT and x > 0:
        x -= speed
        print("Turning Left")
    elif event.type == TURN_RIGHT_EVENT and x < 480:
        x += speed
        print("Turning Right")

# WebSocket handler: Receives commands from HTML and forwards to the base node
async def handler(websocket):
    async for message in websocket:
        message = message.strip()
        print(f"Received Command from HTML: {message}")
        
        # Forward the command to the Base Node on port 8000
        forward_to_base_node(message)

# Forward command to the Base Node
def forward_to_base_node(command):
    base_ip = "127.0.0.1"
    base_port = 8000
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((base_ip, base_port))
            s.sendall(command.encode())
            print(f"Forwarded Command to Base Node: {command}")
    except Exception as e:
        print(f"Error forwarding command to Base Node: {e}")

# WebSocket server to listen for HTML commands
async def start_websocket_server():
    async with websockets.serve(handler, "0.0.0.0", 7998):
        print("WebSocket Server started on ws://localhost:7998")
        await asyncio.Future()  # Keep the server running


def pygame_listener():
    time.sleep(2)
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.bind(("127.0.0.1", 9000))  # Port for satellite node
                server_socket.listen(5)
                print("Pygame Listener: Listening on port 9000")
                while True:
                    conn, addr = server_socket.accept()
                    print(f"HII - Connection accepted from {conn}")
                    with conn:
                        conn.settimeout(5)
                        try:
                            print("HIOOO")
                            data = conn.recv(1024)
                            
                            if not data:
                                break

                            # Attempt to deserialize using pickle
                            deserialized_data = pickle.loads(data)
                            print(f"Pygame Listener: Received Deserialized Data: {deserialized_data}")

                            # Extract the command
                            command = deserialized_data.get("data")
                            if command:
                                print(f"Pygame Listener: Command to Process: {command}")

                                # Post Pygame events based on the command
                                if command == "MOVE_FORWARD":
                                    pygame.event.post(pygame.event.Event(MOVE_FORWARD_EVENT))
                                elif command == "MOVE_BACKWARD":
                                    pygame.event.post(pygame.event.Event(MOVE_BACKWARD_EVENT))
                                elif command == "TURN_LEFT":
                                    pygame.event.post(pygame.event.Event(TURN_LEFT_EVENT))
                                elif command == "TURN_RIGHT":
                                    pygame.event.post(pygame.event.Event(TURN_RIGHT_EVENT))
                        except Exception as e:
                            # print(f"Pygame Listener Error while processing data: {e}")
                            print("")
        except Exception as e:
            print(f"Pygame Listener Error: {e}. Restarting listener...")


# Main game loop
async def game_loop():
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            move_character(event)

        # Fill background and draw character
        window.fill((0, 0, 0))
        pygame.draw.rect(window, (0, 255, 0), (x, y, 20, 20))
        pygame.display.flip()
        clock.tick(30)

        await asyncio.sleep(0)

# Main function to run the WebSocket server, game loop, and Pygame listener
async def main():
    # Start WebSocket server and game loop concurrently
    threading.Thread(target=pygame_listener, daemon=True).start()  # Start Pygame listener in a separate thread
    await asyncio.gather(start_websocket_server(), game_loop())

if __name__ == "__main__":
    asyncio.run(main())
