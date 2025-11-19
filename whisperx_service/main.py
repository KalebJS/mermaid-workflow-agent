"""
WhisperX Transcription & Diarization Service
FastAPI service for processing audio files with speaker diarization
"""
import os
import tempfile
from pathlib import Path
from typing import Optional

import whisperx
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="WhisperX Diarization Service")

# Configuration from environment variables
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
DEVICE = os.getenv("DEVICE", "cpu")  # "cuda" for GPU
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8")  # "float16" for GPU
HF_TOKEN = os.getenv("HF_TOKEN")  # Required for diarization


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


class TranscriptResponse(BaseModel):
    segments: list[TranscriptSegment]
    full_text: str
    diarized_text: str


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model": WHISPER_MODEL}


@app.post("/transcribe", response_model=TranscriptResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    enable_diarization: bool = True,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
):
    """
    Transcribe and diarize audio file
    
    Args:
        audio: Audio file (mp3, wav, m4a, etc.)
        enable_diarization: Whether to perform speaker diarization
        min_speakers: Minimum number of speakers (optional)
        max_speakers: Maximum number of speakers (optional)
    """
    if enable_diarization and not HF_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="HF_TOKEN required for diarization. Set it in environment variables."
        )
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(audio.filename).suffix) as tmp_file:
        content = await audio.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Load audio
        audio = whisperx.load_audio(tmp_path)
        
        # Transcribe with Whisper
        model = whisperx.load_model(WHISPER_MODEL, DEVICE, compute_type=COMPUTE_TYPE)
        result = model.transcribe(audio, batch_size=16)
        
        # Align whisper output
        model_a, metadata = whisperx.load_align_model(
            language_code=result["language"],
            device=DEVICE
        )
        result = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio,
            DEVICE,
            return_char_alignments=False
        )
        
        # Diarize if enabled
        if enable_diarization and HF_TOKEN:
            diarize_model = whisperx.DiarizationPipeline(
                use_auth_token=HF_TOKEN,
                device=DEVICE
            )
            diarize_segments = diarize_model(
                audio,
                min_speakers=min_speakers,
                max_speakers=max_speakers
            )
            result = whisperx.assign_word_speakers(diarize_segments, result)
        
        # Format response
        segments = []
        full_text_parts = []
        diarized_text_parts = []
        
        for segment in result["segments"]:
            speaker = segment.get("speaker", "UNKNOWN")
            text = segment["text"].strip()
            
            segments.append(TranscriptSegment(
                start=segment["start"],
                end=segment["end"],
                text=text,
                speaker=speaker if enable_diarization else None
            ))
            
            full_text_parts.append(text)
            
            if enable_diarization:
                diarized_text_parts.append(f"[{speaker}]: {text}")
            else:
                diarized_text_parts.append(text)
        
        return TranscriptResponse(
            segments=segments,
            full_text=" ".join(full_text_parts),
            diarized_text="\n".join(diarized_text_parts)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
