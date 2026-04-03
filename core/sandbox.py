import os
import subprocess
import json
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger("uvicorn")

class Sandbox:
    """
    ARKANIS SANDBOX: Manages isolated execution of code and tools.
    Currently defaults to restricted subprocess execution, but is 
    prepared for Docker integration.
    """
    
    def __init__(self, use_docker: bool = False):
        self.use_docker = use_docker
        self.docker_image = "python:3.11-slim"
        self._check_docker()

    def _check_docker(self):
        if self.use_docker:
            try:
                subprocess.run(["docker", "--version"], capture_output=True, check=True)
            except Exception:
                logger.warning("Docker requested for Sandbox but not found. Falling back to Restricted Subprocess.")
                self.use_docker = False

    def run(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Runs a command in the sandbox and returns output."""
        if self.use_docker:
            return self._run_docker(command, timeout)
        else:
            return self._run_restricted(command, timeout)

    def _run_docker(self, command: str, timeout: int) -> Dict[str, Any]:
        """Executes in a transient Docker container."""
        # Note: In a real implementation, we'd mount specific volumes
        try:
            cmd = ["docker", "run", "--rm", "--network", "none", self.docker_image, "sh", "-c", command]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "environment": "docker"
            }
        except Exception as e:
            return {"error": f"Docker execution failed: {str(e)}", "environment": "docker"}

    def _run_restricted(self, command: str, timeout: int) -> Dict[str, Any]:
        """Executes using subprocess with restricted ENV and paths."""
        # Only allow specific ENVs to avoid leaking secrets
        safe_env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/tmp",
            "PYTHONPATH": os.getcwd()
        }
        
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                env=safe_env,
                cwd="/tmp" # Start in a safe dir
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "environment": "restricted_subprocess"
            }
        except subprocess.TimeoutExpired:
            return {"error": "Execution timed out.", "environment": "restricted_subprocess"}
        except Exception as e:
            return {"error": str(e), "environment": "restricted_subprocess"}

# Singleton instance
sandbox = Sandbox()
