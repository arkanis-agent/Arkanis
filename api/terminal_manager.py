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
import signal

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
        self.running = True
        self._lock = threading.Lock()

    def start(self, shell="/bin/bash"):
        """Inicializa novo shell em PTY com grupo de processo seguro."""
        with self._lock:
            if self.running:
                logger.warning("Terminal already running")
                return

        self.running = True
        self.pid, self.fd = pty.fork()

        if self.pid == 0:  # Child process
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env["COLUMNS"] = "80"
            env["LINES"] = "24"

            try:
                os.execvpe(shell, [shell], env)
            except Exception as e:
                logger.error(f"Exec failed: {e}")
                os._exit(1)
        else:  # Parent process
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            logger.info(f"Nerve: Terminal process started (PID {self.pid})")

    def _read_loop(self):
        """Monitor terminal output and pipe it to front-end via callback."""
        while True:
            with self._lock:
                if not self.running or self.fd is None:
                    break

            try:
                if not self._fd_is_valid():
                    break

                r, _, _ = select.select([self.fd], [], [], 0.1)
                if self.fd in r:
                    data = os.read(self.fd, 1024)
                    if not data:
                        with self._lock:
                            self.running = False
                        break
                    try:
                        self.on_output(data)
                    except Exception as e:
                        logger.error(f"Nerve: Callback error: {e}")
            except OSError:
                with self._lock:
                    self.running = False
                break
            except Exception as e:
                logger.error(f"Nerve: Read error: {e}")
                with self._lock:
                    self.running = False
                break

    def _fd_is_valid(self) -> bool:
        """Verifica se FD está ainda ativo sem bloquear."""
        try:
            fcntl.fcntl(self.fd, fcntl.F_GETFD)
            return True
        except OSError:
            return False

    def write(self, data: str) -> bool:
        """Write user input to the terminal with encoding safety."""
        with self._lock:
            if self.fd is None or not self.running:
                return False

        try:
            os.write(self.fd, data.encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"Nerve: Write error: {e}")
            return False

    def resize(self, rows: int, cols: int) -> bool:
        """Adjust terminal window size with input validation."""
        with self._lock:
            if self.fd is None or not self.running:
                return False

        if rows is None or cols is None:
            rows, cols = 24, 80

        rows = max(1, int(rows))
        cols = max(1, int(cols))

        try:
            s = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, s)
            return True
        except Exception as e:
            logger.error(f"Nerve: Resize error: {e}")
            return False

    def stop(self):
        """Cleanup terminal process with graceful shutdown."""
        self.running = False

        with self._lock:
            if self.fd is not None:
                try:
                    if self._fd_is_valid():
                        os.close(self.fd)
                except OSError:
                    pass
                finally:
                    self.fd = None
            pid = self.pid

        if pid is not None:
            try:
                # Tentativa 1: SIGTERM (graceful)
                os.kill(pid, signal.SIGTERM)
                import time
                time.sleep(1)

                # Tentativa 2: SIGKILL se não encerrou
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass

        self.thread = None
        logger.info("Nerve: Terminal process terminated.")
