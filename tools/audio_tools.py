import os
import subprocess
import json
import uuid
import asyncio
import logging
import time
import threading
import queue
import shlex
from pathlib import Path
from typing import Dict, Any, Optional
from tools.base_tool import BaseTool
from tools.registry import registry
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("uvicorn")

# Configurações ajustáveis via ambiente
def _get_audio_workers() -> int:
    return int(os.environ.get("AUDIO_WORKERS", "4"))

def _get_whisper_threads() -> int:
    threads = int(os.environ.get("WHISPER_THREADS", "2"))
    return min(threads, os.cpu_count() or 4)

AUDIO_EXECUTOR = ThreadPoolExecutor(max_workers=_get_audio_workers(), thread_name_prefix="audio_task")

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".webm"}

class SpeechToTextTool(BaseTool):
    """
    ARKANIS V3.1 - Speech-to-Text Tool
    Integrates with whisper.cpp to transcribe local audio files.
    Requires: ffmpeg and whisper.cpp binary.
    """
    
    def __init__(self):
        super().__init__()
        self._app_root = Path(__file__).resolve().parent.parent.parent
        self._tmp_root = self._app_root / "tmp"
        self.binary_path = self._app_root / "libs" / "whisper.cpp" / "build" / "bin" / "whisper-cli"
        self.model_path = self._app_root / "libs" / "whisper.cpp" / "models" / "ggml-base.bin"
        self.process_timeout = int(os.environ.get("AUDIO_PROCESS_TIMEOUT", "300"))

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
    
    def _validate_path(self, path: str) -> Optional[Path]:
        """Security: Validate path does not escape allowed directories."""
        try:
            validated = Path(path).resolve()
            root_prefix = self._tmp_root
            
            if not str(validated).startswith(str(root_prefix)): 
                logger.warning(f"Path traversal attempt: {path}")
                return None
            
            return validated
        except (ValueError, TypeError):
            return None
    
    def _validate_extension(self, path: Path) -> bool:
        return path.suffix.lower() in ALLOWED_EXTENSIONS
    
    def execute(self, **kwargs) -> str:
        """
        Standard sync wrapper for tool registry compatibility.
        Uses thread pool to prevent blocking the event loop.
        """
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return json.dumps(asyncio.run(self.execute_async(**kwargs)))
            
            result = loop.run_in_executor(AUDIO_EXECUTOR, self._execute_sync, **kwargs)
            return json.dumps(asyncio.new_event_loop().run_until_complete(result))
        except Exception as e:
            logger.error(f"Critical STT Execution Error")
            return json.dumps({"error": "Erro crítico na execução", "status": "failed"})
    
    def _execute_sync(self, **kwargs) -> str:
        return json.dumps(asyncio.run(self.execute_async(**kwargs)))

    async def execute_async(self, **kwargs) -> Dict[str, Any]:
        """Async execution with robust logging and error handling."""
        temp_input = kwargs.get("temp_input") or kwargs.get("audio_path")
        
        if not temp_input:
            return {"error": "Missing input file path", "status": "failed"}
        
        input_path = self._validate_path(str(temp_input))
        if not input_path or not input_path.exists():
            return {"error": "Arquivo de entrada não encontrado", "status": "failed"}
        
        if not self._validate_extension(input_path):
            return {"error": "Formato de arquivo não suportado", "status": "failed"}

        unique_id = str(uuid.uuid4())[:12]
        temp_wav = input_path.parent / f"{input_path.stem}_{unique_id}_converted.wav"

        start_time = time.time()

        try:
            if not self.binary_path.exists():
                return {"error": "Subsistema Whisper não encontrado", "status": "failed"}

            if not self.model_path.exists():
                return {"error": "Modelo Whisper não encontrado", "status": "failed"}

            # 1. Convert to 16kHz WAV Mono
            conv_process = await asyncio.create_subprocess_exec(
                'ffmpeg',
                '-y',
                '-i', input_path,
                '-ar', '16000',
                '-ac', '1',
                '-c:a', 'pcm_s16le',
                temp_wav,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                timeout=self.process_timeout
            )
            try:
                stdout, stderr = await conv_process.communicate()
            except asyncio.TimeoutError:
                conv_process.kill()
                return {"error": "Timeout na conversão de áudio", "status": "failed"}

            if conv_process.returncode != 0:
                return {"error": "Erro na conversão de áudio", "status": "failed"}

            # 2. Transcribe with whisper.cpp
            threads = _get_whisper_threads()
            build_path = self.binary_path.parent.parent
            src_path = build_path / "src"
            ggml_src_path = build_path / "ggml" / "src"
            env = os.environ.copy()
            new_ld = f"{src_path}:{ggml_src_path}"
            existing_ld = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = new_ld + (f":{existing_ld}" if existing_ld else "")
            
            whisper_process = await asyncio.create_subprocess_exec(
                shlex.split(str(self.binary_path)),
                '-m', str(self.model_path),
                '-f', str(temp_wav),
                '-nt',
                '-t', str(threads),
                '-l', 'pt',
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                timeout=self.process_timeout
            )
            try:
                w_stdout, w_stderr = await whisper_process.communicate()
            except asyncio.TimeoutError:
                whisper_process.kill()
                return {"error": "Timeout na transcrição", "status": "failed"}

            transcription = w_stdout.decode().strip()
            clean_text = transcription.replace("[BLANK_AUDIO]", "").replace("[SILENCE]", "").strip()
            
            return {
                "text": clean_text,
                "status": "success",
                "metrics": {
                    "duration": round(time.time() - start_time, 2),
                    "model": "whisper-base-cpp",
                    "threads": threads,
                    "file_id": unique_id
                }
            }

        except Exception as e:
            logger.error(f"STT Tool Exception")
            return {"error": "Erro na execução", "status": "failed"}
        
        finally:
            if temp_wav.exists():
                try:
                    temp_wav.unlink()
                except Exception:
                    pass