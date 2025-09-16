from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from contextlib import asynccontextmanager
import asyncio
import json
import time
import uuid
from pathlib import Path
from src.utils import (
    download_youtube_audio,
    scan_audio_files,
    broadcast_state,
    audio_state,
)


app = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scan_audio_files()
    yield


AUDIO_DIR = Path("audio_files")
STATIC_DIR = Path("static")
TEMPLATES_DIR = Path("templates")

AUDIO_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

app.router.lifespan_context = lifespan
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/")
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/audio/{filename}")
async def get_audio_file(filename: str):
    file_path = AUDIO_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path)


@app.post("/download-youtube")
async def download_youtube(data: dict):
    try:
        video_url = data.get("url")
        if not video_url:
            raise HTTPException(status_code=400, detail="URL is required")

        # Download in a separate thread to avoid blocking
        def download_task():
            try:
                result = download_youtube_audio(video_url)
                scan_audio_files()  # Refresh available songs
                return result
            except Exception as e:
                print(f"Download error: {e}")
                return None

        # Run download in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, download_task)

        if result:
            scan_audio_files()
            await broadcast_state()
            return {"success": True, "filename": result}
        else:
            raise HTTPException(status_code=500, detail="Download failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = str(uuid.uuid4())
    audio_state.connections[client_id] = websocket

    # Send initial state
    await broadcast_state()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "play":
                audio_state.is_playing = True
                audio_state.start_time = time.time() - message.get("position", 0)
                audio_state.pause_time = 0
                await broadcast_state()

            elif message["type"] == "pause":
                audio_state.is_playing = False
                audio_state.pause_time += time.time() - (
                    audio_state.start_time + audio_state.pause_time
                )
                await broadcast_state()

            elif message["type"] == "seek":
                position = message.get("position", 0)
                audio_state.start_time = time.time() - position
                audio_state.pause_time = 0
                await broadcast_state()

            elif message["type"] == "add_to_queue":
                song = message.get("song")
                if (
                    song in audio_state.available_songs
                    and song not in audio_state.queue
                ):
                    audio_state.queue.append(song)
                    await broadcast_state()

            elif message["type"] == "remove_from_queue":
                song = message.get("song")
                if song in audio_state.queue:
                    audio_state.queue.remove(song)
                    await broadcast_state()

            elif message["type"] == "play_song":
                song = message.get("song")
                if song in audio_state.available_songs:
                    audio_state.current_song = song
                    audio_state.is_playing = True
                    audio_state.start_time = time.time()
                    audio_state.pause_time = 0
                    # Remove from queue if it was there
                    if song in audio_state.queue:
                        audio_state.queue.remove(song)
                    await broadcast_state()

            elif message["type"] == "next_song":
                if audio_state.queue:
                    next_song = audio_state.queue.pop(0)
                    audio_state.current_song = next_song
                    audio_state.is_playing = True
                    audio_state.start_time = time.time()
                    audio_state.pause_time = 0
                    await broadcast_state()

    except WebSocketDisconnect:
        audio_state.connections.pop(client_id, None)


if __name__ == "__main__":
    import uvicorn

    print("Starting Audio Jamming Platform...")
    print("Make sure you have yt-dlp and ffmpeg installed:")
    print("pip install yt-dlp")
    print("And ffmpeg: https://ffmpeg.org/download.html")
    uvicorn.run(app, host="0.0.0.0", port=8000)
