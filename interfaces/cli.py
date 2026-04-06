from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.traceback import install
import time
import os
import logging
import re
from collections import deque
from typing import List, Optional

# Configuração de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cores como constantes
colors = {
    'yellow': 'yellow',
    'red': 'red',
    'green': 'green',
    'blue': 'blue',
    'cyan': 'cyan',
    'white': 'white',
    'bold_cyan': 'bold cyan'
}

class ArkanisCLI:
    """
    Secure CLI Interface for Arkanis V3 with enhanced security and stability.
    """
    # Comandos permitidos na inicialização
    ALLOWED_COMMANDS = {'exit', 'sair', 'quit', 'help', 'history'}
    
    def __init__(self, agent, max_history: int = 100):
        self.console = Console()
        self.agent = agent
        self.command_history: deque = deque(maxlen=max_history)
        install()  # Enable rich traceback formatting

    def show_banner(self):
        """Displays the Arkanis V3 branding with improved formatting."""
        banner_text = """
    █▀▀█ █▀▀█ █ █ █▀▀█ █▀▀▄ ▀█▀ █▀▀
    █▄▄█ █▄▄▀ █▀▄ █▄▄█ █  █  █  ▀▀█
    ▀  ▀ ▀ ▀▀ ▀ ▀ ▀  ▀ ▀  ▀ ▀▀▀ ▀▀▀
    VERSION 3.1 - AI AGENT OPERATING SYSTEM
        """
        self.console.print(Panel(banner_text, style='bold cyan', subtitle='Control Kernel v3'))

    def show_help(self):
        """Displays registered tools with better organization."""
        table = Table(title='Available Tools')
        table.add_column('Tool Name', style='cyan', justify='left')
        table.add_column('Description', style='white', justify='left')
        
        try:
            from tools.registry import registry
            tools = registry.list_tools()
            for name, desc in sorted(tools.items()):
                display_desc = desc[:50] + '...' if len(desc) > 50 else desc
                table.add_row(name, display_desc)
        except ImportError:
            table.add_row('Registry', 'Unavailability - tools module not found')
            
        self.console.print(table)
        self.console.print('\n[bold blue]Commands:[/bold blue] help, history, exit')

    def show_history(self):
        """Displays command history."""
        if not self.command_history:
            self.console.print('[yellow]No command history found.[/yellow]')
            return
            
        table = Table(title='Command History')
        table.add_column('No.', style='cyan')
        table.add_column('Command', style='white')
        
        for idx, cmd in enumerate(self.command_history, 1):
            display_cmd = cmd[:45] + '...' if len(cmd) > 45 else cmd
            table.add_row(str(idx), display_cmd)
            
        self.console.print(table)

    def sanitize_input(self, user_input: str) -> str:
        """Sanitizes input to prevent command injection and control sequences."""
        if not user_input or not isinstance(user_input, str):
            return ''
        
        # Strip whitespace first
        user_input = user_input.strip()
        
        # Remove control characters that could enable command injection
        # Allow only alphanumeric spaces and common punctuation for safety
        safe_pattern = r'[a-zA-Z0-9\s@.#$%&_-]+'
        sanitized = re.findall(safe_pattern, user_input)
        
        return ' '.join(sanitized) if sanitized else ''

    def start_loop(self):
        """Main interaction loop for the CLI with proper error handling."""
        self.show_banner()
        self.console.print('[yellow]System online. Type help for tools or history for commands.[/yellow]')
        
        while True:
            try:
                user_input = Prompt.ask('[green]User[/green>')
                
                if not user_input or not user_input.strip():
                    continue
                    
                sanitized_input = self.sanitize_input(user_input)
                
                if not sanitized_input:
                    self.console.print('[yellow]Empty or invalid input.[/yellow]')
                    continue
                
                # Add to history (before checking commands)
                self.command_history.append(sanitized_input)
                
                # Command validation
                cmd_lower = sanitized_input.lower()
                
                if cmd_lower in self.ALLOWED_COMMANDS:
                    if cmd_lower in ['exit', 'sair', 'quit']:
                        self.console.print('\n[bold red]Shutting down ARKANIS V3...[/bold red]\n')
                        self.cleanup()
                        break
                    
                    if cmd_lower == 'help':
                        self.show_help()
                        continue
                    
                    if cmd_lower == 'history':
                        self.show_history()
                        continue
                
                # Show processing status for agent commands
                with Progress(SpinnerColumn(), TextColumn('[progress.description]{task.description}')) as progress:
                    task = progress.add_task('Processing request...', total=None)
                    
                try:
                    response = self.agent.handle_input(sanitized_input)
                except Exception as e:
                    logger.error(f'Agent Error: {str(e)}', exc_info=True)
                    response = f'
[red][Kernel Error] {str(e)}[/red]
'
                    
                progress.remove_task(task)
                    
                self.console.print(f'
[blue]ARKANIS FINAL REPORT[/blue]
{Panel(response, border_style='blue')}
')
                
            except KeyboardInterrupt:
                logger.warning('User interrupted with Ctrl+C')
                self.console.print('\n[bold red]Shutting down ARKANIS V3...[/bold red]\n')
                self.cleanup()
                break
            except Exception as e:
                logger.error(f'CLI Error: {str(e)}', exc_info=True)
                self.console.print(f'
[red]Unexpected error: {str(e)}[/red]\n')
                
    def cleanup(self):
        """Perform any necessary cleanup before shutdown."""
        try:
            logger.info('CLI cleanup initiated')
            self.console.print(f'[cyan]Session saved. History: {len(self.command_history)} commands.[/cyan]')
        except Exception as e:
            logger.error(f'Cleanup error: {e}')

