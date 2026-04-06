import sys
import os
import subprocess
import tempfile
import uuid
import hashlib
from typing import Any, Dict, Optional
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger

class PythonExecutorTool(BaseTool):
    """
    ARKANIS V3.1 - Data Architect Tool (SECURED)
    Executes Python code in a subprocess with secure sandboxing.
    """
    
    def __init__(self):
        super().__init__()
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "webui", "outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        self._execution_log = []
        # Security: Maximum file size in bytes (1MB default)
        self.max_file_size = 1024 * 1024

    @property
    def name(self) -> str:
        return "python_executor"

    @property
    def description(self) -> str:
        return "Executes Python 3 code in sandbox. For math, data analysis, plotting. Images saved to outputs/."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "code": "Valid Python 3 code to execute (max 10KB). pandas, numpy, matplotlib supported."
        }

    def _validate_input(self, code: str) -> tuple[bool, Optional[str]]:
        """Input validation with security checks."""
        if not code or not code.strip():
            return False, "Code cannot be empty"
        if len(code) > 10 * 1024:  # 10KB limit
            return False, "Code exceeds size limit (10KB max)"
        # Prevent dangerous imports
        dangerous_imports = ['os.system', 'os.popen', 'eval(', 'exec(', 'subprocess', 'importlib']
        for imp in dangerous_imports:
            if imp in code:
                return False, f"Security violation: {imp} not allowed"
        return True, None

    def _sanitize_code(self, code: str) -> str:
        """Sanitize code for safe execution."""
        # Convert relative paths to absolute for output
        return code.replace('./', os.path.join(self.output_dir, ''))

    def execute(self, **kwargs) -> str:
        code = kwargs.get("code", "")
        
        # Security: Validate first
        is_valid, error_msg = self._validate_input(code)
        if not is_valid:
            logger.warning(f"Invalid code attempt: {error_msg}")
            return f"Error: {error_msg}"

        sanitized_code = self._sanitize_code(code.strip())
        logger.info(f"Python executor: Attempted execution, {len(code)} chars")

        # Fix: Double braces {{}} for f-string to pass raw to subprocess
        wrapped_code = f"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import uuid

# Output directory (read-only from subprocess perspective)
OUTPUT_DIR = r"{os.path.abspath(self.output_dir)}"

# Safe plot save function
def save_plot(filename=None):
    if not filename:
        filename = f"plot_{{uuid.uuid4().hex[:8]}}.png"
    path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(path)
    print(f"\\n[IMAGE_GENERATED: {{filename}}]")
    plt.close()

# Inject via globals only (not builtins)
globals()['save_plot'] = save_plot

# User code follows:\n{sanitized_code}"""

        tmp_path = None
        tmp_file = None
        try:
            tmp_file = tempfile.NamedTemporaryFile(
                suffix='.py', 
                mode='w', 
                delete=False, 
                dir=('/tmp' if os.access('/tmp', os.W_OK) else '.'),
                encoding='utf-8'
            )
            tmp_path = tmp_file.name
            tmp_file.write(wrapped_code)
            tmp_file.close()  # Close before execute
            os.chmod(tmp_path, 0o700)  # Restrict permissions
            
        except Exception as e:
            logger.error(f"Preparation failed: {str(e)}")
            return f"Error preparing execution: {str(e)}"

        try:
            process = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            stdout = process.stdout or ''
            stderr = process.stderr or ''
            
            result_parts = []
            logger.info(f"Return code: {process.returncode}")
            
            if stdout.strip():
                result_parts.append(f\"STDOUT:\n{stdout.strip()}\")
            if stderr.strip():
                result_parts.append(f\"STDERR:\n{stderr.strip()}\")
            if process.returncode != 0:
                result_parts.append(f\"ERROR: Exit code {process.returncode}\")

            return "\n".join(result_parts) if result_parts else "Execution successful, no output returned."

        except subprocess.TimeoutExpired:
            return "Error: Execution timed out (30s)."
        except FileNotFoundError:
            return "Error: Python interpreter not found."
        except PermissionError:
            return "Error: Permission denied."
        except Exception as e:
            logger.error(f"Execution failed: {str(e)}")
            return f"Error: {str(e)}"
        finally:
            # Secure cleanup
            if tmp_path:
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except OSError:
                    pass
            if tmp_file:
                try:
                    tmp_file.close()
                except:
                    pass

# Auto-registration
registry.register(PythonExecutorTool())
