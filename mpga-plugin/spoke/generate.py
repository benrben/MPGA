#!/usr/bin/env python3
"""
Pocket TTS speech generation for MPGA spoke (fallback when server is down).

Usage:
    python generate.py --text "Hello" --output speech.wav
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    from pocket_tts import TTSModel, export_model_state
    from safetensors.torch import load_file
    import scipy.io.wavfile

    spoke_dir = os.path.dirname(__file__)
    voice_file = os.path.join(spoke_dir, "voicedata", "trump.safetensors")
    ref_audio = os.path.join(spoke_dir, "voicedata", "trump_ref.wav")

    model = TTSModel.load_model()

    if os.path.exists(voice_file):
        flat = load_file(voice_file)
        voice = {}
        for k, v in flat.items():
            mod, key = k.split("/", 1)
            voice.setdefault(mod, {})[key] = v
    else:
        voice = model.get_state_for_audio_prompt(ref_audio)
        export_model_state(voice, voice_file)

    audio = model.generate_audio(voice, args.text)
    scipy.io.wavfile.write(args.output, model.sample_rate, audio.numpy())


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
