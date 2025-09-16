import yt_dlp
import time
import json
from pathlib import Path
from src.models import AudioState


audio_state = AudioState()

AUDIO_DIR = Path("audio_files")
STATIC_DIR = Path("static")

COOKIE_FILE = STATIC_DIR / "cookies.txt"

# def download_youtube_audio(video_url: str):
#     """Downloads audio from a YouTube video and saves it as an MP3 file with the video's title."""
#     ydl_opts = {
#         "format": "bestaudio/best",
#         "extractaudio": True,
#         "audioformat": "mp3",
#         "outtmpl": str(AUDIO_DIR / "%(title)s.%(ext)s"),
#         "postprocessors": [
#             {
#                 "key": "FFmpegExtractAudio",
#                 "preferredcodec": "mp3",
#                 "preferredquality": "320",
#             }
#         ],
#     }

#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         info_dict = ydl.extract_info(video_url, download=True)
#         title = info_dict.get("title", "output")

#     return f"{title}.mp3"


# def download_youtube_audio(video_url: str):
#     """Downloads audio from a YouTube video and saves it as an MP3 file."""
#     ydl_opts = {
#         'format': 'bestaudio/best',
#         'extractaudio': True,
#         'audioformat': 'mp3',
#         "outtmpl": str(AUDIO_DIR / "%(title)s.%(ext)s"),
#         'postprocessors': [{
#             'key': 'FFmpegExtractAudio',
#             'preferredcodec': 'mp3',
#             'preferredquality': '320',
#         }],
#         # Anti-bot detection measures
#         'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
#         'referer': 'https://www.youtube.com/',
#         'extractor_retries': 3,
#         'fragment_retries': 3,
#         'retry_sleep': 'exp',
#         'sleep_interval': 1,
#         'max_sleep_interval': 5,
#         # Additional headers to mimic browser
#         'http_headers': {
#             'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
#             'Accept-Language': 'en-US,en;q=0.5',
#             'Accept-Encoding': 'gzip, deflate',
#             'Connection': 'keep-alive',
#             'Upgrade-Insecure-Requests': '1',
#         },
#         # Bypass some geo-restrictions
#         'geo_bypass': True,
#         'geo_bypass_country': 'US',
#         # Ignore errors for unavailable formats
#         'ignoreerrors': False,
#         'no_warnings': False,
#         # Use IPv4 to avoid some network issues
#         'force_ipv4': True,
#     }
    
#     # Try multiple extraction strategies
#     extraction_strategies = [
#         # Strategy 1: Standard extraction
#         ydl_opts,
        
#         # Strategy 2: With different user agent (mobile)
#         {**ydl_opts, 'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'},
        
#         # Strategy 3: Lower quality fallback
#         {**ydl_opts, 'format': 'worst[ext=mp4]/worst', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}]},
        
#         # Strategy 4: Audio-only format
#         {**ydl_opts, 'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio'},
#     ]
    
#     last_error = None
#     for i, opts in enumerate(extraction_strategies):
#         try:
#             print(f"Attempting download strategy {i+1}/4...")
#             with yt_dlp.YoutubeDL(opts) as ydl:
#                 info_dict = ydl.extract_info(video_url, download=True)
#                 title = info_dict.get("title", "output")
#                 ydl.download([video_url])
#             print(f"Successfully downloaded using strategy {i+1}")
#             return f"{title}.mp3"
#         except Exception as e:
#             print(f"Strategy {i+1} failed: {str(e)}")
#             last_error = e
#             if i < len(extraction_strategies) - 1:
#                 print("Trying next strategy...")
#                 time.sleep(2)  # Wait between attempts
#                 continue
    
#     # If all strategies fail, raise the last error
#     raise Exception(f"All download strategies failed. Last error: {str(last_error)}")


def download_youtube_audio(video_url: str):
    """Downloads audio from a YouTube video and saves it as an MP3 file with the video's title."""

    ydl_opts = {
        "format": "bestaudio/best",
        "extractaudio": True,
        "audioformat": "mp3",
        "outtmpl": str(AUDIO_DIR / "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }
        ],
    }


    ydl_opts["cookiefile"] = str(COOKIE_FILE)

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
