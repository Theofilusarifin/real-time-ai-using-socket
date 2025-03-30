from aiohttp import web
import socketio
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="aiohttp")
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
async def connect(sid, environ, auth):
    """Handles the connect event."""
    username = auth.get("username")
    if not username:
        raise ConnectionRefusedError("Missing username")
    await sio.save_session(sid, {"username": username})
    await sio.enter_room(sid, "default_room")
    print(f"[{sid}] : {username} connected and joined 'default_room'")


@sio.event
async def chat_message(sid, data):
    """Handles the chat_message event."""
    session = await sio.get_session(sid)
    username = session.get("username", "Unknown")
    user_message = data.get("message", "").strip()
    room = "default_room"
    if not user_message:
        return
    print(f"[{sid}] {username}: {user_message}")
    await sio.emit(
        "broadcast_message",
        {"user": username, "message": user_message},
        room=room,
        skip_sid=sid,
    )

    # Process Gemini query if "@gemini" is in the message
    if "@gemini" in user_message.lower():
        try:
            at_index = user_message.lower().index("@gemini")
            question = user_message[at_index + len("@gemini") :].strip()
            if question and model:
                print(f"[{sid}] Asking Gemini: {question}")
                response = model.generate_content(question, stream=True)
                first_chunk = True
                for chunk in response:
                    if hasattr(chunk, "text") and chunk.text:
                        if first_chunk:
                            text_to_send = "\n🤖 gemini: " + chunk.text
                            first_chunk = False
                        else:
                            text_to_send = chunk.text
                        await sio.emit(
                            "gemini_stream", {"data": text_to_send}, room=room
                        )
                await sio.emit("stream_finished", room=room)
            else:
                await sio.emit(
                    "broadcast_message",
                    {
                        "user": "Gemini 🤖",
                        "message": "Sorry, I didn't catch your question.",
                    },
                    room=room,
                    skip_sid=sid,
                )
        except Exception as e:
            print(f"[Gemini Error]: {e}")
            await sio.emit(
                "broadcast_message",
                {"user": "Gemini 🤖", "message": f"Gemini Error: {str(e)}"},
                room=room,
                skip_sid=sid,
            )


@sio.event
async def save_note(sid, data):
    """Handles the save_note event."""
    note = data.get("note")
    print(f"[{sid}] saved note: {note}")
    return {"status": "success", "length": len(note)}


@sio.event
def disconnect(sid):
    """Handles the disconnect event."""
    print(f"[{sid}] : Disconnected")


if __name__ == "__main__":
    # Run the app using APP_HOST and APP_PORT from .env
    web.run_app(
        app,
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 5000)),
    )
