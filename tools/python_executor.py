import sys
import os
import subprocess
import tempfile
import uuid
from typing import Any, Dict
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger

class PythonExecutorTool(BaseTool):
    """
    ARKANIS V3.1 - Data Architect Tool
    Executes Python code in a subprocess, capturing output and generated images.
    Powerful for data analysis, math, and automation.
    """
    
    def __init__(self):
        super().__init__()
        # Ensure a directory for output images exists in the webui
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "webui", "outputs")
        os.makedirs(self.output_dir, exist_ok=True)

    @property
    def name(self) -> str:
        return "python_executor"

    @property
    def description(self) -> str:
        return "Executes Python 3 code. Use this for math, data analysis (pandas), and plotting (matplotlib). Images are saved to 'outputs/'."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "code": "The valid Python 3 code to execute. Standard libraries, pandas, and matplotlib are available."
        }

    def execute(self, **kwargs) -> str:
        code = kwargs.get("code")
        if not code:
            return "Error: No code provided."

        # 1. Prepare the execution script
        # We wrap it to handle matplotlib non-interactive backend automatically
        wrapped_code = f"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

# Redirect plots to the output directory
def save_plot(filename=None):
    if not filename:
        import uuid
        filename = f"plot_{{uuid.uuid4().hex[:8]}}.png"
    path = os.path.join(r"{self.output_dir}", filename)
    plt.savefig(path)
    print(f"\\n[IMAGE_GENERATED: {{filename}}]")
    plt.close()

# Inject the helper
import builtins
builtins.save_plot = save_plot

# User code follows:
{code}
"""
        
        # 2. Run in a temporary file
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
            tmp.write(wrapped_code)
            tmp_path = tmp.name

        try:
            process = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=30  # Safety timeout
            )
            
            stdout = process.stdout
            stderr = process.stderr
            
            result_output = []
            if stdout:
                result_output.append(f"STDOUT:\n{stdout}")
            if stderr:
                result_output.append(f"STDERR:\n{stderr}")
            if process.returncode != 0:
                result_output.append(f"Exit Code: {process.returncode}")

            if not result_output:
                return "Execution successful, no output returned."
                
            return "\n".join(result_output)

        except subprocess.TimeoutExpired:
            return "Error: Execution timed out (30s)."
        except Exception as e:
            return f"Error executing code: {str(e)}"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

# Auto-registration
registry.register(PythonExecutorTool())
