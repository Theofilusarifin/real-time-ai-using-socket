# Real-time AI Application Using Socket

![Demo Video](./assets/demo.gif)

This application enables real-time communication between multiple clients and a server using Socket.IO. It supports live chat and streams AI responses from Google Generative AI (Gemini) on demand.

## Key Features

- **Socket.IO Communication:**  
  Custom events (`connect`, `disconnect`, `broadcast_message`, `gemini_stream`, and `stream_finished`) provide real-time messaging.

- **Authentication:**  
  Clients supply a username at connection, which is saved in the session.

- **Gemini Streaming:**  
  When a message contains `@gemini`, the server queries Google Generative AI and streams the response in chunks. The first chunk is prefixed (e.g., `🤖 gemini:`).

- **Asynchronous I/O:**  
  Uses prompt_toolkit to handle non-blocking terminal input/output alongside live events.

## Prerequisites

- **Python 3.11** is required.
- Create a new virtual environment:
  ```bash
  python3.11 -m venv .venv
  source .venv/bin/activate  # On Windows: .venv\Scripts\activate
  ```
- Install the required package:
  ```bash
  pip install uv
  ```
- Sync dependencies using **uv**:
  ```bash
  uv sync
  ```

## Configuration

Create a `.env` file in the project root with the following content:```env
# Server settings
APP_HOST=0.0.0.0
APP_PORT=5000

# Google Generative AI API Key
GOOGLE_API_KEY=your_google_api_key_here
```

Replace `your_google_api_key_here` with your actual API key.

## Usage

### Starting the Server

1. Open your terminal.
2. Navigate to the project directory.
3. Run the server:
   ```bash
   python server/main.py
   ```

### Starting the Client

1. Open a new terminal tab.
2. Activate the same virtual environment.
3. Navigate to the project directory.
4. Run the client:
   ```bash
   python client/main.py
   ```

### Running Multiple Clients

Open additional terminal tabs and run the client command in each to simulate multi-user communication.

