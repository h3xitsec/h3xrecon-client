from rich.console import Console
from rich.table import Table
from ..api import ClientAPI
from ..queue import ClientQueue, StreamLockedException
from typing import Optional, List, Dict, Any
import asyncio
import yaml
import typer

class CommandHandlers:
    def __init__(self):
        self.console = Console()
        self.api = ClientAPI()
        self.current_program = None
        self.client_queue = ClientQueue()
        self.no_pager = False

    def show_help(self) -> None:
        """Show help information"""
        table = Table(title="Available Commands")
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="green")
        
        # Program commands
        table.add_row("use <program>", "Set current working program")
        table.add_row("program list", "List all programs")
        table.add_row("program add <n>", "Add a new program")
        table.add_row("program del <n>", "Delete a program")
        table.add_row("program import <file>", "Import programs from file")
        
        # System commands
        table.add_row("system queue show (worker|job|data)", "Show queue information")
        table.add_row("system queue messages (worker|job|data)", "Show queue messages")
        table.add_row("system queue flush (worker|job|data)", "Flush queue")
        table.add_row("system cache (flush|show)", "Manage system cache")
        table.add_row("system status flush (all|worker|jobprocessor|dataprocessor)", "Flush system status")
        
        # Worker commands
        table.add_row("worker list (worker|jobprocessor|dataprocessor|all)", "List components")
        table.add_row("worker status (worker|jobprocessor|dataprocessor|componentid|all)", "Show component status")
        table.add_row("worker killjob (componentid|all)", "Kill job on worker")
        table.add_row("worker ping <componentid>", "Ping a component")
        table.add_row("worker pause (worker|jobprocessor|dataprocessor|componentid|all)", "Pause component")
        table.add_row("worker unpause (worker|jobprocessor|dataprocessor|componentid|all)", "Unpause component")
        table.add_row("worker report <componentid>", "Get component report")
        
        # Config commands
        table.add_row("config add cidr <cidr>", "Add CIDR to current program")
        table.add_row("config add scope <scope>", "Add scope to current program")
        table.add_row("config del cidr <cidr>", "Remove CIDR from current program")
        table.add_row("config del scope <scope>", "Remove scope from current program")
        table.add_row("config list cidr", "List CIDRs of current program")
        table.add_row("config list scope", "List scopes of current program")
        table.add_row("config database drop", "Drop current program's database")
        
        # Asset commands
        table.add_row("add (domain|ip|url) <value> [--stdin]", "Add asset to current program")
        table.add_row("del (domain|ip|url) <value>", "Delete asset from current program")
        
        # List/Show commands
        table.add_row("list domains [--resolved] [--unresolved]", "List domains")
        table.add_row("list ips [--resolved] [--unresolved]", "List IPs")
        table.add_row("list urls", "List URLs")
        table.add_row("list services", "List services")
        table.add_row("list nuclei [--severity <sev>]", "List nuclei findings")
        table.add_row("list certificates", "List certificates")
        table.add_row("show domains [--resolved] [--unresolved]", "Show domains in table format")
        table.add_row("show ips [--resolved] [--unresolved]", "Show IPs in table format")
        table.add_row("show urls", "Show URLs in table format")
        table.add_row("show services", "Show services in table format")
        table.add_row("show nuclei [--severity <sev>]", "Show nuclei findings in table format")
        table.add_row("show certificates", "Show certificates in table format")
        
        # Job commands
        table.add_row("sendjob <function> <target> [params...] [--force]", "Send job to worker")
        
        # General commands
        table.add_row("help", "Show this help message")
        table.add_row("exit", "Exit the console")
        
        self.console.print(table)

    async def handle_program_commands(self, action: str, args: List[str]) -> None:
        """Handle program-related commands"""
        if action == 'list':
            programs = await self.api.get_programs()
            [self.console.print(r.get("name")) for r in programs.data]
        
        elif action == 'add' and args:
            result = await self.api.add_program(args[0])
            if result.success:
                self.console.print(f"[green]Program '{args[0]}' added successfully[/]")
            else:
                self.console.print(f"[red]Error adding program: {result.error}[/]")
                
        elif action == 'del' and args:
            result = await self.api.remove_program(args[0])
            if result.success:
                self.console.print(f"[green]Program '{args[0]}' removed successfully[/]")
            else:
                self.console.print(f"[red]Error removing program: {result.error}[/]")
                
        elif action == 'import' and args:
            await self.import_programs(args[0])

    async def handle_system_commands_with_2_args(self, arg1: str, arg2: str) -> None:
        """Handle system management commands"""
        try:
            if arg1 == 'cache':
                if arg2 == 'flush':
                    await self.api.flush_cache()
                    self.console.print("[green]Cache flushed[/]")
                elif arg2 == 'show':
                    keys = await self.api.show_cache_keys_values()
                    [self.console.print(k) for k in keys]
            else:
                self.console.print(f"[red]Error: Invalid system command: {arg1}[/]")

        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/]")

    async def handle_system_commands_with_3_args(self, arg1: str, arg2: str, arg3: str = None) -> None:
        """Handle system management commands"""
        try:
            if arg1 == 'status' and arg2 == 'flush':
                components = await self.api.get_components(arg3)
                if components.success:
                    for component in components.data:
                        result = await self.api.flush_component_status(component)
                        if result.success:
                            self.console.print("[green]Status flushed successfully[/]")
                        else:
                            self.console.print(f"[red]Error flushing status: {result.error}[/]")
                return
            elif arg1 == 'queue':
                # Determine which stream to use
                stream = None
                if arg3 == 'worker':
                    stream = 'FUNCTION_EXECUTE'
                elif arg3 == 'job':
                    stream = 'FUNCTION_OUTPUT'
                elif arg3 == 'data':
                    stream = 'RECON_DATA'
                else:
                    self.console.print(f"[red]Error: Invalid stream type: {arg3}[/]")
                    return

                if arg2 == 'show':
                    info = await self.client_queue.get_stream_info(stream)
                    self.console.print(info)
                elif arg2 == 'messages':
                    try:
                        messages = await self.client_queue.get_stream_messages(stream)
                        for msg in messages:
                            self.console.print(msg)
                    except StreamLockedException:
                        self.console.print("[red]Error: Stream is locked[/]")
                elif arg2 == 'flush':
                    await self.client_queue.purge_stream(stream)
                    self.console.print(f"[green]Stream {stream} flushed[/]")
                else:
                    self.console.print(f"[red]Error: Invalid queue command: {arg2}[/]")
            else:
                self.console.print(f"[red]Error: Invalid system command: {arg1}[/]")

        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/]")

    async def handle_config_commands(self, action: str, type: str, program: str, value: Optional[str] = None) -> None:
        """Handle configuration commands"""
        try:
            if action == 'list':
                if type == 'cidr':
                    result = await self.api.get_program_cidr(program)
                    [self.console.print(r.get('cidr')) for r in result.data]
                elif type == 'scope':
                    result = await self.api.get_program_scope(program)
                    [self.console.print(r.get('regex')) for r in result.data]
                    
            elif action == 'add' and value:
                if type == 'cidr':
                    result = await self.api.add_program_cidr(program, value)
                elif type == 'scope':
                    result = await self.api.add_program_scope(program, value)
                    
                if result.success:
                    self.console.print(f"[green]{type.upper()} '{value}' added successfully[/]")
                else:
                    self.console.print(f"[red]Error adding {type}: {result.error}[/]")
                    
            elif action == 'del' and value:
                if type == 'cidr':
                    result = await self.api.remove_program_cidr(program, value)
                elif type == 'scope':
                    result = await self.api.remove_program_scope(program, value)
                    
                if result.success:
                    self.console.print(f"[green]{type.upper()} '{value}' removed successfully[/]")
                else:
                    self.console.print(f"[red]Error removing {type}: {result.error}[/]")
                    
            elif action == 'database' and type == 'drop':
                result = await self.api.drop_program_data(program)
                print(result)
                if result.success:
                    self.console.print("[green]Database dropped successfully[/]")
                else:
                    self.console.print(f"[red]Error dropping database: {result.error}[/]")
                    
        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/]")

    async def handle_list_commands(self, type_name, program, resolved=False, unresolved=False, severity=None):
        """Handle list commands"""
        try:
            if type_name == 'domains':
                if resolved:
                    result = await self.api.get_resolved_domains(program)
                elif unresolved:
                    result = await self.api.get_unresolved_domains(program)
                else:
                    result = await self.api.get_domains(program)
                return [(d['domain'], d.get('cnames', 'N/A'), d.get('is_catchall', 'unknown')) for d in result.data]
                
            elif type_name == 'ips':
                if resolved:
                    result = await self.api.get_reverse_resolved_ips(program)
                elif unresolved:
                    result = await self.api.get_not_reverse_resolved_ips(program)
                else:
                    result = await self.api.get_ips(program)
                return [(ip['ip'], ip.get('ptr', 'N/A'), ip.get('cloud_provider', 'unknown')) for ip in result.data]
                
            elif type_name == 'urls':
                result = await self.api.get_urls(program)
                return [(url['url'], url.get('title', 'N/A'), url.get('status_code', 'N/A'), url.get('content_type', 'N/A')) for url in result.data]
                
            elif type_name == 'services':
                result = await self.api.get_services(program)
                return [(
                    service['ip'],
                    service.get('port', 'N/A'),
                    service.get('service', 'unknown'),
                    service.get('version', 'N/A')
                ) for service in result.data]
                
            elif type_name == 'nuclei':
                result = await self.api.get_nuclei(program, severity=severity)
                return [(
                    finding['url'],
                    finding.get('template_id', 'unknown'),
                    finding.get('severity', 'unknown'),
                    finding.get('name', 'N/A')
                ) for finding in result.data]
                
            elif type_name == 'certificates':
                result = await self.api.get_certificates(program)
                return [(
                    cert.get('subject_cn', 'unknown'),
                    cert.get('issuer', 'unknown'),
                    cert.get('valid_until', 'unknown')
                ) for cert in result.data]

            if not result or not result.data:
                self.console.print("[yellow]No results found[/]")
                return []
                
        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/]")
            return []

    async def handle_show_commands(self, type_name, program, resolved=False, unresolved=False, severity=None):
        """Handle show commands"""
        # Use the same data fetching logic as list commands
        return await self.handle_list_commands(type_name, program, resolved, unresolved, severity)

    async def handle_sendjob_command(self, function: str, target: str, program: str, 
                                   force: bool = False, params: List[str] = None) -> None:
        """Handle sendjob command"""
        try:
            # First check if program exists
            programs = await self.api.get_programs()
            if not programs.success:
                self.console.print(f"[red]Error: Could not verify program: {programs.error}[/]")
                return
                
            if not any(p.get("name") == program for p in programs.data):
                self.console.print(f"[red]Error: Program '{program}' not found[/]")
                return

            result = await self.api.send_job(
                function_name=function,
                program_name=program,
                params={
                    "target": target,
                    "extra_params": params or []
                },
                force=force
            )
            
            if result and result.success:
                self.console.print("[green]Job sent successfully[/]")
            else:
                error_msg = result.error if result else "Unknown error"
                self.console.print(f"[red]Error sending job: {error_msg}[/]")
                
        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/]")

    async def import_programs(self, file_path: str) -> None:
        """Import programs from a YAML file"""
        try:
            with open(file_path, 'r') as file:
                data = yaml.safe_load(file)
                for program in data.get('programs', []):
                    name = program.get('name')
                    if not name:
                        continue
                        
                    self.console.print(f"Importing program: {name}")
                    result = await self.api.add_program(name)
                    
                    if not result.success:
                        self.console.print(f"[red]Program '{name}' already exists[/]")
                    elif result.data:
                        self.console.print(f"[green]Program '{name}' added successfully[/]")
                    
                    # Add scope
                    for scope in program.get('scope', []):
                        result = await self.api.add_program_scope(name, scope)
                        if result.success:
                            self.console.print(f"[green]Scope '{scope}' added successfully[/]")
                        else:
                            self.console.print(f"[red]Error adding scope '{scope}': {result.error}[/]")
                    
                    # Add CIDR
                    for cidr in program.get('cidr', []):
                        result = await self.api.add_program_cidr(name, cidr)
                        if result.success:
                            self.console.print(f"[green]CIDR '{cidr}' added successfully[/]")
                        else:
                            self.console.print(f"[red]Error adding CIDR '{cidr}': {result.error}[/]")
                            
                    self.console.print("")
                    
        except Exception as e:
            self.console.print(f"[red]Error importing programs: {str(e)}[/]")

    def display_table_results(self, data: List[Dict[str, Any]]) -> None:
        """Display results in table format"""
        if not data:
            self.console.print("[yellow]No results found[/]")
            return

        table = Table()
        headers = list(data[0].keys())
        for header in headers:
            table.add_column(header.capitalize())

        for row in data:
            table.add_row(*[str(row[h]) for h in headers])

        self.console.print(table)

    def display_list_results(self, type_name: str, data: List[Dict[str, Any]]) -> None:
        """Display results in list format"""
        if not data:
            self.console.print("[yellow]No results found[/]")
            return

        for item in data:
            if type_name == 'domains':
                if 'resolved_ips' in item:
                    self.console.print(f"{item['domain']} -> {item['resolved_ips']}")
                else:
                    self.console.print(item['domain'])
            elif type_name == 'ips':
                if 'ptr' in item:
                    self.console.print(f"{item['ip']} -> {item['ptr']}")
                else:
                    self.console.print(item['ip'])
            elif type_name == 'services':
                self.console.print(f"{item['protocol']}:{item['ip']}:{item['port']}")
            elif type_name == 'certificates':
                self.console.print(item['subject_cn'])
            else:
                self.console.print(str(item)) 

    async def handle_add_commands(self, type_name: str, program: str, items: List[str]) -> None:
        """Handle add commands for domains, IPs, and URLs"""
        try:
            if not program:
                self.console.print("[red]Error: No program specified[/]")
                return

            # Validate program exists
            programs = await self.api.get_programs()
            if not programs.success:
                self.console.print(f"[red]Error getting programs: {programs.error}[/]")
                return
                
            if not any(p.get("name") == program for p in programs.data):
                self.console.print(f"[red]Error: Program '{program}' not found[/]")
                return

            # Format items if single item provided
            if isinstance(items, str):
                items = [items]

            # Add items through the API
            result = await self.api.add_item(type_name, program, items)
            if result.success:
                self.console.print(f"[green]Successfully added {len(items)} {type_name}(s) to program '{program}'[/]")
            else:
                self.console.print(f"[red]Error adding {type_name}(s): {result.error}[/]")

        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/]") 

    async def handle_worker_commands(self, arg1: str, arg2: str) -> None:
        """Handle worker management commands"""
        try:
            if arg1 == 'killjob':
                try:
                    if arg2 == 'all':
                        arg2 = 'worker'
                    response = await self.api.kill_job(arg2)
                    
                    # Display command status
                    if response['status'] == 'success':
                        self.console.print("[green]Kill command executed successfully[/]")
                    elif response['status'] == 'warning':
                        self.console.print("[yellow]Kill command executed with warnings[/]")
                    else:
                        self.console.print(f"[red]Error executing kill command: {response.get('message')}[/]")
                        return
                    
                    # Display responses from components
                    if response.get('responses'):
                        self.console.print("\nResponses from components:")
                        for resp in response['responses']:
                            comp_id = resp.get('component_id', 'unknown')
                            status = "[green]success[/]" if resp.get('success') else "[red]failed[/]"
                            tasks = resp.get('tasks_cancelled', 0)
                            self.console.print(f"{comp_id}: {status} ({tasks} tasks cancelled)")
                            if resp.get('error'):
                                self.console.print(f"  Error: {resp['error']}")
                    
                    # Display missing responses
                    if response.get('missing_responses'):
                        self.console.print("\n[yellow]No response received from:[/]")
                        for comp in response['missing_responses']:
                            self.console.print(f"- {comp}")
                            
                except Exception as e:
                    self.console.print(f"[red]Error executing kill command: {str(e)}[/]")

            elif arg1 == 'list':
                # Handle both workers and processors
                valid_components = ['worker', 'jobprocessor', 'dataprocessor', 'all']
                if not arg2 or arg2 not in valid_components:
                    self.console.print(f"Error: Must specify component: {', '.join(valid_components)}")
                    raise typer.Exit(1)
                else:
                    components = await self.api.get_components(arg2)
                    if not components.success:
                        self.console.print(f"[red]Error getting components: {components.error}[/]")
                        return
                        
                    if components.data:
                        for component in components.data:
                            self.console.print(f"- {component.decode() if isinstance(component, bytes) else component}")
                    else:
                        self.console.print("[yellow]No active components found[/]")
            elif arg1 == 'status':
                components = await self.api.get_components(arg2)
                if components.success:
                    for component in components.data:
                        result = await self.api.get_component_status(component)
                        if result.success:
                            self.console.print(f"{component}: {result.data}")
                        else:
                            self.console.print(f"[red]Error getting status: {result.error}[/]")
                return
            elif arg1 in ['pause', 'unpause']:
                # Send pause/unpause command
                result = await self.api.pause_component(component=arg2) if arg1 == 'pause' else await self.api.pause_component(component=arg2, disable=True)
                
                # Display the command result
                if result['status'] == 'success':
                    self.console.print(f"[green]{result['message']}[/]")
                    
                    # Display responses from components
                    if result.get('responses'):
                        self.console.print("\nResponses from components:")
                        
                        for resp in result['responses']:
                            comp_id = resp.get('component_id')
                            status = "[green]success[/]" if resp.get('success') else "[red]failed[/]"
                            self.console.print(f"{comp_id}: {status}")
                            if resp.get('error'):
                                self.console.print(f"  Error: {resp['error']}")
                        
                        # Check for missing responses
                        if result.get('missing_responses'):
                            self.console.print("\n[yellow]No response received from:[/]")
                            for comp in result['missing_responses']:
                                self.console.print(f"- {comp}")
                    else:
                        self.console.print("[yellow]No responses received from components[/]")
                else:
                    self.console.print(f"[red]Error: {result['message']}[/]")

            elif arg1 == 'report':
                result = await self.api.get_component_report(arg2)
                if result['status'] == 'success':
                    for report in result['reports']:
                        if 'data' in report:
                            self.console.print(f"\nReport from {report.get('data', {}).get('component', {}).get('id', 'unknown')}:")
                            self.console.print(report['data'])
                else:
                    self.console.print(f"[red]Error: {result['message']}[/]")
                return

            elif arg1 == 'ping':
                result = await self.api.ping_component(arg2)
                if result['status'] == 'success':
                    self.console.print(f"[green]{result['message']}[/]")
                    if result.get('responses'):
                        for resp in result['responses']:
                            status = "[green]success[/]" if resp.get('command') == 'pong' else "[red]failed[/]"
                            self.console.print(f"Component {resp.get('component_id')}: {resp.get('command').upper()}")
                else:
                    self.console.print(f"[red]Error: {result['message']}[/]")

        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/]")

    async def handle_worker_commands_with_3_args(self, arg1: str, arg2: str, arg3: str = None) -> None:
        """Handle worker management commands"""
        try:
            if arg1 == 'status':
                components = await self.api.get_components(arg3)
                if components.success:
                    for component in components.data:
                        result = await self.api.get_component_status(component)
                        if result.success:
                            self.console.print(f"{component}: {result.data}")
                        else:
                            self.console.print(f"[red]Error getting status: {result.error}[/]")
                return
            else:
                self.console.print(f"[red]Error: Invalid worker command: {arg1}[/]")

        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/]") 