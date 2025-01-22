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
import sys

app = typer.Typer(
    name="h3xrecon",
    help="H3xRecon - Advanced Reconnaissance Framework Client",
    add_completion=True,
)

handlers = CommandHandlers()

# Add program option to the main app
program_option = typer.Option(None, "--program", "-p", help="Program to work on")

# Add no_pager to the global options at the top
no_pager_option = typer.Option(False, "--no-pager", help="Disable pagination and show all results at once")

## Add wordlist option to the global options at the top
wordlist_option = typer.Option(None, "--wordlist", help="Wordlist to use for web_fuzz")

# Add options for scope management
wildcard_option = typer.Option(False, "--wildcard", help="Use wildcard for domain scope")
regex_option = typer.Option(None, "--regex", help="Use regex for domain scope")

# Add timeout option to the global options at the top
timeout_option = typer.Option(300, "--timeout", help="Timeout for job execution in seconds")

# Add trigger_new_jobs option to the global options at the top
no_trigger_option = typer.Option(False, "--no-trigger", help="Do not trigger new jobs after processing")

# Add mode option to the global options at the top
mode_option = typer.Option(None, "--mode", help="Plugin run mode")

# Add a filter option to the global options at the top
filter_option = typer.Option(None, "--filter", "-f", help="Filter")

# Add a ack option to the global options at the top
wait_ack_option = typer.Option(False, "--wait-ack", "-w", help="Wait for job request response")

@app.callback()
def main(
    program: Optional[str] = program_option,
    no_pager: bool = no_pager_option,
    wordlist: Optional[str] = wordlist_option,
    wildcard: bool = wildcard_option,
    regex: Optional[str] = regex_option,
    no_trigger: bool = no_trigger_option,
    timeout: int = timeout_option,
    mode: Optional[str] = mode_option,
    filter: Optional[str] = filter_option,
    wait_ack: bool = wait_ack_option,
):
    """
    H3xRecon - Advanced Reconnaissance Framework Client
    """
    if program:
        handlers.current_program = program
    handlers.no_pager = no_pager
    if wordlist:
        handlers.wordlist = wordlist
    if wildcard:
        handlers.wildcard_scope = wildcard
    if regex:
        handlers.regex_scope = regex
    handlers.no_trigger = no_trigger
    handlers.timeout = timeout
    handlers.mode = mode
    handlers.filter = filter
    handlers.wait_ack = wait_ack
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
    args: Optional[List[str]] = typer.Argument(None, help="Additional arguments"),
    filter: str = typer.Option(None, "--filter", "-f", help="Filter")
):
    """
    System management commands
    
    Actions:
    - queue: Manage message queues (show/messages/flush worker/job/data)
    - cache: Manage system cache (flush/show)
    - status: Control system status (flush all/worker/jobprocessor/dataprocessor)
    - database: Manage database (backup/restore path/to/file)
    """
    
    if not args or len(args) < 2:
        typer.echo("Error: Invalid command. Use 'h3xrecon system --help' for more information.")
        raise typer.Exit(1)
        
    print(f"Filter value in system_commands: {filter}")  # Debug print
    
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
        print(f"Passing filter to handler: {filter}")  # Debug print
        asyncio.run(handlers.handle_system_commands_with_3_args(args[0], args[1], args[2], filter=filter))
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
    
    if args[0] in ['killjob', 'pause', 'unpause', 'ping', 'list', 'report','status']:
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
    program: Optional[str] = program_option,
    wildcard: bool = wildcard_option,
    regex: Optional[str] = regex_option
):
    """Configuration commands"""
    program = get_program(program)
    if not program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)
    asyncio.run(handlers.handle_config_commands(action, type, program, value, wildcard, regex))

@app.command("list")
def list_commands(
    type: str = typer.Argument(..., help="Type: domains, ips, websites, websites_paths, services, nuclei, certificates"),
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
                    identifiers.append(item['Domain'])  # domain
                elif type == 'ips':
                    identifiers.append(item['IP'])  # ip
                elif type == 'websites':
                    identifiers.append(item['URL'])  # url
                elif type == 'websites_paths':
                    identifiers.append(item['URL'])  # url
                elif type == 'services':
                    identifiers.append(f"{item['IP']}:{item['Port']}")  # ip:port
                elif type == 'nuclei':
                    identifiers.append(f"{item['Target']} ({item['Severity']})")  # target (severity)
                elif type == 'certificates':
                    identifiers.append(item['Subject CN'])  # domain
                elif type == 'screenshots':
                    identifiers.append(item['URL'])  # screenshot
            
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
    type: str = typer.Argument(..., help="Type: domains, ips, websites, websites_paths, services, nuclei, certificates, screenshots, dns"),
    resolved: bool = typer.Option(False, "--resolved", help="Show only resolved items"),
    unresolved: bool = typer.Option(False, "--unresolved", help="Show only unresolved items"),
    severity: Optional[str] = typer.Option(None, "--severity", help="Severity for nuclei findings"),
    domain: str = typer.Option(None, "--domain", "-d", help="Domain to show DNS records for"),
    program: Optional[str] = program_option,
    no_pager: Optional[bool] = no_pager_option
):
    """Show reconnaissance assets in table format"""
    program = get_program(program)
    if not program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)
        
    async def run():
        if type == 'dns':
            await handlers.handle_dns_command(program, domain)
        else:
            items = await handlers.handle_show_commands(type, program, resolved, unresolved, severity)
            if items:
                headers = get_headers_for_type(type)
                
                # Simplified logic: if either global or local no_pager is True, disable pagination
                disable_pager = handlers.no_pager or no_pager
                
                if disable_pager:
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
    force: bool = typer.Option(False, "--force", help="Force job execution"),
    program: Optional[str] = program_option
):
    """Execute workflow functions (combined functions) on targets"""
    program = get_program(program)
    if not program:
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

    asyncio.run(handlers.handle_workflow_command(name, program, targets, force))
    
@app.command("sendjob")
def sendjob_command(
    function_name: str = typer.Argument(..., help="Function to execute"),
    target: str = typer.Argument(..., help="Target for the function (use '-' to read from stdin)"),
    force: bool = typer.Option(False, "--force", help="Force job execution"),
    no_trigger: bool = typer.Option(False, "--no-trigger", help="Do not trigger new jobs after processing"),
    params: Optional[List[str]] = typer.Argument(None, help="Additional parameters"),
    program: Optional[str] = program_option,
    wordlist: Optional[str] = wordlist_option,
    timeout: int = timeout_option,
    mode: Optional[str] = mode_option,
    wait_ack: bool = wait_ack_option
):
    """Send job to worker"""
    program = get_program(program)
    if not program:
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
        job_params = {
            "function_name": function_name,
            "targets": targets,
            "program": program,
            "force": force,
            "params": params or {},
            "wordlist": wordlist,
            "no_trigger": no_trigger,
            "timeout": timeout,
            "need_response": wait_ack
        }
        if mode:
            job_params["mode"] = mode
        #print(job_params)
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
    program: Optional[str] = program_option,
    no_trigger: bool = typer.Option(False, "--no-trigger", help="Do not trigger new jobs after processing"),
    stdin: bool = typer.Option(False, "--stdin", "-", help="Read items from stdin")
):
    """Add reconnaissance assets"""
    program = get_program(program)
    if not program:
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

    asyncio.run(handlers.handle_add_commands(type, program, items, no_trigger))

if __name__ == "__main__":
    app()