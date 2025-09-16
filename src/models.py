from typing import Dict, List
from fastapi import WebSocket
import time


class AudioState:
    def __init__(self):
        self.current_song: str = None
        self.is_playing: bool = False
        self.start_time: float = 0.0  # When the current song started playing
        self.pause_time: float = 0.0  # Total pause duration
        self.last_action_time: float = time.time()
        self.queue: List[str] = []
        self.available_songs: List[str] = []
        self.connections: Dict[str, WebSocket] = {}

    def get_current_position(self) -> float:
        """Get current playback position in seconds"""
        if not self.current_song or not self.is_playing:
            return 0.0
        current_time = time.time()
        return current_time - self.start_time - self.pause_time
