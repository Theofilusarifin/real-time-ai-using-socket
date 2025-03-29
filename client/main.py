import asyncio
import socketio
import functools

sio = socketio.AsyncClient()
stream_finished_event = asyncio.Event()  # Event to signal that a stream is finished
input_ready_event = asyncio.Event()  # Event to signal when input is ready
text_queue = asyncio.Queue()  # Queue for buffering text chunks

@sio.event
async def connect():
    """Handle connection establishment with the server."""
    print('Connection established')
    stream_finished_event.set()  # Allow user input immediately after connecting
    input_ready_event.set()  # Signal that input is ready

@sio.event
async def gemini_stream(data):
    """Handle incoming text chunks from the server."""
    text_chunk = data.get('data', '')  # Extract text chunk from incoming data
    if text_chunk:
        await text_queue.put(text_chunk)

@sio.event
async def stream_finished():
    """Signal the display task to end the current stream output."""
    await text_queue.put(None)  # Indicate end of current message
    stream_finished_event.set()  # Allow main() to accept a new user message

@sio.event
async def disconnect():
    """Handle disconnection from the server."""
    print('Disconnected from server')
    await text_queue.put("<<EXIT>>")  # Indicate exit
    stream_finished_event.set()  # Signal that input is ready

async def display_typing_effect(queue):
    """Display text from the queue with a typing effect."""
    while True:
        chunk = await queue.get()
        if chunk is None:  # End of a current message
            queue.task_done()
            await asyncio.sleep(0.1)  # Delay to ensure output is flushed
            print()  # Move to a new line after flushing
            input_ready_event.set()  # Signal that input is ready
            continue
        if chunk == "<<EXIT>>":
            queue.task_done()
            break
        # Print the entire chunk immediately
        for char in chunk:
            print(char, end='', flush=True)
            await asyncio.sleep(0.005)  # Delay for each character
        queue.task_done()
    print()

async def main():
    """Main function to manage the client lifecycle and user input."""
    display_task = asyncio.create_task(display_typing_effect(text_queue))
    try:
        await sio.connect('http://localhost:5000')
        loop = asyncio.get_running_loop()
        while True:
            await stream_finished_event.wait()  # Wait for the stream to finish
            await input_ready_event.wait()  # Wait for the display to finish
            stream_finished_event.clear()  # Clear the event for the next round
            input_ready_event.clear()  # Clear the input ready event
            message = await loop.run_in_executor(
                None, functools.partial(input, "\nEnter your message (or type 'exit' to quit): ")
            )
            if message.lower() == 'exit':
                await text_queue.put("<<EXIT>>")
                break
            await sio.emit('chat_message', {'message': message})
    except Exception as e:
        print(f"\nError: {e}")
        await text_queue.put("<<EXIT>>")
    finally:
        print("\nDisconnecting...")
        await sio.disconnect()
        await display_task
        print("Disconnected.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
