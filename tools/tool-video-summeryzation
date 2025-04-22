# tool-video_summary_pitch_tool.py
# Description: Generate a 30-second pitch and a full summary from a video/audio link.

from typing import Literal
import tempfile
import os
import streamlit as st
from pytube import YouTube
import whisper
import openai

function_schema = {
    "type": "object",
    "properties": {
        "video_url": {
            "type": "string",
            "description": "YouTube video URL or a direct video link"
        },
        "mode": {
            "type": "string",
            "enum": ["Summary", "Pitch", "Both"],
            "description": "Choose what you want to generate"
        }
    },
    "required": ["video_url", "mode"]
}

def function_call(video_url: str, mode: Literal["Summary", "Pitch", "Both"]):
    """Generates a summary and/or a 30-second pitch from a video URL"""

    with tempfile.TemporaryDirectory() as tmpdir:
        st.info("🔄 Downloading video...")
        yt = YouTube(video_url)
        video = yt.streams.filter(only_audio=True).first()
        video_path = video.download(output_path=tmpdir, filename="audio.mp4")

        st.info("🎙 Transcribing audio...")
        model = whisper.load_model("base")
        result = model.transcribe(video_path)
        transcript = result["text"]

        if not transcript.strip():
            return "⚠️ No speech detected."

        prompts = {
            "Summary": f"Summarize this transcript in clear English:\n{transcript}",
            "Pitch": f"Generate a compelling 30-second pitch based on this transcript:\n{transcript}"
        }

        outputs = {}
        if mode in ["Summary", "Both"]:
            st.info("🧠 Creating summary...")
            summary = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompts["Summary"]}]
            ).choices[0].message.content.strip()
            outputs["Summary"] = summary

        if mode in ["Pitch", "Both"]:
            st.info("🎯 Crafting pitch...")
            pitch = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompts["Pitch"]}]
            ).choices[0].message.content.strip()
            outputs["Pitch"] = pitch

        return outputs
