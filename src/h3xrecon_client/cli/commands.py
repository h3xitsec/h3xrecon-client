import typer
from typing import Optional, List
from .handlers import CommandHandlers
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import clear
from rich.console import Console
import shutil
import math

app = typer.Typer(
    name="h3xrecon",
    help="H3xRecon - Advanced Reconnaissance Framework Client",
    add_completion=True,
)

handlers = CommandHandlers()

# Add program option to the main app
program_option = typer.Option(None, "--program", "-p", help="Program to work on")

@app.callback()
def main(program: Optional[str] = program_option):
    """
    H3xRecon - Advanced Reconnaissance Framework Client
    """
    if program:
        handlers.current_program = program

def get_program(cmd_program: Optional[str]) -> Optional[str]:
    """Get program from command option or global option"""
    return cmd_program or handlers.current_program

@app.command("program")
def program_commands(
    action: str = typer.Argument(..., help="Action to perform: list, add, del, import"),
    args: Optional[List[str]] = typer.Argument(None, help="Additional arguments")
):
    """Manage reconnaissance programs"""
    asyncio.run(handlers.handle_program_commands(action, args or []))

@app.command("system")
def system_commands(
    component: str = typer.Argument(..., help="Component: killjob, cache, queue, workers, pause, unpause, report"),
    action: str = typer.Argument(..., help="Action to perform"),
    args: Optional[List[str]] = typer.Argument(None, help="Additional arguments"),
):
    """
    System management commands
    
    Components:
    - queue: Manage message queues (show/messages/flush/lock/unlock worker/job/data)
    - cache: Manage system cache (flush/show)
    - workers: Manage workers (status/list)
    - killjob: Kill specific job
    - pause/unpause: Control system components
    - report: Get component reports
    """
    # Validate queue commands
    if component == 'queue':
        valid_actions = ['show', 'messages', 'flush', 'lock', 'unlock']
        valid_targets = ['worker', 'job', 'data']
        
        if action not in valid_actions:
            typer.echo(f"Error: Invalid queue action. Must be one of: {', '.join(valid_actions)}")
            raise typer.Exit(1)
            
        if not args or args[0] not in valid_targets:
            typer.echo(f"Error: Must specify queue type: {', '.join(valid_targets)}")
            raise typer.Exit(1)
    
    asyncio.run(handlers.handle_system_commands(component, action, args or []))

@app.command("config")
def config_commands(
    action: str = typer.Argument(..., help="Action: add, del, list"),
    type: str = typer.Argument(..., help="Type: cidr, scope"),
    value: Optional[str] = typer.Argument(None, help="Value for add/del actions"),
    program: Optional[str] = program_option
):
    """Configuration commands"""
    program = get_program(program)
    if not program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)
    asyncio.run(handlers.handle_config_commands(action, type, program, value))

@app.command("list")
def list_commands(
    type: str = typer.Argument(..., help="Type: domains, ips, urls, services, nuclei, certificates"),
    resolved: bool = typer.Option(False, "--resolved", help="Show only resolved items"),
    unresolved: bool = typer.Option(False, "--unresolved", help="Show only unresolved items"),
    severity: Optional[str] = typer.Option(None, "--severity", help="Severity for nuclei findings"),
    program: Optional[str] = program_option
):
    """List reconnaissance assets"""
    program = get_program(program)
    if not program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)
        
    async def run():
        items = await handlers.handle_list_commands(type, program, resolved, unresolved, severity)
        if items:
            # Get the main identifier for each asset type
            identifiers = []
            for item in items:
                if type == 'domains':
                    identifiers.append(item[0])  # domain
                elif type == 'ips':
                    identifiers.append(item[0])  # ip
                elif type == 'urls':
                    identifiers.append(item[0])  # url
                elif type == 'services':
                    identifiers.append(f"{item[0]}:{item[1]}")  # ip:port
                elif type == 'nuclei':
                    identifiers.append(f"{item[0]} ({item[2]})")  # target (severity)
                elif type == 'certificates':
                    identifiers.append(item[0])  # domain
            
            for identifier in identifiers:
                typer.echo(identifier)
                
    asyncio.run(run())

class CliPaginator:
    def __init__(self):
        terminal_height = shutil.get_terminal_size().lines
        self.items_per_page = terminal_height - 6  # Leave room for headers and navigation
        self.current_page = 1
        self.items = []
        self.headers = None
        
    def create_key_bindings(self):
        kb = KeyBindings()
        
        @kb.add('n')
        async def _(event):
            if self.current_page < self.total_pages:
                self.current_page += 1
                event.app.exit()
            
        @kb.add('p')
        async def _(event):
            if self.current_page > 1:
                self.current_page -= 1
                event.app.exit()
            
        @kb.add('q')
        async def _(event):
            event.app.exit('q')
            
        return kb
        
    def calculate_column_widths(self, headers, items, terminal_width):
        """Calculate optimal column widths based on content and terminal width"""
        # Get max width for each column
        widths = []
        for i in range(len(headers)):
            column_content = [str(item[i]) for item in items] + [headers[i]]
            max_width = max(len(str(c)) for c in column_content)
            widths.append(max_width)
            
        # Adjust if total width exceeds terminal
        total_width = sum(widths) + (len(headers) - 1) * 3  # Account for separators
        if total_width > terminal_width:
            # Distribute available width proportionally
            available_width = terminal_width - (len(headers) - 1) * 3
            total_max_width = sum(widths)
            widths = [max(4, int(w * available_width / total_max_width)) for w in widths]
            
        return widths
        
    async def paginate(self, items, headers):
        """Display items with pagination"""
        self.items = items
        self.headers = headers
        self.total_pages = math.ceil(len(items) / self.items_per_page)
        self.current_page = 1
        
        # Create session for pagination
        session = PromptSession(key_bindings=self.create_key_bindings())
        
        while True:
            clear()
            self.show_current_page()
            
            # Show navigation help
            nav_text = (
                f"\nPage {self.current_page}/{self.total_pages}\n"
                "Navigation: Press "
                "[cyan]n[/cyan] for next page, "
                "[cyan]p[/cyan] for previous page, "
                "[cyan]q[/cyan] to quit"
            )
            console = Console()
            console.print(nav_text)
            
            # Get single keypress
            key = await session.app.run_async()
            if key == 'q':
                break
            
            # Update terminal height in case of resize
            terminal_height = shutil.get_terminal_size().lines
            self.items_per_page = terminal_height - 6
            
    def show_current_page(self):
        """Show the current page of items"""
        terminal_width = shutil.get_terminal_size().columns
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.items[start_idx:end_idx]
        
        # Calculate column widths
        col_widths = self.calculate_column_widths(self.headers, page_items, terminal_width)
        
        console = Console()
        
        # Print headers
        header_row = " | ".join(
            f"{h:<{w}}" for h, w in zip(self.headers, col_widths)
        )
        console.print(f"[bold]{header_row}[/]")
        console.print("-" * min(sum(col_widths) + (len(self.headers) - 1) * 3, terminal_width))
        
        # Print items
        for item in page_items:
            row = " | ".join(
                f"{str(field):<{w}}" for field, w in zip(item, col_widths)
            )
            console.print(row)

@app.command("show")
def show_commands(
    type: str = typer.Argument(..., help="Type: domains, ips, urls, services, nuclei, certificates"),
    resolved: bool = typer.Option(False, "--resolved", help="Show only resolved items"),
    unresolved: bool = typer.Option(False, "--unresolved", help="Show only unresolved items"),
    severity: Optional[str] = typer.Option(None, "--severity", help="Severity for nuclei findings"),
    program: Optional[str] = program_option
):
    """Show reconnaissance assets in table format"""
    program = get_program(program)
    if not program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)
        
    async def run():
        items = await handlers.handle_list_commands(type, program, resolved, unresolved, severity)
        if items:
            headers = get_headers_for_type(type)
            paginator = CliPaginator()
            await paginator.paginate(items, headers)
            
    asyncio.run(run())

def get_headers_for_type(type_name):
    """Return headers based on asset type"""
    headers_map = {
        'domains': ['Domain', 'IP', 'Status'],
        'ips': ['IP', 'Hostname', 'Status'],
        'urls': ['URL', 'Status', 'Title'],
        'services': ['IP', 'Port', 'Service', 'Version'],
        'nuclei': ['Target', 'Template', 'Severity', 'Info'],
        'certificates': ['Domain', 'Issuer', 'Valid Until']
    }
    return headers_map.get(type_name, [])

@app.command("sendjob")
def sendjob_command(
    function: str = typer.Argument(..., help="Function to execute"),
    target: str = typer.Argument(..., help="Target for the function"),
    force: bool = typer.Option(False, "--force", help="Force job execution"),
    params: Optional[List[str]] = typer.Argument(None, help="Additional parameters"),
    program: Optional[str] = program_option
):
    """Send job to worker"""
    program = get_program(program)
    if not program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)
    asyncio.run(handlers.handle_sendjob_command(function, target, program, force, params or []))

@app.command("console")
def console_mode():
    """Start interactive console mode"""
    from .console import H3xReconConsole
    console = H3xReconConsole()
    asyncio.run(console.run())

if __name__ == "__main__":
    app()