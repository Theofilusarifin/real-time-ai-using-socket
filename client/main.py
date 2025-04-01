import asyncio
import socketio
import os
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts.utils import run_in_terminal
from dotenv import load_dotenv

load_dotenv()

sio = socketio.AsyncClient()

stream_finished_event = asyncio.Event()
input_ready_event = asyncio.Event()

gemini_queue = asyncio.Queue()


@sio.event
async def connect():
    """Handles the connect event."""
    run_in_terminal(lambda: print("Connection established"))
    stream_finished_event.set()
    input_ready_event.set()


@sio.event
async def disconnect():
    """Handles the disconnect event."""
    run_in_terminal(lambda: print("Disconnected from server"))
    await gemini_queue.put("<<EXIT>>")
    stream_finished_event.set()
    input_ready_event.set()


@sio.event
async def broadcast_message(data):
    """Handles the broadcast_message event."""
    sender = data.get("user", "Unknown")
    message = data.get("message", "")
    run_in_terminal(lambda: print(f"\n💬 {sender}: {message}"))


@sio.event
async def gemini_stream(data):
    """Handles the gemini_stream event."""
    text_chunk = data.get("data", "")
    if text_chunk:
        await gemini_queue.put(text_chunk)


@sio.event
async def stream_finished():
    """Handles the stream_finished event."""
    await gemini_queue.put(None)
    stream_finished_event.set()


async def process_gemini_queue():
    """Processes Gemini text chunks from the queue."""
    while True:
        chunk = await gemini_queue.get()
        if chunk == "<<EXIT>>":
            gemini_queue.task_done()
            break
        if chunk is None:
            run_in_terminal(lambda: print())
            gemini_queue.task_done()
            input_ready_event.set()
            continue
        run_in_terminal(lambda: print(chunk, end="", flush=True))
        gemini_queue.task_done()


async def main():
    """Main function to run the client."""
    session = PromptSession()
    username = await session.prompt_async("Enter your username: ")

    app_host = os.getenv("APP_HOST", "localhost")
    app_port = os.getenv("APP_PORT", "5000")

    await sio.connect(f"http://{app_host}:{app_port}", auth={"username": username})
    run_in_terminal(lambda: print(f"\nYou are now logged in as: {username}"))

    # Start background task for Gemini streaming
    asyncio.create_task(process_gemini_queue())

    with patch_stdout():
        while True:
            # Wait for any current Gemini stream to finish
            await stream_finished_event.wait()
            await input_ready_event.wait()
            stream_finished_event.clear()
            input_ready_event.clear()

            # Prompt for a new message
            message = await session.prompt_async(f"\n💬 {username}: ")
            if message.lower() == "exit":
                await gemini_queue.put("<<EXIT>>")
                break
            await sio.emit("chat_message", {"message": message})
            # If no Gemini is triggered, immediately release input
            if "@gemini" not in message.lower():
                stream_finished_event.set()
                input_ready_event.set()
    await sio.disconnect()
    run_in_terminal(lambda: print("Disconnected from server"))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        run_in_terminal(lambda: print("\nExiting..."))
