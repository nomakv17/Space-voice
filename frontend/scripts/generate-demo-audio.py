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

# Demo call script - AI agent handling an HVAC inquiry
DEMO_SCRIPT = [
    {
        "speaker": "ai",
        "text": "Hi, thanks for calling CoolAir HVAC! I'm Sarah, your AI assistant. How can I help you today?"
    },
    {
        "speaker": "customer",
        "text": "Yeah, hi. My AC stopped working this morning and it's getting really hot in here. I need someone to come take a look."
    },
    {
        "speaker": "ai",
        "text": "I'm sorry to hear that! I can definitely help you get that fixed. Just to make sure we send the right technician, is your unit not turning on at all, or is it running but not cooling?"
    },
    {
        "speaker": "customer",
        "text": "It's running, but it's just blowing warm air. The house is at 85 degrees right now."
    },
    {
        "speaker": "ai",
        "text": "Got it, sounds like it could be a refrigerant issue or a compressor problem. I have a technician available this afternoon between 2 and 4 PM, or tomorrow morning between 9 and 11. Which works better for you?"
    },
    {
        "speaker": "customer",
        "text": "This afternoon would be great. The sooner the better."
    },
    {
        "speaker": "ai",
        "text": "Perfect! I've scheduled Mike, one of our senior technicians, to arrive between 2 and 4 PM today. He'll give you a call when he's 30 minutes out. Can I confirm this is for the address on file?"
    },
    {
        "speaker": "customer",
        "text": "Yes, that's correct."
    },
    {
        "speaker": "ai",
        "text": "Excellent! You're all set. Mike will be there this afternoon. In the meantime, try to stay cool, and don't hesitate to call back if you need anything else. Have a great day!"
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
        "model_id": "eleven_multilingual_v2",  # Most natural sounding model
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.5,  # Add some expressiveness
            "use_speaker_boost": True
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")

    return response.content


def generate_demo_audio(api_key: str, output_path: Path) -> None:
    """Generate the demo call audio file."""

    # Create temporary directory for individual clips
    temp_dir = output_path.parent / "temp_clips"
    temp_dir.mkdir(exist_ok=True)

    clip_files = []

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

    print("\nCombining clips...")

    # Concatenate MP3 files directly (works without ffmpeg)
    # MP3 frames are self-contained, so simple concatenation works
    with open(output_path, "wb") as outfile:
        for clip_path in clip_files:
            with open(clip_path, "rb") as infile:
                outfile.write(infile.read())

    print(f"Created combined audio: {output_path}")

    # Cleanup temp files
    print("Cleaning up temporary files...")
    for clip in clip_files:
        clip.unlink(missing_ok=True)
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
