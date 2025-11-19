"""
Open WebUI Function: Audio Transcription with Diarization
Calls WhisperX service to transcribe and diarize audio files
"""
import os
import requests
from typing import Optional
from pydantic import BaseModel, Field


class Pipe:
    """Open WebUI Pipe for audio transcription with speaker diarization"""
    
    class Valves(BaseModel):
        WHISPERX_SERVICE_URL: str = Field(
            default=os.getenv("WHISPERX_SERVICE_URL", "http://localhost:8000"),
            description="URL of the WhisperX service"
        )
        ENABLE_DIARIZATION: bool = Field(
            default=os.getenv("ENABLE_DIARIZATION", "true").lower() == "true",
            description="Enable speaker diarization"
        )
        MIN_SPEAKERS: Optional[int] = Field(
            default=int(os.environ["MIN_SPEAKERS"]) if os.getenv("MIN_SPEAKERS") else None,
            description="Minimum number of speakers (optional)"
        )
        MAX_SPEAKERS: Optional[int] = Field(
            default=int(os.environ["MAX_SPEAKERS"]) if os.getenv("MAX_SPEAKERS") else None,
            description="Maximum number of speakers (optional)"
        )
    
    def __init__(self):
        self.type = "pipe"
        self.id = "transcribe_audio"
        self.name = "Audio Transcription (Diarized)"
        self.valves = self.Valves()
    
    def pipe(self, body: dict) -> dict:
        """
        Process audio file and return diarized transcript
        
        Expected body format:
        {
            "messages": [...],
            "files": [{"type": "audio", "url": "...", "name": "..."}]
        }
        """
        # Check if there are audio files
        files = body.get("files", [])
        audio_files = [f for f in files if f.get("type") == "audio"]
        
        if not audio_files:
            return {
                "messages": body.get("messages", []) + [{
                    "role": "assistant",
                    "content": "No audio file detected. Please upload an audio file to transcribe."
                }]
            }
        
        # Process first audio file
        audio_file = audio_files[0]
        
        try:
            # Download audio file
            audio_url = audio_file.get("url")
            audio_response = requests.get(audio_url)
            audio_response.raise_for_status()
            
            # Send to WhisperX service
            files_payload = {
                "audio": (audio_file.get("name", "audio.mp3"), audio_response.content)
            }
            
            params = {
                "enable_diarization": self.valves.ENABLE_DIARIZATION,
            }
            
            if self.valves.MIN_SPEAKERS:
                params["min_speakers"] = self.valves.MIN_SPEAKERS
            if self.valves.MAX_SPEAKERS:
                params["max_speakers"] = self.valves.MAX_SPEAKERS
            
            response = requests.post(
                f"{self.valves.WHISPERX_SERVICE_URL}/transcribe",
                files=files_payload,
                params=params,
                timeout=300  # 5 minute timeout for long audio
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Format transcript for the agent
            transcript_text = result["diarized_text"]
            
            # Add transcript as a system message for context
            messages = body.get("messages", [])
            messages.append({
                "role": "assistant",
                "content": f"I've transcribed the audio file. Here's the transcript with speaker labels:\n\n{transcript_text}\n\nHow would you like me to help you create a process workflow diagram from this?"
            })
            
            return {"messages": messages}
        
        except requests.exceptions.RequestException as e:
            return {
                "messages": body.get("messages", []) + [{
                    "role": "assistant",
                    "content": f"Error transcribing audio: {str(e)}\n\nPlease check that the WhisperX service is running at {self.valves.WHISPERX_SERVICE_URL}"
                }]
            }
        except Exception as e:
            return {
                "messages": body.get("messages", []) + [{
                    "role": "assistant",
                    "content": f"Unexpected error: {str(e)}"
                }]
            }
