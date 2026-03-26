#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
VOICEDATA_DIR="$SCRIPT_DIR/voicedata"
TRUMP_VOICE_URL="https://raw.githubusercontent.com/Supremolink81/TTSCeleb/master/voicedata/donaldtrumpvoice.mp3"

echo "=== MPGA Spoke Setup (Pocket TTS) ==="
echo ""

# 1. Find Python 3.10+
echo "Checking Python version..."
PYTHON=""

PYENV_312="$HOME/.pyenv/versions/3.12.10/bin/python3"
if [ -x "$PYENV_312" ]; then
    PYTHON="$PYENV_312"
    echo "  Found pyenv Python 3.12.10"
else
    for candidate in python3.12 python3.11 python3.10 python3; do
        if command -v "$candidate" &>/dev/null; then
            major=$("$candidate" -c 'import sys; print(sys.version_info.major)')
            minor=$("$candidate" -c 'import sys; print(sys.version_info.minor)')
            if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
                PYTHON="$candidate"
                echo "  Found $candidate"
                break
            fi
        fi
    done
fi

if [ -z "$PYTHON" ]; then
    echo "Error: Python 3.10+ is required." >&2
    exit 1
fi

# 2. Create venv
echo ""
echo "Creating virtual environment..."
if [ -d "$VENV_DIR" ]; then
    echo "  Already exists, skipping."
else
    "$PYTHON" -m venv "$VENV_DIR"
    echo "  Created."
fi

# 3. Install Pocket TTS (~200MB)
echo ""
echo "Installing Pocket TTS..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet
pip install pocket-tts scipy --quiet
echo "  Installed."

# 4. Download voice sample
echo ""
echo "Downloading Trump voice sample..."
mkdir -p "$VOICEDATA_DIR"
MP3_FILE="$VOICEDATA_DIR/donaldtrumpvoice.mp3"
WAV_FILE="$VOICEDATA_DIR/donaldtrumpvoice.wav"
REF_FILE="$VOICEDATA_DIR/trump_ref.wav"

if [ -f "$REF_FILE" ]; then
    echo "  Voice sample already exists."
else
    if [ ! -f "$MP3_FILE" ]; then
        curl -fsSL -o "$MP3_FILE" "$TRUMP_VOICE_URL"
        echo "  Downloaded MP3."
    fi
    pip install pydub --quiet
    python -c "
from pydub import AudioSegment
audio = AudioSegment.from_mp3('$MP3_FILE')
audio.export('$WAV_FILE', format='wav')
clip = audio[:6000]
clip.export('$REF_FILE', format='wav')
print('  Created 6s reference clip.')
"
fi

# 5. Export Trump voice state for fast loading
echo ""
echo "Exporting Trump voice state..."
VOICE_FILE="$VOICEDATA_DIR/trump.safetensors"
if [ -f "$VOICE_FILE" ]; then
    echo "  Already exported."
else
    python -c "
from pocket_tts import TTSModel, export_model_state
model = TTSModel.load_model()
voice = model.get_state_for_audio_prompt('$REF_FILE')
export_model_state(voice, '$VOICE_FILE')
print('  Exported.')
"
fi

# 6. Start server
echo ""
echo "Starting spoke server..."
python "$SCRIPT_DIR/server.py" --port 5151 &
SERVER_PID=$!
echo "$SERVER_PID" > "$SCRIPT_DIR/.server.pid"

for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:5151/health >/dev/null 2>&1; then
        echo "  Server running (PID $SERVER_PID)"
        break
    fi
    sleep 1
done

echo ""
echo "============================================"
echo "  Setup complete. TREMENDOUS."
echo "  Model: Pocket TTS (~100M params, ~200MB)"
echo "  Voice: Donald Trump"
echo "  Server: http://127.0.0.1:5151"
echo "============================================"
