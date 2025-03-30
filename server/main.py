from aiohttp import web
import socketio
import os
import google.generativeai as genai
from dotenv import load_dotenv

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
    print("[Server] Gemini API initialization error:", str(e))
    model = None


@sio.event
async def connect(sid, environ):
    """Handle a new client connection."""
    print(f"[{sid}] : Connected")


@sio.event
async def chat_message(sid, data):
    """Handle incoming chat messages from clients."""
    print(f"[{sid}] : Server received message: {data}")
    user_message = data.get("message", "")

    if user_message:
        try:
            print(f"[{sid}] : Sending message to Gemini: {user_message}")
            if model:
                response = model.generate_content(user_message, stream=True)
                for chunk in response:
                    if hasattr(chunk, "text"):
                        try:
                            await sio.emit("gemini_stream", {"data": chunk.text}, room=sid)
                        except Exception as e:
                            print(f"[{sid}] : Error sending gemini_stream: {e}")
                try:
                    await sio.emit("stream_finished", room=sid)
                    print(f"[{sid}] : Stream finished signal sent")
                except Exception as e:
                    print(f"[{sid}] : Error sending stream_finished: {e}")
            else:
                print(f"[{sid}] : Gemini model not initialized")
                try:
                    await sio.emit("gemini_error", {"error": "Gemini model not initialized"}, room=sid)
                except Exception as e:
                    print(f"[{sid}] : Error sending gemini_error: {e}")

        except Exception as e:
            print(f"[{sid}] : Gemini error: {str(e)}")
            await sio.emit("gemini_error", {"error": str(e)}, room=sid)


@sio.event
def disconnect(sid):
    """Handle client disconnection."""
    print(f"[{sid}] : Disconnected")


if __name__ == "__main__":
    web.run_app(app, port=int(os.getenv("PORT", 5000)))
