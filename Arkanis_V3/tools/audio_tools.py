import os
import subprocess
import json
import uuid
import asyncio
from typing import Dict
from tools.base_tool import BaseTool
from tools.registry import registry

class SpeechToTextTool(BaseTool):
    """
    ARKANIS V3.1 - Speech-to-Text Tool
    Integrates with whisper.cpp to transcribe local audio files.
    Requires: ffmpeg and whisper.cpp binary.
    """
    
    @property
    def name(self) -> str:
        return "speech_to_text"

    @property
    def description(self) -> str:
        return "Transcribes an audio file (wav, mp3, ogg, m4a) to text using local whisper.cpp."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "audio_path": "Path to the audio file to transcribe."
        }

    def execute(self, **kwargs) -> str:
        # Standard sync wrapper for tool registry compatibility if needed
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we are in an async loop (FastAPI), we should really be using the async method.
                # But for registry.execute compatibility, we provide this.
                return asyncio.run_coroutine_threadsafe(self.execute_async(**kwargs), loop).result()
            else:
                return asyncio.run(self.execute_async(**kwargs))
        except RuntimeError:
            return asyncio.run(self.execute_async(**kwargs))

    async def execute_async(self, **kwargs) -> str:
        audio_path = kwargs.get("audio_path")
        if not audio_path:
            return json.dumps({"error": "Missing audio_path argument."})

        if not os.path.exists(audio_path):
            return json.dumps({"error": f"Audio file not found at {audio_path}"})

        # 1. Setup paths
        v3_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        whisper_bin = os.path.join(v3_dir, "libs", "whisper.cpp", "build", "bin", "whisper-cli")
        whisper_model = os.path.join(v3_dir, "libs", "whisper.cpp", "models", "ggml-base.bin")
        
        if not os.path.exists(whisper_bin):
            return json.dumps({
                "error": "whisper.cpp not found. Please run V3/scripts/install_whisper.sh first."
            })

        # 2. Performance Optimization: Detect CPU threads
        threads = os.cpu_count() or 1

        # 3. Convert audio to 16kHz WAV asynchronously
        tmp_wav = os.path.join(os.path.dirname(audio_path), f"tmp_{uuid.uuid4().hex}.wav")
        try:
            conv_cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                tmp_wav
            ]
            process = await asyncio.create_subprocess_exec(
                *conv_cmd, 
                stdout=asyncio.subprocess.DEVNULL, 
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.wait()
            if process.returncode != 0:
                raise Exception(f"FFmpeg returned exit code {process.returncode}")

        except Exception as e:
            return json.dumps({"error": f"Failed to convert audio via ffmpeg: {str(e)}"})

        # 4. Transcribe via whisper.cpp asynchronously
        try:
            # -nt: no timestamps
            # -t N: thread count
            whisper_cmd = [
                whisper_bin,
                "-m", whisper_model,
                "-f", tmp_wav,
                "-nt",
                "-t", str(threads)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *whisper_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"Whisper failed (Code {process.returncode}): {stderr.decode()}")

            transcription = stdout.decode().strip()
            
            if os.path.exists(tmp_wav):
                os.remove(tmp_wav)

            return json.dumps({
                "text": transcription,
                "status": "success",
                "audio_source": audio_path,
                "metrics": {
                    "threads": threads,
                    "vad_enabled": False
                }
            })

        except Exception as e:
            if os.path.exists(tmp_wav):
                os.remove(tmp_wav)
            return json.dumps({"error": f"Whisper transcription failed: {str(e)}"})

# Auto-registration
registry.register(SpeechToTextTool())
