import asyncio
import websockets
import pygame

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

# WebSocket handler
async def handler(websocket, path):
    async for message in websocket:
        message = message.strip()
        print(f"Received Command: {message}")
        if message == "MOVE_FORWARD":
            pygame.event.post(pygame.event.Event(MOVE_FORWARD_EVENT))
        elif message == "MOVE_BACKWARD":
            pygame.event.post(pygame.event.Event(MOVE_BACKWARD_EVENT))
        elif message == "TURN_LEFT":
            pygame.event.post(pygame.event.Event(TURN_LEFT_EVENT))
        elif message == "TURN_RIGHT":
            pygame.event.post(pygame.event.Event(TURN_RIGHT_EVENT))

# Start WebSocket server
async def start_server():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("WebSocket Server started on ws://localhost:8765")
        await asyncio.Future()  # Keep the server running

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

# Main function to run both server and game loop
async def main():
    await asyncio.gather(start_server(), game_loop())

if __name__ == "__main__":
    asyncio.run(main())
