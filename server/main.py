from aiohttp import web
import socketio
import os
import google.generativeai as genai
from dotenv import load_dotenv
import asyncio  # Keep asyncio

load_dotenv()

sio = socketio.AsyncServer(cors_allowed_origins="*")
app = web.Application()
sio.attach(app)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("No GOOGLE_API_KEY found in .env")

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
except Exception as e:
    print("[Server] Gemini API initialization error:", str(e))  # Server-specific log
    model = None


@sio.event
async def connect(sid, environ):
    print(f"[{sid}] : Connected")  # Log connection


@sio.event
async def chat_message(sid, data):
    print(f"[{sid}] : Server received message: {data}")  # Log received message
    user_message = data.get("message", "")

    if user_message:
        try:
            print(f"[{sid}] : Sending message to Gemini: {user_message}")  # Log message sent to Gemini
            if model:
                response = model.generate_content(user_message, stream=True) # Stream=True
                # Send chunks as they arrive
                for chunk in response: # Standard for loop
                    if hasattr(chunk, 'text'):
                        # print(f"[{sid}] Gemini response chunk:", chunk.text) # Optional server log with SID
                        try:
                            await sio.emit("gemini_stream", {"data": chunk.text}, room=sid)
                        except Exception as e:
                            print(f"[{sid}] : Error sending gemini_stream: {e}")  # Log error sending stream
                # Signal stream completion
                try:
                    await sio.emit("stream_finished", room=sid)
                    print(f"[{sid}] : Stream finished signal sent")  # Log stream completion
                except Exception as e:
                    print(f"[{sid}] : Error sending stream_finished: {e}") # Add SID
            else:
                print(f"[{sid}] : Gemini model not initialized")  # Log model not initialized
                try:
                    await sio.emit(
                        "gemini_error", {"error": "Gemini model not initialized"}, room=sid
                    )
                except Exception as e:
                    print(f"[{sid}] : Error sending gemini_error: {e}")  # Log error sending error

        except Exception as e:
            print(f"[{sid}] : Gemini error: {str(e)}") # Add SID
            await sio.emit("gemini_error", {"error": str(e)}, room=sid)


@sio.event
def disconnect(sid):
    print(f"[{sid}] : Disconnected")  # Log disconnection


if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 5000)))  # Use port from environment variable
