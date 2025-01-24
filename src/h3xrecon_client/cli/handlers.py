from rich.console import Console
from rich.table import Table
from ..api import ClientAPI
from ..config import ClientConfig
from ..queue import ClientQueue, StreamLockedException
from typing import Optional, List, Dict, Any
import yaml
import uuid
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
        table.add_row("system status flush (all|recon|parsing|data)", "Flush system status")
        
        # Worker commands
        table.add_row("worker list (recon|parsing|data|all)", "List components")
        table.add_row("worker status (recon|parsing|data|componentid|all)", "Show component status")
        table.add_row("worker killjob (componentid|all)", "Kill job on worker")
        table.add_row("worker ping <componentid>", "Ping a component")
        table.add_row("worker pause (recon|parsing|data|componentid|all)", "Pause component")
        table.add_row("worker unpause (recon|parsing|data|componentid|all)", "Unpause component")
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
        table.add_row("list websites", "List websites")
        table.add_row("list websites_paths", "List websites paths")
        table.add_row("list services", "List services")
        table.add_row("list nuclei [--severity <sev>]", "List nuclei findings")
        table.add_row("list certificates", "List certificates")
        table.add_row("list screenshots", "List screenshots")
        table.add_row("show domains [--resolved] [--unresolved]", "Show domains in table format")
        table.add_row("show ips [--resolved] [--unresolved]", "Show IPs in table format")
        table.add_row("show websites", "Show websites in table format")
        table.add_row("show websites_paths", "Show websites paths in table format")
        table.add_row("show services", "Show services in table format")
        table.add_row("show nuclei [--severity <sev>]", "Show nuclei findings in table format")
        table.add_row("show certificates", "Show certificates in table format")
        table.add_row("show screenshots", "Show screenshots in table format")
        
        # Job commands
        table.add_row("sendjob <function> <target> [params...] [--force]", "Send job to worker")
        table.add_row("meta <function> <target> [params...] [--force]", "Send meta job to worker")
        
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
            elif arg1 == 'database':
                if not arg2:
                    self.console.print("[red]Error: Missing backup file path[/]")
                    return
                result = await self.api.backup_database(arg2)
                if result.success:
                    self.console.print(f"[green]Database backup created at {arg2}[/]")
                else:
                    self.console.print(f"[red]Error creating backup: {result.error}[/]")
            else:
                self.console.print(f"[red]Error: Invalid system command: {arg1}[/]")

        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/]")

    async def handle_system_commands_with_3_args(self, arg1: str, arg2: str, arg3: str = None, filter: str = None) -> None:
        """Handle system management commands"""
        try:
            if arg1 == 'status' and arg2 == 'flush':
                if arg3 in ['recon', 'parsing', 'data', 'all']:
                    components = await self.api.get_components(arg3)
                    if components.success:
                        for component in components.data:
                            result = await self.api.flush_component_status(component)
                            if result.success:
                                self.console.print(f"[green]Status flushed successfully for {component}[/]")
                            else:
                                self.console.print(f"[red]Error flushing status: {result.error}[/]")
                return
            elif arg1 == 'database' and arg2 in ['backup', 'restore']:
                if not arg3:
                    self.console.print("[red]Error: Missing backup file path[/]")
                    return
                    
                if arg2 == 'backup':
                    result = await self.api.backup_database(arg3)
                    if result.success:
                        self.console.print(f"[green]Database backup created at {arg3}[/]")
                    else:
                        self.console.print(f"[red]Error creating backup: {result.error}[/]")
                else:  # restore
                    result = await self.api.restore_database(arg3)
                    if result.success:
                        self.console.print(f"[green]Database restored from {arg3}[/]")
                    else:
                        self.console.print(f"[red]Error restoring database: {result.error}[/]")
                return
            elif arg1 == 'queue':
                # Determine which stream to use
                streams = []
                if arg3 == 'recon':
                    streams.append('RECON_INPUT')
                elif arg3 == 'parsing':
                    streams.append('PARSING_INPUT')
                elif arg3 == 'data':
                    streams.append('DATA_INPUT')
                elif arg3 == 'all':
                    streams.append('RECON_INPUT')
                    streams.append('PARSING_INPUT')
                    streams.append('DATA_INPUT')
                else:
                    self.console.print(f"[red]Error: Invalid stream type: {arg3}[/]")
                    return

                for stream in streams:
                    if arg2 == 'show':
                        info = await self.client_queue.get_stream_info(stream)
                        self.console.print(info)
                    elif arg2 == 'messages':
                        try:
                            subject = None
                            if filter:
                                subject = f"recon.input.{filter}"
                            messages = await self.client_queue.get_stream_messages(stream, subject=subject)
                            for msg in messages:
                                self.console.print(msg["data"])
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

    async def handle_config_commands(self, action: str, type: str, program: str, value: Optional[str] = None, wildcard: bool = False, regex: Optional[str] = None) -> None:
        """Handle configuration commands"""
        try:
            if action == 'list':
                if type == 'cidr':
                    result = await self.api.get_program_cidr(program)
                    [self.console.print(r.get('cidr')) for r in result.data]
                elif type == 'scope':
                    result = await self.api.get_program_scope(program)
                    if wildcard:
                        [self.console.print(r.get('domain')) for r in result.data if r.get('wildcard')]
                    else:
                        [self.console.print(r.get('regex')) for r in result.data]

            elif action == 'show' and type == 'scope':
                result = await self.api.get_program_scope(program)
                if wildcard:
                    [self.display_table_results([r for r in result.data if r.get('wildcard')])]
                else:
                    [self.display_table_results(result.data)]
            
            elif action == 'add' and value:
                if type == 'cidr':
                    result = await self.api.add_program_cidr(program, value)
                elif type == 'scope':
                    result = await self.api.add_program_scope(program, value, wildcard, regex)
                if result['inserted']:
                    self.console.print(f"[green] Scope '{value}' added successfully[/]")
                else:
                    self.console.print(f"[yellow] Scope '{value}' already exists[/]")
                    
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
                if result.success:
                    return [{'Domain': d['domain'], 
                            'IPs': d.get('resolved_ips', 'N/A'), 
                            'CNAMEs': d.get('cnames', 'N/A'), 
                            'Catchall': d.get('is_catchall', 'unknown')} for d in result.data]
                
            elif type_name == 'ips':
                if resolved:
                    result = await self.api.get_reverse_resolved_ips(program)
                elif unresolved:
                    result = await self.api.get_not_reverse_resolved_ips(program)
                else:
                    result = await self.api.get_ips(program)
                return [{'IP': ip['ip'], 
                        'PTR': ip.get('ptr', 'N/A'), 
                        'Cloud Provider': ip.get('cloud_provider', 'unknown')} for ip in result.data]
                
            elif type_name == 'websites':
                result = await self.api.get_websites(program)
                return [{'URL': website['url'], 
                        'Host': website.get('host', 'N/A'), 
                        'Port': website.get('port', 'N/A'), 
                        'Scheme': website.get('scheme', 'N/A'), 
                        'Techs': website.get('techs', 'N/A')} for website in result.data]
            elif type_name == 'websites_paths':
                result = await self.api.get_websites_paths(program)
                return [{'URL': website.get('url', 'N/A'), 
                        'Path': website.get('path', 'N/A'), 
                        'Final Path': website.get('final_path', 'N/A'), 
                        'Status Code': website.get('status_code', 'N/A'), 
                        'Content Type': website.get('content_type', 'N/A')} for website in result.data]
            elif type_name == 'services':
                result = await self.api.get_services(program)
                return [{
                    'IP': service['ip'],
                    'Port': service.get('port', 'N/A'),
                    'Service': service.get('service', 'unknown'),
                    'Protocol': service.get('protocol', 'N/A'),
                    'Resolved Hostname': service.get('ptr', 'unknown')
                } for service in result.data]
                
            elif type_name == 'nuclei':
                result = await self.api.get_nuclei(program, severity=severity)
                return [{
                    'Target': finding['url'],
                    'Template': finding.get('template_id', 'unknown'),
                    'Severity': finding.get('severity', 'unknown'),
                    'Matcher Name': finding.get('name', 'N/A')
                } for finding in result.data]
                
            elif type_name == 'certificates':
                result = await self.api.get_certificates(program)
                return [{
                    'Subject CN': cert.get('subject_cn', 'unknown'),
                    'Issuer': cert.get('issuer', 'unknown'),
                    'Valid Until': cert.get('valid_until', 'unknown')
                } for cert in result.data]
            elif type_name == 'screenshots':
                result = await self.api.get_screenshots(program)
                return [{
                    'URL': screenshot.get('url', 'unknown'),
                    'Filepath': screenshot.get('filepath', 'unknown'),
                    'MD5 Hash': screenshot.get('md5_hash', 'unknown')
                } for screenshot in result.data]

        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/]")
            return []

    async def handle_show_commands(self, type_name, program, resolved=False, unresolved=False, severity=None):
        """Handle show commands."""
        items = await self.handle_list_commands(type_name, program, resolved, unresolved, severity)
        if items:
            self.display_table_results(items)

    async def handle_dns_command(self, program: str, domain: str = None):
        """Handle DNS record display command.
        
        Args:
            program (str): Program name
            domain (str, optional): Domain to filter records by
        
        Returns:
            List[Dict]: List of DNS records
        """
        try:
            result = await self.api.get_dns_records(program, domain)
            if result.success:
                # Group records by domain
                records_by_domain = {}
                for record in result.data:
                    domain = record['domain']
                    if domain not in records_by_domain:
                        records_by_domain[domain] = []
                    records_by_domain[domain].append(record)

                # Print records grouped by domain
                for domain, records in records_by_domain.items():
                    # Print domain header
                    self.console.print(f"\n[bold blue]# Zone: {domain}[/bold blue]")
                    self.console.print("[dim]# Records: {0}[/dim]".format(len(records)))
                    self.console.print("[dim]" + "─" * 80 + "[/dim]")

                    # Sort records by type and hostname
                    records.sort(key=lambda x: (x['dns_type'], x['hostname']))

                    # Find the maximum lengths for proper spacing
                    max_hostname = max(len(r['hostname']) for r in records)
                    max_ttl = max(len(str(r['ttl'])) for r in records)
                    max_type = max(len(r['dns_type']) for r in records)
                    max_class = max(len(r['dns_class']) for r in records)

                    # Print column headers
                    self.console.print(
                        f"[dim]{'NAME'.ljust(max_hostname)} "
                        f"{'TTL'.rjust(max_ttl)} "
                        f"{'CLASS'.ljust(max_class)} "
                        f"{'TYPE'.ljust(max_type)} "
                        f"VALUE[/dim]"
                    )
                    self.console.print("[dim]" + "─" * 80 + "[/dim]")

                    # Print each record with proper spacing and colors
                    for record in records:
                        hostname = record['hostname'].ljust(max_hostname)
                        ttl = str(record['ttl']).rjust(max_ttl)
                        dns_class = record['dns_class'].ljust(max_class)
                        dns_type = record['dns_type'].ljust(max_type)
                        value = record['value']

                        # Color-code different record types
                        type_color = {
                            'A': 'green',
                            'AAAA': 'green',
                            'CNAME': 'yellow',
                            'MX': 'blue',
                            'TXT': 'magenta',
                            'NS': 'cyan',
                            'SOA': 'red',
                            'SRV': 'blue',
                            'PTR': 'yellow'
                        }.get(record['dns_type'], 'white')

                        # Format value based on record type
                        if record['dns_type'] == 'MX':
                            # Split priority and target for MX records
                            try:
                                priority, mx_target = value.split(' ', 1)
                                value = f"[dim]{priority}[/dim] {mx_target}"
                            except ValueError:
                                pass
                        elif record['dns_type'] == 'TXT':
                            value = f'"{value}"'  # Quote TXT record values

                        self.console.print(
                            f"{hostname} "
                            f"[dim]{ttl}[/dim] "
                            f"{dns_class} "
                            f"[{type_color}]{dns_type}[/{type_color}] "
                            f"{value}"
                        )

                    self.console.print()  # Add empty line between domains
                return result.data
            else:
                self.console.print(f"[red]Error getting DNS records: {result.error}[/]")
                return None
        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/]")
            return None
    
    async def handle_workflow_command(self, name: str, program: str, targets: List[str], force: bool = False):
        """Handle workflow command"""
        try:
            if not name:
                self.console.print("[red]Error: Workflow name is required[/]")
                return
                
            if not program:
                self.console.print("[red]Error: Program name is required[/]")
                return
                
            if not targets:
                self.console.print("[red]Error: At least one target is required[/]")
                return

            # First check if program exists
            programs = await self.api.get_programs()
            if not programs.success:
                self.console.print(f"[red]Error: Could not verify program: {programs.error}[/]")
                return
                
            if not any(p.get("name") == program for p in programs.data):
                self.console.print(f"[red]Error: Program '{program}' not found[/]")
                return

            total_targets = len(targets)
            successful_jobs = 0
            jobs = ClientConfig().workflows.get(name, {}).get('jobs', [])
            if not jobs:
                self.console.print(f"[red]Error: Unknown workflow: {name}[/]")
                return
            for target in targets:
                for job in jobs:
                    job["params"] = job.get("params", {})
                    job['params']['target'] = target
                    job['program_name'] = program
                    job['params']['extra_params'] = job.get("params", {}).get("extra_params", [])
                    job["force"] = job.get("force", force)
                    job["trigger_new_jobs"] = job.get("trigger_new_jobs", True)
                    result = await self.api.send_job(**job)
                    if result and result.success:
                        successful_jobs += 1
                    else:
                        error_msg = result.error if result else "Unknown error"
                        self.console.print(f"[red]Error sending job for target {target}: {error_msg}[/]")

            if successful_jobs == total_targets * len(jobs):
                self.console.print(f"[green]All {total_targets * len(jobs)} workflow jobs sent successfully[/]")
            else:
                self.console.print(f"[yellow]{successful_jobs} out of {total_targets * len(jobs)} jobs sent successfully[/]")
                
        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/]")
    
    async def handle_sendjob_command(self, 
                                     function_name: str, 
                                     targets: List[str], 
                                     program: str, 
                                     force: bool = False, 
                                     params: List[str] = None, 
                                     wordlist: str = None, 
                                     no_trigger: bool = False, 
                                     timeout: int = None,
                                     mode: str = None,
                                     response_id: bool = False) -> None:
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

            total_targets = len(targets)
            successful_jobs = 0 
            for target in targets:
                
                job = {
                    "function_name": function_name,
                    "program_name": program,
                    "trigger_new_jobs": not no_trigger,
                    "params": {
                        "target": target,
                        "extra_params": params or [],
                        "wordlist": wordlist,
                        "timeout": timeout,
                        "mode": mode
                    },
                    "force": force,
                    "response_id": response_id
                }
                if response_id:
                    response_sub = await self.client_queue.create_jobrequest_response_sub(job['response_id'])
                result = await self.api.send_job(**job)
                self.console.print(f"Job sent for target {target}")
                if response_id:
                    self.console.print(f"Waiting for acknowledgement from a recon worker...")
                    response = await self.api.wait_for_response(response_id=job['response_id'], timeout=120, response_sub=response_sub)
                    if response:
                        self.console.print(f"{response.get('component_id')} - Status: {response.get('status')} - Execution ID: {response.get('execution_id')}")
                        successful_jobs += 1
                    else:
                        self.console.print(f"[red]Error: No response received from recon worker[/]")
                else:
                    successful_jobs += 1

            if successful_jobs == total_targets:
                self.console.print(f"[green]All {total_targets} jobs sent successfully[/]")
            else:
                self.console.print(f"[yellow]{successful_jobs} out of {total_targets} jobs sent successfully[/]")
            if response_id:
                self.console.print("Waiting for completion confirmation from parsing worker...")
                response = await self.api.wait_for_response(response_id=job['response_id'], timeout=120, response_sub=response_sub)
                if response:
                    self.console.print(f"{response.get('component_id')} - Status: {response.get('status')} - Execution ID: {response.get('execution_id')}")
                else:
                    self.console.print(f"[red]Error: No response received from recon worker[/]")
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
                        result = await self.api.add_program_scope(name, **scope)
                        if result['inserted']:
                            self.console.print(f"[green]Scope '{scope}' added successfully[/]")
                        else:
                            self.console.print(f"[yellow]Scope '{scope}' already exists[/]")
                    
                    # Add CIDR
                    for cidr in program.get('cidr', []):
                        result = await self.api.add_program_cidr(name, cidr)
                        if result['inserted']:
                            self.console.print(f"[green]CIDR '{cidr}' added successfully[/]")
                        else:
                            self.console.print(f"[yellow]CIDR '{cidr}' already exists[/]")
                            
                    self.console.print("[green]Program imported successfully[/]")
                    
        except Exception as e:
            self.console.print(f"[red]Error importing programs: {str(e)}[/]")

    def display_table_results(self, data: List[Any]) -> None:
        """Display results in table format"""
        if not data:
            self.console.print("[yellow]No results found[/]")
            return

        table = Table()
        
        # Handle both dictionary and tuple data formats
        if isinstance(data[0], dict):
            headers = list(data[0].keys())
            for header in headers:
                table.add_column(str(header))
            
            for row in data:
                table.add_row(*[str(row[h]) for h in headers])
        else:
            # For legacy tuple data, use predefined headers based on the data structure
            headers = ['Domain', 'IPs', 'CNAMEs', 'Catchall']  # Default headers for domain data
            for header in headers:
                table.add_column(header)
            
            for row in data:
                # Convert all values to strings and handle None values
                formatted_row = [
                    str(val) if val is not None else 'None' 
                    for val in row
                ]
                table.add_row(*formatted_row)

        self.console.print(table)

    def display_list_results(self, type_name: str, data: List[Dict[str, Any]]) -> None:
        """Display results in list format"""
        if not data:
            self.console.print("[yellow]No results found[/]")
            return

        for item in data:
            if type_name == 'domains':
                if 'IPs' in item:
                    self.console.print(f"{item['Domain']} -> {item['IPs']}")
                else:
                    self.console.print(item['Domain'])
            elif type_name == 'ips':
                if 'PTR' in item:
                    self.console.print(f"{item['IP']} -> {item['PTR']}")
                else:
                    self.console.print(item['IP'])
            elif type_name == 'services':
                self.console.print(f"{item['Protocol']}:{item['IP']}:{item['Port']}")
            elif type_name == 'certificates':
                self.console.print(item['Subject CN'])
            elif type_name == 'websites':
                self.console.print(item['URL'])
            elif type_name == 'websites_paths':
                self.console.print(f"{item['URL']}{item['Path']}")
            elif type_name == 'nuclei':
                self.console.print(f"{item['Target']} - {item['Template']} ({item['Severity']})")
            elif type_name == 'screenshots':
                self.console.print(f"{item['URL']} -> {item['Filepath']}")
            else:
                self.console.print(str(item))

    async def handle_add_commands(self, type_name: str, program: str, items: List[str], no_trigger: bool = False) -> None:
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
            result = await self.api.add_item(type_name, program, items, no_trigger)
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
                            success = resp.get('success')
                            status = f"[green]{resp.get('status')}[/]" if success else "[red]failed[/]"
                            self.console.print(f"{comp_id}: {status}")
                            if not success:
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
                valid_components = ['recon', 'parsing', 'data', 'all']
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
                            self.console.print(f"- {component if isinstance(component, bytes) else component}")
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