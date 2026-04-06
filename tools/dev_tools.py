import os
import subprocess
import json
import logging
import re
from typing import Dict, Any, List, Optional
from tools.base_tool import BaseTool
from tools.registry import registry
from core.agent_bus import agent_bus
from core.sandbox import sandbox

logger = logging.getLogger(__name__)

# Whitelist for allowed paths
ALLOWED_PATHS = ['/home/diego/Área de trabalho/Arkanis_V3.1']
DENIED_PATHS = ['/etc/', '/root/', '/proc/', '/sys/', '/bin', '/sbin', '/usr/bin', '/usr/sbin']

def is_safe_command(command: str) -> bool:
    """Security check to block dangerous shell commands."""
    blocked_patterns = [
        "rm -rf /", "rm -rf .", "rm -rf *",
        "mkfs", "dd if=", "shred", "shutdown", "reboot",
        "> /dev/", ":(){ :|: & };:", "chmod -R 777",
        "chown", "passwd", "mount", "umount"
    ]
    for pattern in blocked_patterns:
        if pattern in command:
            return False
    # Check for dangerous redirects and pipes
    if re.search(r\"[>|;]&\", command):
        return False
    return True

def validate_path(path: str) -> bool:
    """Validate that path is within allowed directories."""
    for denied in DENIED_PATHS:
        if path.startswith(denied) or f\"/{denended}\" in path:
            return False
    for allowed in ALLOWED_PATHS:
        if allowed in path:
            return True
    return False

class ShellExecTool(BaseTool):
    """A tool to execute safe shell commands."""
    @property
    def name(self) -> str: return "shell_exec"
    @property
    def description(self) -> str:
        return "Executes a shell command and returns output. Allowed: ls, ldd, file, cat, grep, pip, python, which, ffmpeg, ps, df, etc."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"command": "The shell command to execute."}
    
    def execute(self, **kwargs) -> str:
        cmd = kwargs.get("command")
        if not cmd: return "Error: No command provided."
        
        if not is_safe_command(cmd):
            return "Error: Command rejected for security reasons."
        
        # Validate command doesn't try path traversal in arguments
        if '..' in cmd or any(path in cmd for path in DENIED_PATHS):
            return "Error: Command rejected - suspicious path detected."
            
        try:
            timeout = int(kwargs.get("timeout", 30))
            result = sandbox.run(cmd, timeout=timeout)
            
            agent_bus.broadcast_message("system", f"[DEV_TOOL/SANDBOX] Command executed: {cmd[:50]}...")
            return json.dumps(result)
        except Exception as e:
            return f"Error executing command: {str(e)}"

class ReadFileLinesTool(BaseTool):
    """Reads specific range of lines from a file."""
    @property
    def name(self) -> str: return "read_file_lines"
    @property
    def description(self) -> str: return "Reads a specific range of lines from a file. Useful for large logs."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "Path to file", "start": "Start line (1-indexed)", "count": "Number of lines to read"}
    
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        if not path or not validate_path(path):
            return "Error: Invalid path - outside allowed directories."
        
        if not os.path.exists(path): return f"Error: File {path} not found."
        
        try:
            start = int(kwargs.get("start", 1))
            count = int(kwargs.get("count", 50))
            
            # Validate numeric parameters
            if start < 1 or count < 1:
                return "Error: Invalid line parameters."
                
            if start > 1000000 or count > 1000000:
                return "Error: Line parameters exceed maximum safe limits."
                
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                selected = lines[max(0, start-1) : start-1+count]
                return "".join(selected)
        except Exception as e:
            return f"Error reading lines: {str(e)}"

class GrepInFileTool(BaseTool):
    """Search for a pattern in a file."""
    @property
    def name(self) -> str: return "grep_in_file"
    @property
    def description(self) -> str: return "Searches for a text pattern in a file and returns matching lines."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "Path to file", "pattern": "Text to search for"}
    
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        pattern = kwargs.get("pattern")
        
        if not path or not validate_path(path):
            return "Error: Invalid path - outside allowed directories."
        if not path or not pattern: return "Error: Missing path or pattern."
        
        # Validate pattern length to prevent DoS
        if len(pattern) > 500:
            return "Error: Pattern too long."
        
        try:
            matches = []
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if pattern in line:
                        matches.append(f"{i}: {line.strip()}")
                        if len(matches) >= 1000:  # Limit results
                            matches.append("... (truncated, max 1000 matches)")
                            break
            return json.dumps(matches) if matches else "No matches found."
        except Exception as e:
            return f"Error searching file: {str(e)}"

class CheckBinaryTool(BaseTool):
    """Check binary dependencies and properties."""
    @property
    def name(self) -> str: return "check_binary"
    @property
    def description(self) -> str: return "Checks binary existence, type, and shared library dependencies (ldd)."
    @property
    def arguments(self) -> Dict[str, str]:
        return {"binary_path": "Path to the executable binary."}
    
    def execute(self, **kwargs) -> str:
        path = kwargs.get("binary_path")
        
        if not path or not validate_path(path):
            return "Error: Invalid path - outside allowed directories."
        
        if not path: return "Error: No path provided."
        
        report = {"exists": os.path.exists(path)}
        if not report["exists"]: return json.dumps(report)
        
        try:
            f_info = subprocess.run(["file", path], capture_output=True, text=True)
            report["file_info"] = f_info.stdout.strip()
            
            ldd_info = subprocess.run(["ldd", path], capture_output=True, text=True)
            report["dependencies"] = ldd_info.stdout
            report["missing_libs"] = "not found" in ldd_info.stdout
            
            return json.dumps(report)
        except Exception as e:
            return f"Error checking binary: {str(e)}"

class PatchFileLineTool(BaseTool):
    """Replace a specific line in a file."""
    @property
    def name(self) -> str: return "patch_file_line"
    @property
    def description(self) -> str: return "Replaces a specific line number in a file with new content.""
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "Path to file", "line_number": "Line to replace (1-indexed)", "new_content": "New line text"}
    
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        
        if not path or not validate_path(path):
            return "Error: Invalid path - outside allowed directories."
        
        line_num = kwargs.get("line_number")
        if line_num:
            try:
                line_num = int(line_num)
            except ValueError:
                return "Error: line_number must be an integer."
        else:
            return "Error: Missing line_number parameter."
        
        new_content = kwargs.get("new_content")
        
        if not path or not line_num or new_content is None: return "Error: Missing parameters."
        
        if len(new_content) > 10000:
            return "Error: new_content too long."
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if 1 <= line_num <= len(lines):
                lines[line_num - 1] = new_content + "\n"
                with open(path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                agent_bus.broadcast_message("system", f"[DEV_TOOL] Patched file {path} at line {line_num}")
                return f"Successfully patched line {line_num} in {path}."
            else:
                return f"Error: Line number {line_num} out of range (1-{len(lines)})."
        except Exception as e:
            return f"Error patching file: {str(e)}"

class InstallPythonPackageTool(BaseTool):
    """Install a python package via pip."""
    @property
    def name(self) -> str: return "install_python_package"
    @property
    def description(self) -> str: return "Installs a Python package using pip.""
    @property
    def arguments(self) -> Dict[str, str]:
        return {"package": "Package name to install (e.g. 'requests==2.31.0')"}
    
    def execute(self, **kwargs) -> str:
        pkg = kwargs.get("package")
        
        # Validate package name format to prevent injection
        if pkg and not re.match(r"^\w([\w.-]*\w)?$", pkg.split('==')[0].split('>=')[0].split('<=')[0]) if pkg else False:
            return "Error: Invalid package name format."
        
        if not pkg: return "Error: No package name provided."
        
        try:
            pip_cmd = [os.sys.executable, "-m", "pip", "install", pkg]
            result = subprocess.run(pip_cmd, capture_output=True, text=True)
            return json.dumps({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            })
        except Exception as e:
            return f"Error installing package: {str(e)}"

class GetProcessInfoTool(BaseTool):
    """Get info about running processes."""
    @property
    def name(self) -> str: return "get_process_info"
    @property
    def description(self) -> str: return "Returns a list of active processes matching a name pattern.""
    @property
    def arguments(self) -> Dict[str, str]:
        return {"pattern": "Process name or pattern to search for."}
    
    def execute(self, **kwargs) -> str:
        pattern = kwargs.get("pattern", "")
        
        # CRITICAL FIX: Avoid shell=True - use subprocess properly
        # Only allow safe character patterns (alphanumeric, space, dash, underscore)
        if pattern and not re.match(r"^[a-zA-Z0-9_\- ]+$", pattern):
            return "Error: Invalid pattern - contains unsafe characters."
        
        try:
            cmd = ["ps", "aux"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            processes = result.stdout.split('\n')
            
            if pattern:
                processes = [p for p in processes if pattern.lower() in p.lower()]
                
            if not processes or (len(processes) == 1 and not processes[0].strip()):
                return "No matching processes found."
                
            return "\n".join(processes)
        except Exception as e:
            return f"Error getting process info: {str(e)}"

class WriteFullFileTool(BaseTool):
    """Overwrites an entire file with new content."""
    @property
    def name(self) -> str: return "write_full_file"
    @property
    def description(self) -> str: return "Overwrites an entire file with the provided content. USE WITH EXTREME CARE.""
    @property
    def arguments(self) -> Dict[str, str]:
        return {"path": "Path to file", "content": "New content for the file"}
    
    def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        content = kwargs.get("content")
        
        if not path or not validate_path(path):
            return "Error: Invalid path - outside allowed directories."
        if not path or content is None: return "Error: Missing path or content."
        
        # Prevent dangerous overwrites
        if path.endswith('.bak') or '/tmp/' in path:
            return "Error: Writing to backup or temp directories is not allowed."
        
        try:
            # Backup before overwrite
            backup_path = path + ".bak"
            if os.path.exists(path):
                import shutil
                shutil.copy2(path, backup_path)
                
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content[:100000])  # Limit content size
            
            agent_bus.broadcast_message("system", f"[DEV_TOOL] File overwritten: {path}")
            return f"Successfully wrote {len(content)} characters to {path}."
        except Exception as e:
            return f"Error writing file: {str(e)}"

# Registration
registry.register(ShellExecTool())
registry.register(ReadFileLinesTool())
registry.register(GrepInFileTool())
registry.register(CheckBinaryTool())
registry.register(PatchFileLineTool())
registry.register(InstallPythonPackageTool())
registry.register(GetProcessInfoTool())
registry.register(WriteFullFileTool())