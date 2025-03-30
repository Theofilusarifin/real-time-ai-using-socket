import asyncio
import socketio
import functools

sio = socketio.AsyncClient()
stream_finished_event = asyncio.Event()
input_ready_event = asyncio.Event()
text_queue = asyncio.Queue()


@sio.event
async def connect():
    """Handle connection establishment with the server."""
    print("Connection established")
    stream_finished_event.set()
    input_ready_event.set()


@sio.event
async def gemini_stream(data):
    """Receive and process a chunk of data from the Gemini stream."""
    text_chunk = data.get("data", "")
    if text_chunk:
        await text_queue.put(text_chunk)


@sio.event
async def stream_finished():
    """Indicate that the stream has finished and signal the event."""
    await text_queue.put(None)
    stream_finished_event.set()


@sio.event
async def disconnect():
    """Handle disconnection from the server."""
    print("Disconnected from server")
    await text_queue.put("<<EXIT>>")
    stream_finished_event.set()


async def display_typing_effect(queue):
    """Display typing effect for the text received in the queue."""
    while True:
        chunk = await queue.get()
        if chunk is None:
            queue.task_done()
            await asyncio.sleep(0.1)
            print()
            input_ready_event.set()
            continue
        if chunk == "<<EXIT>>":
            queue.task_done()
            break
        for char in chunk:
            print(char, end="", flush=True)
            await asyncio.sleep(0.005)
        queue.task_done()
    print()


async def main():
    """Main function to manage the client connection and message handling."""
    display_task = asyncio.create_task(display_typing_effect(text_queue))
    try:
        await sio.connect("http://localhost:5000")
        while True:
            await stream_finished_event.wait()
            await input_ready_event.wait()
            stream_finished_event.clear()
            input_ready_event.clear()
            message = await asyncio.get_event_loop().run_in_executor(
                None,
                functools.partial(input, "\nEnter your message (or type 'exit' to quit): ")
            )
            if message.lower() == "exit":
                await text_queue.put("<<EXIT>>")
                break
            await sio.emit("chat_message", {"message": message})
    except Exception as e:
        print(f"\nError: {e}")
        await text_queue.put("<<EXIT>>")
    finally:
        print("\nDisconnecting...")
        await sio.disconnect()
        await display_task
        print("Disconnected.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
