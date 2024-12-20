from rich.console import Console
from rich.table import Table
from ..api import ClientAPI
from ..queue import ClientQueue, StreamLockedException
from typing import Optional, List, Dict, Any
import asyncio
import yaml

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
        table.add_row("program add <name>", "Add a new program")
        table.add_row("program del <name>", "Delete a program")
        table.add_row("program import <file>", "Import programs from file")
        
        # System commands
        table.add_row("system killjob <worker_id>", "Kill job on worker")
        table.add_row("system cache flush", "Flush system cache")
        table.add_row("system cache show", "Show cache contents")
        table.add_row("system queue show (worker|job|data)", "Show queue information")
        table.add_row("system queue messages (worker|job|data)", "Show queue messages")
        table.add_row("system queue flush (worker|job|data)", "Flush queue")
        table.add_row("system queue (lock|unlock) (worker|job|data)", "Lock/unlock queue")
        table.add_row("system workers status", "Show workers status")
        table.add_row("system workers list", "List all workers")
        table.add_row("system pause (dataprocessor|jobprocessor|worker) [id]", "Pause component")
        table.add_row("system unpause (dataprocessor|jobprocessor|worker) [id]", "Unpause component")
        table.add_row("system report (worker|jobprocessor|dataprocessor) [id]", "Get component report")
        
        # Config commands
        table.add_row("config add cidr <cidr>", "Add CIDR to current program")
        table.add_row("config add scope <scope>", "Add scope to current program")
        table.add_row("config del cidr <cidr>", "Remove CIDR from current program")
        table.add_row("config del scope <scope>", "Remove scope from current program")
        table.add_row("config list cidr", "List CIDRs of current program")
        table.add_row("config list scope", "List scopes of current program")
        table.add_row("config database drop", "Drop current program's database")
        
        # Asset commands
        table.add_row("add domain <domain>", "Add domain to current program")
        table.add_row("add ip <ip>", "Add IP to current program")
        table.add_row("add url <url>", "Add URL to current program")
        table.add_row("del domain <domain>", "Delete domain from current program")
        table.add_row("del ip <ip>", "Delete IP from current program")
        table.add_row("del url <url>", "Delete URL from current program")
        
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

    async def handle_system_commands(self, component: str, action: str, args: List[str] = None) -> None:
        """Handle system management commands"""
        try:
            if component == 'killjob':
                worker_id = action
                
                # Get list of workers
                workers = await self.api.get_workers()
                if not workers.success:
                    self.console.print(f"[red]Error: Could not get workers - {workers.error}[/]")
                    return
                    
                # Handle 'all' option
                if worker_id.lower() == 'all':
                    if not workers.data:
                        self.console.print("[yellow]No active workers found[/]")
                        return
                        
                    self.console.print("[yellow]Sending kill command to all workers...[/]")
                    for worker in workers.data:
                        try:
                            result = await self.api.kill_job(worker)
                            if result.success:
                                self.console.print(f"[green]Kill command sent successfully to worker {worker}[/]")
                            else:
                                self.console.print(f"[red]Error sending kill command to worker {worker}: {result.error}[/]")
                        except Exception as e:
                            self.console.print(f"[red]Error killing job on worker {worker}: {str(e)}[/]")
                    
                    # Wait briefly to check all workers' status
                    await asyncio.sleep(1)
                    for worker in workers.data:
                        try:
                            status = await self.api.get_worker_status(worker)
                            if status.success and status.data:
                                self.console.print(f"[yellow]Worker {worker} status: {status.data}[/]")
                        except Exception as e:
                            self.console.print(f"[red]Could not get status for worker {worker}: {str(e)}[/]")
                            
                else:
                    # Single worker kill logic
                    try:
                        if not any(str(w) == str(worker_id) for w in workers.data):
                            self.console.print(f"[red]Error: Worker '{worker_id}' not found[/]")
                            return
                        
                        # Send kill command
                        result = await self.api.kill_job(worker_id)
                        if result.success:
                            self.console.print(f"[green]Kill command sent successfully to worker {worker_id}[/]")
                        else:
                            self.console.print(f"[red]Error sending kill command: {result.error}[/]")
                            
                        # Wait briefly to check worker status
                        await asyncio.sleep(1)
                        status = await self.api.get_worker_status(worker_id)
                        if status.success and status.data:
                            self.console.print(f"[yellow]Worker {worker_id} status: {status.data}[/]")
                        
                    except Exception as e:
                        self.console.print(f"[red]Error killing job on worker {worker_id}: {str(e)}[/]")

            elif component == 'workers':
                if action == 'status':
                    workers = await self.api.get_workers()
                    if not workers.success:
                        self.console.print(f"[red]Error getting workers: {workers.error}[/]")
                        return
                        
                    for worker_id in workers.data:
                        status = await self.api.get_worker_status(worker_id)
                        if status.success and status.data:
                            self.console.print(f"Worker {worker_id}: {status.data}")
                        else:
                            self.console.print(f"Worker {worker_id}: No status available")
                            
                elif action == 'list':
                    workers = await self.api.get_workers()
                    if not workers.success:
                        self.console.print(f"[red]Error getting workers: {workers.error}[/]")
                        return
                        
                    if workers.data:
                        self.console.print("\nActive Workers:")
                        for worker in workers.data:
                            self.console.print(f"- {worker}")
                    else:
                        self.console.print("[yellow]No active workers found[/]")
                        
            elif component == 'cache':
                if action == 'flush':
                    await self.api.flush_cache()
                    self.console.print("[green]Cache flushed[/]")
                elif action == 'show':
                    keys = await self.api.show_cache_keys_values()
                    [self.console.print(k) for k in keys]
                    
            elif component == 'queue':
                # Determine which stream to use
                stream = None
                if 'worker' in args:
                    stream = 'FUNCTION_EXECUTE'
                elif 'job' in args:
                    stream = 'FUNCTION_OUTPUT'
                elif 'data' in args:
                    stream = 'RECON_DATA'

                if action == 'show':
                    try:
                        result = await self.client_queue.get_stream_info(stream)
                        if result:
                            # Create rich table for display
                            table = Table()
                            headers = result[0].keys()
                            for header in headers:
                                table.add_column(header.capitalize())
                            
                            for row in result:
                                table.add_row(*[str(val) for val in row.values()])
                            
                            self.console.print(table)
                        else:
                            self.console.print("[yellow]No queue information available[/]")
                    except StreamLockedException as e:
                        self.console.print(f"[red]Error: Stream is locked - {str(e)}[/]")
                    except Exception as e:
                        self.console.print(f"[red]Error getting queue info: {str(e)}[/]")

                elif action == 'messages':
                    try:
                        result = await self.client_queue.get_stream_messages(stream)
                        if result:
                            # Create rich table for display
                            table = Table()
                            headers = result[0].keys()
                            for header in headers:
                                table.add_column(header.capitalize())
                            
                            for row in result:
                                table.add_row(*[str(val) for val in row.values()])
                            
                            self.console.print(table)
                        else:
                            self.console.print("[yellow]No messages found[/]")
                    except StreamLockedException as e:
                        self.console.print(f"[red]Error: Stream is locked - {str(e)}[/]")
                    except Exception as e:
                        self.console.print(f"[red]Error getting messages: {str(e)}[/]")

                elif action == 'flush':
                    try:
                        result = await self.client_queue.flush_stream(stream)
                        self.console.print(f"[green]{result}[/]")
                    except StreamLockedException as e:
                        self.console.print(f"[red]Error: Stream is locked - {str(e)}[/]")
                    except Exception as e:
                        self.console.print(f"[red]Error flushing stream: {str(e)}[/]")

                elif action in ['lock', 'unlock']:
                    try:
                        if action == 'lock':
                            result = await self.client_queue.lock_stream(stream)
                        else:
                            result = await self.client_queue.unlock_stream(stream)
                        self.console.print(f"[green]{result}[/]")
                    except Exception as e:
                        self.console.print(f"[red]Error {action}ing stream: {str(e)}[/]")

            elif component in ['pause', 'unpause']:
                processor_type = action
                component_id = args[0] if args else None
                if component == 'pause':
                    result = await self.api.pause_processor(processor_type, component_id)
                else:
                    result = await self.api.unpause_processor(processor_type, component_id)
                self.console.print(result['message'])
                
            elif component == 'report':
                component_id = args[0] if args else None
                result = await self.api.get_component_report(action, component_id)
                if result['status'] == 'success':
                    for report in result['reports']:
                        if 'report' in report:
                            self.console.print(f"\nReport from {report.get('processor_id', 'unknown')}:")
                            self.console.print(report['report'])
                else:
                    self.console.print(f"[red]Error: {result['message']}[/]")
                    
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