import os
import pty
import subprocess
import threading
import select
import termios
import struct
import fcntl
from typing import Callable
from core.logger import logger

class TerminalManager:
    """
    ARKANIS NERVE - Terminal Fusion Manager
    Manages a pseudo-terminal (PTY) process and bridges it to WebSockets.
    """
    
    def __init__(self, on_output: Callable[[bytes], None]):
        self.on_output = on_output
        self.fd = None
        self.pid = None
        self.thread = None
        self.running = False

    def start(self, shell="/bin/bash"):
        """Starts a new shell in a PTY."""
        if self.running:
            return
            
        self.pid, self.fd = pty.fork()
        
        if self.pid == 0: # Child process
            # Set environment variables
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env["COLUMNS"] = "80"
            env["LINES"] = "24"
            
            os.execvpe(shell, [shell], env)
        else: # Parent process
            self.running = True
            logger.info(f"Nerve: Terminal process started (PID {self.pid})")
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()

    def _read_loop(self):
        """Monitor terminal output and pipe it to front-end via callback."""
        while self.running:
            try:
                r, w, e = select.select([self.fd], [], [], 0.1)
                if self.fd in r:
                    data = os.read(self.fd, 1024)
                    if not data:
                        self.stop()
                        break
                    self.on_output(data)
            except Exception as e:
                logger.error(f"Nerve: Read error: {e}")
                self.stop()
                break

    def write(self, data: str):
        """Write user input to the terminal."""
        if self.fd:
            os.write(self.fd, data.encode())

    def resize(self, rows: int, cols: int):
        """Adjust terminal window size."""
        if self.fd:
            s = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, s)

    def stop(self):
        """Cleanup terminal process."""
        self.running = False
        if self.fd:
            os.close(self.fd)
            self.fd = None
        if self.pid:
            try:
                os.kill(self.pid, 9)
            except:
                pass
            self.pid = None
        logger.info("Nerve: Terminal process terminated.")
