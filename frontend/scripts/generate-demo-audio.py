#!/usr/bin/env python3
"""
Generate demo call audio for SpaceVoice landing page.
Uses OpenAI TTS API to create a realistic HVAC call demonstration.
"""

import os
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai")
    sys.exit(1)


# Demo call script - AI agent handling an HVAC inquiry
DEMO_SCRIPT = [
    {
        "speaker": "ai",
        "voice": "nova",  # Warm, professional female voice
        "text": "Hi, thanks for calling CoolAir HVAC! I'm Sarah, your AI assistant. How can I help you today?"
    },
    {
        "speaker": "customer",
        "voice": "onyx",  # Male customer voice
        "text": "Yeah, hi. My AC stopped working this morning and it's getting really hot in here. I need someone to come take a look."
    },
    {
        "speaker": "ai",
        "voice": "nova",
        "text": "I'm sorry to hear that! I can definitely help you get that fixed. Just to make sure we send the right technician, is your unit not turning on at all, or is it running but not cooling?"
    },
    {
        "speaker": "customer",
        "voice": "onyx",
        "text": "It's running, but it's just blowing warm air. The house is at 85 degrees right now."
    },
    {
        "speaker": "ai",
        "voice": "nova",
        "text": "Got it, sounds like it could be a refrigerant issue or a compressor problem. I have a technician available this afternoon between 2 and 4 PM, or tomorrow morning between 9 and 11. Which works better for you?"
    },
    {
        "speaker": "customer",
        "voice": "onyx",
        "text": "This afternoon would be great. The sooner the better."
    },
    {
        "speaker": "ai",
        "voice": "nova",
        "text": "Perfect! I've scheduled Mike, one of our senior technicians, to arrive between 2 and 4 PM today. He'll give you a call when he's 30 minutes out. Can I confirm this is for the address on file?"
    },
    {
        "speaker": "customer",
        "voice": "onyx",
        "text": "Yes, that's correct."
    },
    {
        "speaker": "ai",
        "voice": "nova",
        "text": "Excellent! You're all set. Mike will be there this afternoon. In the meantime, try to stay cool, and don't hesitate to call back if you need anything else. Have a great day!"
    },
]


def generate_demo_audio(api_key: str, output_path: Path) -> None:
    """Generate the demo call audio file."""
    client = OpenAI(api_key=api_key)

    # Create temporary directory for individual clips
    temp_dir = output_path.parent / "temp_clips"
    temp_dir.mkdir(exist_ok=True)

    clip_files = []

    print("Generating audio clips...")
    for i, line in enumerate(DEMO_SCRIPT):
        print(f"  [{i+1}/{len(DEMO_SCRIPT)}] {line['speaker']}: {line['text'][:50]}...")

        response = client.audio.speech.create(
            model="tts-1-hd",  # High quality
            voice=line["voice"],
            input=line["text"],
            response_format="mp3"
        )

        clip_path = temp_dir / f"clip_{i:02d}.mp3"
        response.stream_to_file(str(clip_path))
        clip_files.append(clip_path)

    print("\nCombining clips...")

    # Try to use ffmpeg to combine clips with small pauses
    try:
        import subprocess

        # Create a file list for ffmpeg
        list_file = temp_dir / "clips.txt"
        with open(list_file, "w") as f:
            for clip in clip_files:
                f.write(f"file '{clip.absolute()}'\n")
                # Add a small silence between clips (using a silent audio file or filter)

        # Combine using ffmpeg concat demuxer
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path)
        ], check=True, capture_output=True)

        print(f"Created combined audio: {output_path}")

    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ffmpeg not available - using first clip as demo")
        # Fallback: just use the combined clips manually or first clip
        import shutil
        shutil.copy(clip_files[0], output_path)
        print(f"Copied first clip to: {output_path}")

    # Cleanup temp files
    print("Cleaning up temporary files...")
    for clip in clip_files:
        clip.unlink(missing_ok=True)
    if (temp_dir / "clips.txt").exists():
        (temp_dir / "clips.txt").unlink()
    temp_dir.rmdir()

    print("Done!")


def main():
    # Get API key from environment or argument
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key and len(sys.argv) > 1:
        api_key = sys.argv[1]

    if not api_key:
        print("Usage: python generate-demo-audio.py [OPENAI_API_KEY]")
        print("Or set OPENAI_API_KEY environment variable")
        sys.exit(1)

    # Output path
    script_dir = Path(__file__).parent
    output_path = script_dir.parent / "public" / "audio" / "demo-call-sample.mp3"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_demo_audio(api_key, output_path)


if __name__ == "__main__":
    main()
