# tool-video_to_text.py
# Description: Extract full transcript text from a YouTube video using Whisper.

import tempfile
from pytube import YouTube
import whisper

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

description = (
    "Download a YouTube video audio track and transcribe it to text using Whisper."
)

def function_call(video_url: str) -> str:
    """
    Download audio from the given YouTube URL and return the transcribed text.
    """
    # Initialize YouTube and get audio stream
    yt = YouTube(video_url)
    audio_stream = yt.streams.filter(only_audio=True).first()
    
    # Use a temporary directory for download and transcription
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = audio_stream.download(output_path=tmpdir, filename="audio.mp4")

        # Load Whisper model and transcribe
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        transcript = result.get("text", "").strip()

    # Return the transcript or a message if empty
    return transcript if transcript else "[No transcript available]"
