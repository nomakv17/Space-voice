#!/usr/bin/env python3
"""
Generate demo call audio for SpaceVoice landing page.
Uses ElevenLabs API for natural-sounding conversational voices.
"""

import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests package not installed. Run: pip install requests")
    sys.exit(1)


# ElevenLabs Voice IDs - These are natural conversational voices
VOICES = {
    # Sarah - soft, warm female voice (great for AI assistant)
    "ai": "EXAVITQu4vr4xnSDxMaL",
    # Josh - conversational male voice (natural customer sound)
    "customer": "TxGEqnHWrfWFTfGW9XjX",
}

# Demo call script - Natural conversational flow with real speech patterns
# Using filler words, casual language, and natural pacing
DEMO_SCRIPT = [
    {
        "speaker": "ai",
        "text": "Hi there, CoolAir HVAC, this is Sarah. How can I help you?"
    },
    {
        "speaker": "customer",
        "text": "Hey, uh, yeah so my AC just stopped working and it's like... it's really hot in here. I need somebody to come out."
    },
    {
        "speaker": "ai",
        "text": "Oh no, I'm so sorry! Okay, let me help you with that. So is it not turning on at all, or is it running but just not cooling?"
    },
    {
        "speaker": "customer",
        "text": "No it's running, but it's just blowing like... warm air? And the house is at like 85 degrees already."
    },
    {
        "speaker": "ai",
        "text": "Ugh, that's rough. Okay, so that sounds like maybe a refrigerant issue. Um, let me check availability... So I've got a tech free this afternoon between 2 and 4, or tomorrow morning around 9. What works for you?"
    },
    {
        "speaker": "customer",
        "text": "Oh, this afternoon for sure. The sooner the better honestly."
    },
    {
        "speaker": "ai",
        "text": "Got it, totally understand. Okay so I'm putting you down for today, 2 to 4. Mike's gonna come out, he's one of our best guys. He'll call you when he's about 30 minutes away, cool?"
    },
    {
        "speaker": "customer",
        "text": "Yeah, perfect. Thanks."
    },
    {
        "speaker": "ai",
        "text": "You got it! Hang in there, and he'll get you taken care of this afternoon. Bye bye!"
    },
]


def generate_speech(api_key: str, voice_id: str, text: str) -> bytes:
    """Generate speech audio using ElevenLabs API."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }

    data = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",  # Fast, natural conversational model
        "voice_settings": {
            "stability": 0.3,  # Lower = more expressive/variable
            "similarity_boost": 0.8,
            "style": 0.7,  # Higher = more dramatic/emotional delivery
            "use_speaker_boost": True
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")

    return response.content


def create_silence_mp3(duration_ms: int, output_path: Path) -> None:
    """Create a silent MP3 file using a minimal valid MP3 frame repeated."""
    # Minimal valid MP3 frame (silent, 128kbps, 44.1kHz, mono)
    # This is a single valid MPEG Audio Layer 3 frame of silence
    silent_frame = bytes([
        0xFF, 0xFB, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ])
    # Each frame is ~26ms at 128kbps, so repeat for duration
    num_frames = max(1, duration_ms // 26)
    with open(output_path, "wb") as f:
        for _ in range(num_frames):
            f.write(silent_frame)


def generate_demo_audio(api_key: str, output_path: Path) -> None:
    """Generate the demo call audio file."""

    # Create temporary directory for individual clips
    temp_dir = output_path.parent / "temp_clips"
    temp_dir.mkdir(exist_ok=True)

    clip_files = []

    # Create silence files for pauses between speakers
    short_pause = temp_dir / "pause_short.mp3"  # 400ms - thinking pause
    long_pause = temp_dir / "pause_long.mp3"    # 800ms - between speakers
    create_silence_mp3(400, short_pause)
    create_silence_mp3(800, long_pause)

    print("Generating audio clips with ElevenLabs...")
    for i, line in enumerate(DEMO_SCRIPT):
        print(f"  [{i+1}/{len(DEMO_SCRIPT)}] {line['speaker']}: {line['text'][:50]}...")

        voice_id = VOICES[line["speaker"]]
        audio_data = generate_speech(api_key, voice_id, line["text"])

        clip_path = temp_dir / f"clip_{i:02d}.mp3"
        with open(clip_path, "wb") as f:
            f.write(audio_data)
        clip_files.append(clip_path)

        # Small delay to avoid rate limiting
        time.sleep(0.3)

    print("\nCombining clips with natural pauses...")

    # Concatenate MP3 files with pauses between speakers
    with open(output_path, "wb") as outfile:
        prev_speaker = None
        for i, clip_path in enumerate(clip_files):
            # Add pause between different speakers (not before first clip)
            if i > 0:
                current_speaker = DEMO_SCRIPT[i]["speaker"]
                if prev_speaker != current_speaker:
                    # Longer pause when speaker changes
                    with open(long_pause, "rb") as pf:
                        outfile.write(pf.read())
                else:
                    # Shorter pause for same speaker continuing
                    with open(short_pause, "rb") as pf:
                        outfile.write(pf.read())

            with open(clip_path, "rb") as infile:
                outfile.write(infile.read())

            prev_speaker = DEMO_SCRIPT[i]["speaker"]

    print(f"Created combined audio: {output_path}")

    # Cleanup temp files
    print("Cleaning up temporary files...")
    for clip in clip_files:
        clip.unlink(missing_ok=True)
    short_pause.unlink(missing_ok=True)
    long_pause.unlink(missing_ok=True)
    temp_dir.rmdir()

    # Show file size
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\nDone! Final audio: {size_mb:.2f} MB")


def main():
    # Get API key from environment or argument
    api_key = os.environ.get("ELEVENLABS_API_KEY")

    if not api_key and len(sys.argv) > 1:
        api_key = sys.argv[1]

    if not api_key:
        print("Usage: python generate-demo-audio.py [ELEVENLABS_API_KEY]")
        print("Or set ELEVENLABS_API_KEY environment variable")
        sys.exit(1)

    # Output path
    script_dir = Path(__file__).parent
    output_path = script_dir.parent / "public" / "audio" / "demo-call-sample.mp3"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_demo_audio(api_key, output_path)


if __name__ == "__main__":
    main()
