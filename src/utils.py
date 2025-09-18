import yt_dlp
import time
import json
from pathlib import Path
from src.models import AudioState
import browser_cookie3


audio_state = AudioState()

AUDIO_DIR = Path("audio_files")
STATIC_DIR = Path("static")


def get_youtube_cookies():
    cj = browser_cookie3.chrome(domain_name=".youtube.com")
    return cj


def download_youtube_audio(video_url: str):
    """Downloads audio from a YouTube video and saves it as an MP3 file with the video's title."""
    cookies = get_youtube_cookies()
    ydl_opts = {
        "format": "bestaudio/best",
        "extractaudio": True,
        "audioformat": "mp3",
        "cookiefile": None,
        "cookiejar": cookies,
        "outtmpl": str(AUDIO_DIR / "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        title = info_dict.get("title", "output")

    return f"{title}.mp3"


def scan_audio_files():
    """Scan the audio directory for available songs"""
    audio_state.available_songs = [
        f.name
        for f in AUDIO_DIR.iterdir()
        if f.suffix.lower() in [".mp3", ".wav", ".ogg", ".m4a"]
    ]


async def broadcast_state():
    """Broadcast current audio state to all connected clients"""
    if not audio_state.connections:
        return

    state_data = {
        "type": "state_update",
        "current_song": audio_state.current_song,
        "is_playing": audio_state.is_playing,
        "position": audio_state.get_current_position(),
        "queue": audio_state.queue,
        "available_songs": audio_state.available_songs,
        "timestamp": time.time(),
    }

    disconnected = []
    for client_id, websocket in audio_state.connections.items():
        try:
            await websocket.send_text(json.dumps(state_data))
        except:
            disconnected.append(client_id)

    # Remove disconnected clients
    for client_id in disconnected:
        audio_state.connections.pop(client_id, None)
