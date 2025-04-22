# tool-video_to_text.py
# Description: Extract full transcript text from a YouTube video using OpenAI Whisper API.

import tempfile
from pytube import YouTube
import openai

# Schema for get_tools_schema()
function_schema = {
    "type": "object",
    "properties": {
        "video_url": {
            "type": "string",
            "description": "YouTube video URL to transcribe"
        }
    },
    "required": ["video_url"]
}

# Description shown in the Tools management UI
description = (
    "Download a YouTube video's audio track and transcribe it to text using OpenAI Whisper API."
)

def function_call(video_url: str) -> str:
    """
    Download audio from the given YouTube URL and return the transcribed text using OpenAI's Whisper API.
    """
    # Initialize YouTube and get the audio stream
    yt = YouTube(video_url)
    audio_stream = yt.streams.filter(only_audio=True).first()

    # Use a temporary directory to download and process
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = audio_stream.download(output_path=tmpdir, filename="audio.mp4")

        # Transcribe using OpenAI Whisper API
        with open(audio_path, "rb") as audio_file:
            response = openai.Audio.transcriptions.create(
                file=audio_file,
                model="whisper-1"
            )
        transcript = response.get("text", "").strip()

    return transcript or "[No transcript available]"
