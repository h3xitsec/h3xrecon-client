import typer
from typing import Optional, List
from .handlers import CommandHandlers
from .options import GlobalOptions
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import clear
from rich.console import Console
import shutil
import math
import sys
import uuid
from .command_options import ShowCommandOptions, ConfigCommandOptions, JobCommandOptions, SystemCommandOptions

app = typer.Typer(
    name="h3xrecon",
    help="H3xRecon - Advanced Reconnaissance Framework Client",
    add_completion=True,
)

# Initialize global options
app.global_options = GlobalOptions()

# Get all global options
global_options = GlobalOptions.get_options()

@app.callback()
def main(
    program: Optional[str] = global_options["program"],
    no_pager: bool = global_options["no_pager"],
    quiet: bool = global_options["quiet"],
    timeout: int = global_options["timeout"],
    debug: bool = global_options["debug"],
):
    """
    H3xRecon - Advanced Reconnaissance Framework Client
    """
    # Update global options with provided values
    app.global_options.update(
        program=program,
        no_pager=no_pager,
        quiet=quiet,
        timeout=timeout,
        debug=debug
    )

def get_handlers() -> CommandHandlers:
    """Get command handlers with current global options"""
    return CommandHandlers(app.global_options)

@app.command("program")
def program_commands(
    action: str = typer.Argument(..., help="Action to perform: list, add, del, import"),
    args: Optional[List[str]] = typer.Argument(None, help="Additional arguments")
):
    """Manage reconnaissance programs"""
    handlers = get_handlers()
    asyncio.run(handlers.handle_program_commands(action, args or []))

@app.command("system")
def system_commands(
    args: Optional[List[str]] = typer.Argument(None, help="Additional arguments"),
    filter: Optional[str] = SystemCommandOptions.get_options()["filter"]
):
    """
    System management commands
    
    Actions:
    - queue: Manage message queues (show/messages/flush worker/job/data)
    - cache: Manage system cache (flush/show)
    - status: Control system status (flush all/worker/jobprocessor/dataprocessor)
    - database: Manage database (backup/restore path/to/file)
    """
    handlers = get_handlers()
    cmd_opts = SystemCommandOptions(filter=filter)
    
    if not args or len(args) < 2:
        typer.echo("Error: Invalid command. Use 'h3xrecon system --help' for more information.")
        raise typer.Exit(1)
        
    if args[0] == 'cache':
        asyncio.run(handlers.handle_system_commands_with_2_args(args[0], args[1]))
        return
    elif args[0] == 'database':
        if len(args) != 3:
            typer.echo("Error: Invalid database command. Usage: h3xrecon system database (backup|restore) path/to/file")
            raise typer.Exit(1)
        asyncio.run(handlers.handle_system_commands_with_3_args(args[0], args[1], args[2]))
        return
    elif args[0] in ['queue', 'status']:
        if len(args) != 3:
            typer.echo("Error: Invalid command. Use 'h3xrecon system --help' for more information.")
            raise typer.Exit(1)
        asyncio.run(handlers.handle_system_commands_with_3_args(args[0], args[1], args[2], filter=cmd_opts.filter))
        return
    else:
        typer.echo("Error: Invalid command. Use 'h3xrecon system --help' for more information.")
        raise typer.Exit(1)

@app.command("worker")
def worker_commands(
    args: Optional[List[str]] = typer.Argument(None, help="Additional arguments"),
):
    """
    Worker management commands
    
    Actions:
    - list: List components (worker/jobprocessor/dataprocessor/all)
    - status: Show component status (worker/jobprocessor/dataprocessor/componentid/all)
    - killjob: Kill job on worker (componentid/all)
    - ping: Ping a component (componentid)
    - pause: Pause component (worker/jobprocessor/dataprocessor/componentid/all)
    - unpause: Unpause component (worker/jobprocessor/dataprocessor/componentid/all)
    - report: Get component report (componentid)
    """
    handlers = get_handlers()
    if args[0] in ['killjob', 'pause', 'unpause', 'ping', 'list', 'report', 'status']:
        asyncio.run(handlers.handle_worker_commands(args[0], args[1]))
        return
    else:
        typer.echo("Error: Invalid command. Use 'h3xrecon worker --help' for more information.")
        raise typer.Exit(1)

@app.command("config")
def config_commands(
    action: str = typer.Argument(..., help="Action: add, del, list"),
    type: str = typer.Argument(..., help="Type: cidr, scope"),
    value: Optional[str] = typer.Argument(None, help="Value for add/del actions"),
    wildcard: bool = ConfigCommandOptions.get_options()["wildcard"],
    regex: Optional[str] = ConfigCommandOptions.get_options()["regex"]
):
    """Configuration commands"""
    handlers = get_handlers()
    opts = app.global_options
    cmd_opts = ConfigCommandOptions(
        wildcard=wildcard,
        regex=regex
    )
    
    if not opts.program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)
    asyncio.run(handlers.handle_config_commands(action, type, opts.program, value, cmd_opts.wildcard, cmd_opts.regex))

@app.command("list")
def list_commands(
    type: str = typer.Argument(..., help="Type: domains, ips, websites, websites_paths, services, nuclei, certificates"),
    resolved: bool = ShowCommandOptions.get_options()["resolved"],
    unresolved: bool = ShowCommandOptions.get_options()["unresolved"],
    severity: Optional[str] = ShowCommandOptions.get_options()["severity"],
    filter: Optional[str] = ShowCommandOptions.get_options()["filter"]
):
    """List reconnaissance assets"""
    handlers = get_handlers()
    opts = app.global_options
    cmd_opts = ShowCommandOptions(
        resolved=resolved,
        unresolved=unresolved,
        severity=severity,
        filter=filter
    )
    
    if not opts.program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)
        
    async def run():
        items = await handlers.handle_list_commands(
            type, 
            opts.program, 
            cmd_opts.resolved, 
            cmd_opts.unresolved, 
            cmd_opts.severity,
            cmd_opts.filter
        )
        if items:
            # Get the main identifier for each asset type
            identifiers = []
            for item in items:
                if type == 'domains':
                    identifiers.append(item['Domain'])
                elif type == 'ips':
                    identifiers.append(item['IP'])
                elif type == 'websites':
                    identifiers.append(item['URL'])
                elif type == 'websites_paths':
                    identifiers.append(item['URL'])
                elif type == 'services':
                    identifiers.append(f"{item['IP']}:{item['Port']}")
                elif type == 'nuclei':
                    identifiers.append(f"{item['Target']} ({item['Severity']})")
                elif type == 'certificates':
                    identifiers.append(item['Subject CN'])
                elif type == 'screenshots':
                    identifiers.append(item['URL'])
            
            for identifier in identifiers:
                if not opts.quiet:
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
    type: str = typer.Argument(..., help="Type: domains, ips, websites, websites_paths, services, nuclei, certificates, screenshots, dns"),
    resolved: bool = ShowCommandOptions.get_options()["resolved"],
    unresolved: bool = ShowCommandOptions.get_options()["unresolved"],
    severity: Optional[str] = ShowCommandOptions.get_options()["severity"],
    domain: Optional[str] = ShowCommandOptions.get_options()["domain"],
    filter: Optional[str] = ShowCommandOptions.get_options()["filter"]
):
    """Show reconnaissance assets in table format"""
    handlers = get_handlers()
    opts = app.global_options
    cmd_opts = ShowCommandOptions(
        resolved=resolved,
        unresolved=unresolved,
        severity=severity,
        domain=domain,
        filter=filter
    )
    
    if not opts.program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)
        
    async def run():
        if type == 'dns':
            await handlers.handle_dns_command(opts.program, cmd_opts.domain)
        else:
            items = await handlers.handle_show_commands(
                type_name=type,
                program=opts.program,
                resolved=cmd_opts.resolved,
                unresolved=cmd_opts.unresolved,
                severity=cmd_opts.severity,
                filter=cmd_opts.filter
            )
            if items:
                headers = get_headers_for_type(type)
                if opts.no_pager:
                    # Display all results without pagination
                    console = Console()
                    terminal_width = shutil.get_terminal_size().columns
                    
                    # Calculate column widths
                    col_widths = CliPaginator().calculate_column_widths(headers, items, terminal_width)
                    
                    # Print headers
                    header_row = " | ".join(
                        f"{h:<{w}}" for h, w in zip(headers, col_widths)
                    )
                    console.print(f"[bold]{header_row}[/]")
                    console.print("-" * min(sum(col_widths) + (len(headers) - 1) * 3, terminal_width))
                    
                    # Print items
                    for item in items:
                        row = " | ".join(
                            f"{str(field):<{w}}" for field, w in zip(item, col_widths)
                        )
                        console.print(row)
                else:
                    # Use pagination
                    paginator = CliPaginator()
                    await paginator.paginate(items, headers)
            
    asyncio.run(run())

def get_headers_for_type(type_name):
    """Return headers based on asset type"""
    headers_map = {
        'domains': ['Domain', 'IPs', 'CNAMEs', 'Catchall'],
        'ips': ['IP', 'PTR', 'Cloud Provider'],
        'websites': ['URL','Host','Port','Scheme','Techs'],
        'websites_paths': ['URL', 'Path', 'Final Path', 'Status Code', 'Content Type'],
        'services': ['IP', 'Port', 'Service', 'Protocol', 'Resolved Hostname'],
        'nuclei': ['Target', 'Template', 'Severity', 'Matcher Name'],
        'certificates': ['Subject CN', 'Issuer Org', 'Serial', 'Valid Date', 'Expiry Date', 'Subject Alternative Names'],
        'screenshots': ['URL', 'Screenshot', 'MD5 Hash']
    }
    return headers_map.get(type_name, [])

@app.command("workflow")
def workflow_commands(
    name: str = typer.Argument(..., help="workflow function to execute (e.g., dns_resolve)"),
    target: str = typer.Argument(..., help="Target for the function (use '-' to read from stdin)"),
    wordlist: Optional[str] = JobCommandOptions.get_options()["wordlist"],
    mode: Optional[str] = JobCommandOptions.get_options()["mode"],
    no_trigger: bool = JobCommandOptions.get_options()["no_trigger"],
    wait_ack: bool = JobCommandOptions.get_options()["wait_ack"],
    force: bool = JobCommandOptions.get_options()["force"]
):
    """Execute workflow functions (combined functions) on targets"""
    handlers = get_handlers()
    opts = app.global_options
    cmd_opts = JobCommandOptions(
        wordlist=wordlist,
        mode=mode,
        no_trigger=no_trigger,
        wait_ack=wait_ack,
        force=force
    )
    
    if not opts.program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)

    # Handle stdin input when target is '-'
    if target == '-':
        targets = []
        for line in sys.stdin:
            line = line.strip()
            if line:  # Skip empty lines
                targets.append(line)
        if not targets:
            typer.echo("Error: No targets received from stdin")
            raise typer.Exit(1)
    else:
        targets = [target]

    asyncio.run(handlers.handle_workflow_command(name, opts.program, targets, cmd_opts.force))

@app.command("sendjob")
def sendjob_command(
    function_name: str = typer.Argument(..., help="Function to execute"),
    target: str = typer.Argument(..., help="Target for the function (use '-' to read from stdin)"),
    params: Optional[List[str]] = typer.Argument(None, help="Additional parameters"),
    wordlist: Optional[str] = JobCommandOptions.get_options()["wordlist"],
    mode: Optional[str] = JobCommandOptions.get_options()["mode"],
    no_trigger: bool = JobCommandOptions.get_options()["no_trigger"],
    wait_ack: bool = JobCommandOptions.get_options()["wait_ack"],
    force: bool = JobCommandOptions.get_options()["force"]
):
    """Send job to worker"""
    handlers = get_handlers()
    opts = app.global_options
    cmd_opts = JobCommandOptions(
        wordlist=wordlist,
        mode=mode,
        no_trigger=no_trigger,
        wait_ack=wait_ack,
        force=force
    )
    
    if not opts.program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)

    # Handle stdin input when target is '-'
    if target == '-':
        targets = []
        for line in sys.stdin:
            line = line.strip()
            if line:  # Skip empty lines
                targets.append(line)
        if not targets:
            typer.echo("Error: No targets received from stdin")
            raise typer.Exit(1)
    else:
        targets = [target]

    response_id = str(uuid.uuid4()) if cmd_opts.wait_ack else None
    debug_id = str(uuid.uuid4()) if opts.debug else None
    
    job_params = {
        "function_name": function_name,
        "targets": targets,
        "program": opts.program,
        "force": cmd_opts.force,
        "params": params or {},
        "wordlist": cmd_opts.wordlist,
        "no_trigger": cmd_opts.no_trigger,
        "timeout": opts.timeout,
        "response_id": response_id,
        "debug_id": debug_id
    }
    if cmd_opts.mode:
        job_params["mode"] = cmd_opts.mode
    asyncio.run(handlers.handle_sendjob_command(**job_params))

@app.command("console")
def console_mode():
    """Start interactive console mode"""
    from .console import H3xReconConsole
    console = H3xReconConsole()
    asyncio.run(console.run())

@app.command("add")
def add_commands(
    type: str = typer.Argument(..., help="Type: domain, ip, website, website_path"),
    item: str = typer.Argument(..., help="Item to add"),
    stdin: bool = typer.Option(False, "--stdin", "-", help="Read items from stdin")
):
    """Add reconnaissance assets"""
    handlers = get_handlers()
    opts = app.global_options
    if not opts.program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)

    items = []
    if stdin:
        # Read from stdin
        for line in sys.stdin:
            line = line.strip()
            if line:  # Skip empty lines
                items.append(line)
    else:
        items = [item]

    asyncio.run(handlers.handle_add_commands(type, opts.program, items, opts.no_trigger))

if __name__ == "__main__":
    app()