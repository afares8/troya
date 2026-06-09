"""Voice interface for Cascade CLI — speech-to-text and text-to-speech."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .ui import Colors, print_error, print_info, print_success


def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def record_audio(duration: int = 5) -> Path | None:
    """Record audio using ffmpeg."""
    if not check_ffmpeg():
        print_error("ffmpeg not found. Install with: brew install ffmpeg")
        return None
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    print_info(f"Recording for {duration}s... (speak now)")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "avfoundation", "-i", ":default", "-t", str(duration), path],
            capture_output=True,
            check=True,
        )
        return Path(path)
    except subprocess.CalledProcessError as e:
        print_error(f"Recording failed: {e}")
        return None


def transcribe_with_whisper(audio_path: Path, model: str = "base") -> str:
    """Transcribe audio using Whisper (requires openai-whisper package)."""
    try:
        import whisper
        print_info("Loading Whisper model...")
        wmodel = whisper.load_model(model)
        result = wmodel.transcribe(str(audio_path))
        return result["text"].strip()
    except ImportError:
        print_error("openai-whisper not installed. Run: pip install openai-whisper")
        return ""
    except Exception as e:
        print_error(f"Transcription failed: {e}")
        return ""


def speak_text(text: str, voice: str = "Samantha") -> None:
    """Speak text using macOS say command."""
    try:
        subprocess.run(["say", "-v", voice, text], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Fallback to espeak or pyttsx3
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except ImportError:
            pass


def voice_chat(client, context, executor) -> str:
    """Record voice, transcribe, send to AI, speak response."""
    audio = record_audio(duration=5)
    if not audio:
        return ""
    try:
        text = transcribe_with_whisper(audio)
        if not text:
            return ""
        print(f"{Colors.GREEN}You (voice):{Colors.RESET} {text}")
        # Now process normally
        from .agentic import run_agentic
        response = run_agentic(client, context, executor, text)
        print(f"{Colors.MAGENTA}Cascade:{Colors.RESET} {response[:200]}")
        speak_text(response[:500])
        return response
    finally:
        audio.unlink(missing_ok=True)
