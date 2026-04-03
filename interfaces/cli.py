from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
import time
import os

class ArkanisCLI:
    """
    Standard CLI Interface for Arkanis V3.
    """
    def __init__(self, agent):
        self.console = Console()
        self.agent = agent

    def show_banner(self):
        """Displays the Arkanis V3 branding."""
        banner_text = """
    █▀▀█ █▀▀█ █ █ █▀▀█ █▀▀▄ ▀█▀ █▀▀
    █▄▄█ █▄▄▀ █▀▄ █▄▄█ █  █  █  ▀▀█
    ▀  ▀ ▀ ▀▀ ▀ ▀ ▀  ▀ ▀  ▀ ▀▀▀ ▀▀▀
    VERSION 3.1 - AI AGENT OPERATING SYSTEM
        """
        self.console.print(Panel(banner_text, style="bold cyan", subtitle="Control Kernel v3"))

    def start_loop(self):
        """Main interaction loop for the CLI."""
        self.show_banner()
        self.console.print("[yellow]System online. Type 'exit' to quit or 'help' for tools.[/yellow]\n")

        while True:
            user_input = Prompt.ask("[bold green]User[/bold green]")
            
            if user_input.lower() in ["exit", "sair", "quit"]:
                self.console.print("\n[red]Shutting down ARKANIS V3...[/red]\n")
                break
                
            if user_input.lower() == "help":
                self.show_help()
                continue

            try:
                # Visibility Mode avoids wrapping everything in a single progress bar
                response = self.agent.handle_input(user_input)
            except Exception as e:
                response = f"[Kernel Error] {str(e)}"

            self.console.print(Panel(response, title="[bold blue]ARKANIS FINAL REPORT[/bold blue]", border_style="blue"))

    def show_help(self):
        """Displays registered tools."""
        from tools.registry import registry
        table = Table(title="Available Tools")
        table.add_column("Tool Name", style="cyan")
        table.add_column("Description", style="white")
        
        tools = registry.list_tools()
        for name, desc in tools.items():
            table.add_row(name, desc)
            
        self.console.print(table)
