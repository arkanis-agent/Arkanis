import os
import subprocess
import json
import uuid
import asyncio
import logging
import time
from typing import Dict, Any
from tools.base_tool import BaseTool
from tools.registry import registry

logger = logging.getLogger("uvicorn")

class SpeechToTextTool(BaseTool):
    """
    ARKANIS V3.1 - Speech-to-Text Tool
    Integrates with whisper.cpp to transcribe local audio files.
    Requires: ffmpeg and whisper.cpp binary.
    """
    
    def __init__(self):
        super().__init__()
        # Determine paths relative to project root
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.binary_path = os.path.join(app_root, "libs", "whisper.cpp", "build", "bin", "whisper-cli")
        self.model_path = os.path.join(app_root, "libs", "whisper.cpp", "models", "ggml-base.bin")

    @property
    def name(self) -> str:
        return "speech_to_text"

    @property
    def description(self) -> str:
        return "Transcribes an audio file (wav, mp3, ogg, m4a) to text using local whisper.cpp."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "temp_input": "Path to the temporary audio file to transcribe."
        }

    def execute(self, **kwargs) -> str:
        """
        Standard sync wrapper for tool registry compatibility.
        Ensures execution works even if called from within another event loop.
        """
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We are inside an active loop (common in FastAPI/Telegram)
                # We must run the async task in a way that doesn't block or conflict.
                import threading
                from concurrent.futures import ThreadPoolExecutor
                
                def _run_sync():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self.execute_async(**kwargs))
                    finally:
                        new_loop.close()

                with ThreadPoolExecutor() as executor:
                    future = executor.submit(_run_sync)
                    return json.dumps(future.result())
            else:
                # No loop running, safe to use asyncio.run
                return json.dumps(asyncio.run(self.execute_async(**kwargs)))
        except Exception as e:
            logger.error(f"Critical STT Execution Error: {str(e)}")
            return json.dumps({"error": f"Erro crítico na execução: {str(e)}", "status": "failed"})

    async def execute_async(self, **kwargs) -> Dict[str, Any]:
        """Async execution with robust logging and error handling."""
        temp_input = kwargs.get("temp_input") or kwargs.get("audio_path")
        if not temp_input:
            return {"error": "Missing input file path.", "status": "failed"}

        start_time = time.time()
        temp_wav = temp_input + ".converted.wav"
        
        try:
            # 0. Pre-flight checks
            if not os.path.exists(temp_input):
                return {"error": f"Arquivo de entrada não encontrado: {temp_input}", "status": "failed"}

            if not os.path.exists(self.binary_path):
                return {"error": "Subsistema Whisper não encontrado. Reinstale as dependências.", "status": "failed"}

            # 1. Convert to 16kHz WAV Mono (Whisper Requirement)
            conv_process = await asyncio.create_subprocess_exec(
                'ffmpeg', '-y', '-i', temp_input,
                '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le',
                temp_wav,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await conv_process.communicate()
            
            if conv_process.returncode != 0:
                err_msg = stderr.decode().strip()
                logger.error(f"FFMPEG Error: {err_msg}")
                return {"error": f"Erro na conversão de áudio: {err_msg[:100]}", "status": "failed"}

            # 2. Transcribe with whisper.cpp
            if not os.path.exists(self.model_path):
                return {"error": f"Modelo Whisper não encontrado em {self.model_path}", "status": "failed"}
                
            threads = os.cpu_count() or 4
            # Correct paths for whisper.cpp shared libraries found in libs/whisper.cpp/build/
            build_path = os.path.dirname(os.path.dirname(self.binary_path))
            
            # Setup environment with local library paths
            env = os.environ.copy()
            env["LD_LIBRARY_PATH"] = build_path + (f":{env.get('LD_LIBRARY_PATH', '')}" if env.get('LD_LIBRARY_PATH') else "")
            
            whisper_process = await asyncio.create_subprocess_exec(
                self.binary_path, 
                '-m', self.model_path,
                '-f', temp_wav,
                '-nt', # No timestamps
                '-t', str(threads),
                '-l', 'pt', # Force Portuguese for STT stability
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            w_stdout, w_stderr = await whisper_process.communicate()
            
            if whisper_process.returncode != 0:
                err_msg = w_stderr.decode().strip()
                logger.error(f"Whisper Error: {err_msg}")
                return {"error": f"Erro na transcrição: {err_msg[:100]}", "status": "failed"}

            transcription = w_stdout.decode().strip()
            
            # 3. Clean up VAD artifacts / system noises
            clean_text = transcription.replace("[BLANK_AUDIO]", "").replace("[SILENCE]", "").strip()
            
            duration = time.time() - start_time
            return {
                "text": clean_text,
                "status": "success",
                "metrics": {
                    "duration": round(duration, 2),
                    "model": "whisper-base-cpp",
                    "threads": threads
                }
            }

        except Exception as e:
            logger.error(f"STT Tool Exception: {str(e)}")
            return {"error": str(e), "status": "failed"}
        finally:
            # Cleanup only the converted wav
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except:
                    pass

# Auto-registration
registry.register(SpeechToTextTool())
