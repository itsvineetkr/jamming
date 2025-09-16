let ws;
let audioState = {
    currentSong: null,
    isPlaying: false,
    position: 0,
    queue: [],
    availableSongs: [],
    timestamp: 0
};
let isUpdatingFromServer = false;
let audio = document.getElementById('audioPlayer');

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onopen = function () {
        document.getElementById('connectionStatus').textContent = 'Connected';
        document.getElementById('connectionStatus').className = 'connection-status connected';
    };

    ws.onclose = function () {
        document.getElementById('connectionStatus').textContent = 'Disconnected';
        document.getElementById('connectionStatus').className = 'connection-status';
        setTimeout(connectWebSocket, 3000);
    };

    ws.onmessage = function (event) {
        const data = JSON.parse(event.data);
        if (data.type === 'state_update') {
            updateAudioState(data);
        }
    };
}

function updateAudioState(newState) {
    isUpdatingFromServer = true;

    // Update current song
    if (newState.current_song !== audioState.currentSong) {
        audioState.currentSong = newState.current_song;
        if (newState.current_song) {
            audio.src = `/audio/${newState.current_song}`;
            document.getElementById('currentSong').textContent = newState.current_song;
        } else {
            document.getElementById('currentSong').textContent = 'No song selected';
        }
    }

    // Update play state
    if (newState.is_playing !== audioState.isPlaying) {
        audioState.isPlaying = newState.is_playing;
        if (newState.is_playing) {
            audio.play().catch(e => console.log('Play failed:', e));
            document.getElementById('playBtn').innerHTML = '<i class="fa-solid fa-pause"></i>';
        } else {
            audio.pause();
            document.getElementById('playBtn').innerHTML = '<i class="fa-solid fa-play"></i>';
        }
    }

    // Sync position (with some tolerance for network latency)
    const serverTime = Date.now() / 1000;
    const latency = serverTime - newState.timestamp;
    const expectedPosition = newState.position + (newState.is_playing ? latency : 0);

    if (Math.abs(audio.currentTime - expectedPosition) > 0.5) {
        audio.currentTime = expectedPosition;
    }

    // Update lists
    audioState.queue = newState.queue;
    audioState.availableSongs = newState.available_songs;

    updateSongLists();
    isUpdatingFromServer = false;
}

function updateSongLists() {
    // Update available songs
    const availableDiv = document.getElementById('availableSongs');
    availableDiv.innerHTML = '';

    audioState.availableSongs.forEach(song => {
        const div = document.createElement('div');
        div.className = 'song-item';
        div.innerHTML = `
                    <span class="song-name" onclick="playSong('${song}')">${song}</span>
                    <div class="song-actions">
                        <button class="btn secondary small-btn" onclick="addToQueue('${song}')">Add</button>
                    </div>
                `;
        availableDiv.appendChild(div);
    });

    // Update queue
    const queueDiv = document.getElementById('queueSongs');
    queueDiv.innerHTML = '';

    audioState.queue.forEach(song => {
        const div = document.createElement('div');
        div.className = 'song-item';
        div.innerHTML = `
                    <span class="song-name">${song}</span>
                    <div class="song-actions">
                        <button class="btn small-btn" onclick="removeFromQueue('${song}')">Remove</button>
                    </div>
                `;
        queueDiv.appendChild(div);
    });
}

function sendMessage(message) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
    }
}

function playPause() {
    if (audioState.isPlaying) {
        sendMessage({ type: 'pause' });
    } else {
        sendMessage({ type: 'play', position: audio.currentTime });
    }
}

function nextSong() {
    sendMessage({ type: 'next_song' });
}

function playSong(song) {
    sendMessage({ type: 'play_song', song: song });
}

function addToQueue(song) {
    sendMessage({ type: 'add_to_queue', song: song });
}

function removeFromQueue(song) {
    sendMessage({ type: 'remove_from_queue', song: song });
}

function seek(event) {
    if (!audio.duration) return;

    const rect = event.target.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    const position = percent * audio.duration;

    sendMessage({ type: 'seek', position: position });
}

function updateProgress() {
    if (isUpdatingFromServer) return;

    const progress = document.getElementById('progressBar');
    const currentTime = document.getElementById('currentTime');

    if (audio.duration) {
        const percent = (audio.currentTime / audio.duration) * 100;
        progress.style.width = percent + '%';
        currentTime.textContent = formatTime(audio.currentTime);
    }
}

function updateDuration() {
    const totalTime = document.getElementById('totalTime');
    if (audio.duration) {
        totalTime.textContent = formatTime(audio.duration);
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

async function downloadYoutube() {
    const url = document.getElementById('ytUrl').value.trim();
    if (!url) {
        showStatus('Please enter a YouTube URL', 'error');
        return;
    }

    showStatus('Downloading...', 'success');
    const downloadBtn = event.target;
    downloadBtn.disabled = true;
    downloadBtn.textContent = 'Downloading...';

    try {
        const response = await fetch('/download-youtube', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url })
        });

        const result = await response.json();

        if (result.success) {
            showStatus(`Downloaded: ${result.filename}`, 'success');
            document.getElementById('ytUrl').value = '';
        } else {
            showStatus('Download failed', 'error');
        }
    } catch (error) {
        showStatus('Download failed: ' + error.message, 'error');
    } finally {
        downloadBtn.disabled = false;
        downloadBtn.textContent = 'Download';
    }
}

function showStatus(message, type) {
    const status = document.getElementById('downloadStatus');
    status.textContent = message;
    status.className = `status ${type}`;
    status.style.display = 'block';

    setTimeout(() => {
        status.style.display = 'none';
    }, 5000);
}

// Initialize
connectWebSocket();

// Handle Enter key in URL input
document.getElementById('ytUrl').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        downloadYoutube();
    }
});