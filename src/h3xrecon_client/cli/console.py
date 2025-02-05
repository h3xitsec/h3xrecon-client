from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import clear
from .handlers import CommandHandlers
import math
import shutil
import json
import os
import shlex
from typing import Optional

__all__ = ['H3xReconConsole']

class H3xReconConsole(CommandHandlers):
    def __init__(self):
        super().__init__()
        self.session = PromptSession()
        self.running = True
        self.config_file = os.path.expanduser('~/.h3xrecon/config.json')
        
        # Define command completions
        self.completer = NestedCompleter.from_nested_dict({
            'use': None,
            'program': {
                'list': None,
                'add': None,
                'del': None,
                'import': None,
            },
            'add': {
                'domain': {
                    '--stdin': None,
                },
                'ip': {
                    '--stdin': None,
                },
                'url': {
                    '--stdin': None,
                },
            },
            'del': {
                'domain': None,
                'ip': None,
                'url': None,
            },
            'system': {
                'queue': {
                    'show': {
                        'worker': None,
                        'job': None,
                        'data': None,
                    },
                    'messages': {
                        'worker': None,
                        'job': None,
                        'data': None,
                    },
                    'flush': {
                        'worker': None,
                        'job': None,
                        'data': None,
                    },
                },
                'cache': {
                    'flush': None,
                    'show': None,
                },
                'status': {
                    'flush': {
                        'all': None,
                        'recon': None,
                        'parsing': None,
                        'data': None,
                    }
                }
            },
            'worker': {
                'list': {
                    'recon': None,
                    'parsing': None,
                    'data': None,
                    'all': None,
                },
                'status': {
                    'recon': None,
                    'parsing': None,
                    'data': None,
                    'all': None,
                },
                'killjob': {
                    'all': None,
                },
                'ping': None,
                'pause': {
                    'recon': None,
                    'parsing': None,
                    'data': None,
                    'all': None,
                },
                'unpause': {
                    'recon': None,
                    'parsing': None,
                    'data': None,
                    'all': None,
                },
                'report': None,
            },
            'config': {
                'add': {
                    'cidr': None,
                    'scope': None,
                },
                'del': {
                    'cidr': None,
                    'scope': None,
                },
                'list': {
                    'cidr': None,
                    'scope': None,
                },
                'database': {
                    'drop': None,
                }
            },
            'sendjob': {
                '--force': None,
            },
            'list': {
                'domains': {
                    '--resolved': None,
                    '--unresolved': None,
                },
                'ips': {
                    '--resolved': None,
                    '--unresolved': None,
                },
                'websites': None,
                'websites_paths': None,
                'services': None,
                'nuclei': {
                    '--severity': None,
                },
                'certificates': None,
                'screenshots': None,
            },
            'show': {
                'domains': {
                    '--resolved': None,
                    '--unresolved': None,
                },
                'ips': {
                    '--resolved': None,
                    '--unresolved': None,
                },
                'websites': None,
                'websites_paths': None,
                'services': None,
                'nuclei': {
                    '--severity': None,
                },
                'certificates': None,
                'screenshots': None,
            },
            'help': None,
            'exit': None,
        })
        
        self.style = Style.from_dict({
            'prompt': 'ansicyan bold',
        })
        
        # Get terminal size and set items per page
        terminal_height = shutil.get_terminal_size().lines
        self.items_per_page = terminal_height - 6
        self.current_page = 1
        self.total_pages = 1
        self.current_items = []
        
        # Add custom keybindings for pagination
        self.pagination_bindings = {
            'n': self.next_page,
            'p': self.previous_page,
            'q': self.quit_pagination,
        }
        
        # Load config synchronously
        self.load_active_program()

    def save_active_program(self):
        """Save active program to config file"""
        try:
            # Load existing config
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Update or create client section
            if 'client' not in config:
                config['client'] = {}
            config['client']['active_program'] = self.current_program
            
            # Save updated config
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
                
        except Exception as e:
            self.console.print(f"[red]Error saving active program: {str(e)}[/]")

    def load_active_program(self):
        """Load active program from config file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.current_program = config.get('client', {}).get('active_program')
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not load active program: {str(e)}[/]")
            self.current_program = None

    async def validate_active_program(self) -> bool:
        """Validate that a program is selected and exists"""
        if not self.current_program:
            self.console.print("[red]No program selected. Use 'use <program>' first[/red]")
            return False

        try:
            programs = await self.api.get_programs()
            if not any(p.get("name") == self.current_program for p in programs.data):
                self.console.print(f"[red]Program '{self.current_program}' not found[/red]")
                self.current_program = None  # Reset invalid program
                self.save_active_program()
                return False
            return True
        except Exception as e:
            self.console.print(f"[red]Error validating program: {str(e)}[/red]")
            return False

    async def next_page(self, event=None):
        """Go to next page"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            return True
        return False

    async def previous_page(self, event=None):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            return True
        return False

    async def quit_pagination(self, event=None):
        """Quit pagination"""
        return True

    async def display_paginated_items(self, items, headers=None):
        """Display items with pagination"""
        self.current_items = items
        self.total_pages = math.ceil(len(items) / self.items_per_page)
        self.current_page = 1
        
        # Create a custom session for pagination with single-key bindings
        pagination_session = PromptSession(
            key_bindings=self.create_pagination_bindings()
        )
        
        while True:
            clear()
            if headers:
                # Table format for show command
                await self.show_current_page(headers)
            else:
                # Simple list format for list command
                start_idx = (self.current_page - 1) * self.items_per_page
                end_idx = start_idx + self.items_per_page
                page_items = self.current_items[start_idx:end_idx]
                for item in page_items:
                    self.console.print(item)
            
            # Show navigation help
            nav_text = (
                f"\nPage {self.current_page}/{self.total_pages}\n"
                "Navigation: Press "
                "[cyan]n[/cyan] for next page, "
                "[cyan]p[/cyan] for previous page, "
                "[cyan]q[/cyan] to quit"
            )
            self.console.print(nav_text)
            
            # Get single keypress
            key = await pagination_session.app.run_async()
            if key == 'q':
                break
            
            # Update terminal height in case of resize
            terminal_height = shutil.get_terminal_size().lines
            self.items_per_page = terminal_height - 6

    def create_pagination_bindings(self):
        """Create key bindings for pagination"""
        from prompt_toolkit.key_binding import KeyBindings
        kb = KeyBindings()
        
        @kb.add('n')
        async def _(event):
            if await self.next_page():
                event.app.exit()
            
        @kb.add('p')
        async def _(event):
            if await self.previous_page():
                event.app.exit()
            
        @kb.add('q')
        async def _(event):
            event.app.exit('q')
            
        return kb

    async def show_current_page(self, headers=None):
        """Show the current page of items"""
        # Get terminal size
        terminal_width = shutil.get_terminal_size().columns
        
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.current_items[start_idx:end_idx]
        
        if headers:
            # Calculate column widths based on content and terminal width
            col_widths = self.calculate_column_widths(headers, page_items, terminal_width)
            
            # Print headers
            header_row = " | ".join(
                f"{h:<{w}}" for h, w in zip(headers, col_widths)
            )
            self.console.print(f"[bold]{header_row}[/]")
            self.console.print("-" * min(sum(col_widths) + (len(headers) - 1) * 3, terminal_width))
            
            # Print items
            header_to_key = {
                'Domain': 'Domain',
                'CNAMEs': 'CNAMEs',
                'CatchAll': 'Catchall',
                'IP': 'IP',
                'PTR': 'PTR',
                'Cloud Provider': 'CloudProvider',
                'URL': 'URL',
                'Host': 'Host',
                'Port': 'Port',
                'Scheme': 'Scheme',
                'Techs': 'Techs',
                'Path': 'Path',
                'Final Path': 'FinalPath',
                'Status Code': 'StatusCode',
                'Content Type': 'ContentType',
                'Service': 'Service',
                'Version': 'Version',
                'Template': 'Template',
                'Severity': 'Severity',
                'Name': 'Name',
                'Issuer': 'Issuer',
                'Valid Until': 'ValidUntil',
                'Screenshot': 'Screenshot',
                'MD5 Hash': 'MD5Hash'
            }
            
            for item in page_items:
                row_values = []
                for header in headers:
                    key = header_to_key.get(header, header)
                    value = item.get(key, '')
                    if isinstance(value, list):
                        value = ', '.join(str(v) for v in value if v is not None)
                    elif value is None:
                        value = ''
                    row_values.append(str(value))
                
                row = " | ".join(
                    f"{str(value):<{w}}" for value, w in zip(row_values, col_widths)
                )
                self.console.print(row)
        else:
            for item in page_items:
                self.console.print(str(item))

    def calculate_column_widths(self, headers, items, terminal_width):
        """Calculate optimal column widths based on content and terminal width"""
        # Get max width for each column
        widths = []
        header_to_key = {
            'Domain': 'Domain',
            'CNAMEs': 'CNAMEs',
            'CatchAll': 'Catchall',
            'IP': 'IP',
            'PTR': 'PTR',
            'Cloud Provider': 'CloudProvider',
            'URL': 'URL',
            'Host': 'Host',
            'Port': 'Port',
            'Scheme': 'Scheme',
            'Techs': 'Techs',
            'Path': 'Path',
            'Final Path': 'FinalPath',
            'Status Code': 'StatusCode',
            'Content Type': 'ContentType',
            'Service': 'Service',
            'Version': 'Version',
            'Template': 'Template',
            'Severity': 'Severity',
            'Name': 'Name',
            'Issuer': 'Issuer',
            'Valid Until': 'ValidUntil',
            'Screenshot': 'Screenshot',
            'MD5 Hash': 'MD5Hash'
        }

        for header in headers:
            key = header_to_key.get(header, header)
            # Get values for this column, handling potential missing keys
            column_content = []
            for item in items:
                value = item.get(key, '')
                if isinstance(value, list):
                    value = ', '.join(str(v) for v in value if v is not None)
                elif value is None:
                    value = ''
                column_content.append(str(value))
            column_content.append(header)  # Add header to content for width calculation
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

    async def handle_list_commands(self, type_name, program, resolved=False, unresolved=False, severity=None):
        """Handle list commands - simple list format"""
        items = await super().handle_list_commands(type_name, program, resolved, unresolved, severity)
        if items:
            # Get the main identifier for each asset type
            identifiers = []
            for item in items:
                if type_name == 'domains':
                    identifiers.append(item)  # domain
                elif type_name == 'ips':
                    identifiers.append(item)  # ip
                elif type_name == 'websites':
                    identifiers.append(item)  # url
                elif type_name == 'websites_paths':
                    identifiers.append(item)  # url
                elif type_name == 'services':
                    identifiers.append(f"{item}:{item[1]}")  # ip:port
                elif type_name == 'nuclei':
                    identifiers.append(f"{item} ({item[2]})")  # target (severity)
                elif type_name == 'certificates':
                    identifiers.append(item)  # domain
                elif type_name == 'screenshots':
                    identifiers.append(item)  # url
            
            # Display paginated list of identifiers
            await self.display_paginated_items(identifiers)
            
    async def handle_show_commands(self, type_name, program, resolved=False, unresolved=False, severity=None):
        """Handle show commands - detailed table format"""
        items = await super().handle_list_commands(type_name, program, resolved, unresolved, severity)
        if items:
            headers = self.get_headers_for_type(type_name)
            await self.display_paginated_items(items, headers)

    def get_headers_for_type(self, type_name):
        """Return headers based on asset type"""
        headers_map = {
            'domains': ['Domain', 'CNAMEs', 'IPs', 'CatchAll'],
            'ips': ['IP', 'PTR', 'Cloud Provider'],
            'websites': ['URL', 'Host', 'Port', 'Scheme', 'Techs'],
            'websites_paths': ['URL', 'Path', 'Final Path', 'Status Code', 'Content Type'],
            'services': ['IP', 'Port', 'Service', 'Version'],
            'nuclei': ['URL', 'Template', 'Severity', 'Name'],
            'certificates': ['Domain', 'Issuer', 'Valid Until'],
            'screenshots': ['URL', 'Screenshot', 'MD5 Hash']
        }
        return headers_map.get(type_name, None)

    async def handle_command(self, command: str) -> None:
        """Handle a console command"""
        if not command:
            return

        try:
            # Split command into parts while preserving quoted strings
            args = shlex.split(command)
            cmd = args[0].lower()

            if cmd == 'help':
                self.show_help()
                return

            if cmd == 'use':
                if len(args) != 2:
                    self.console.print("[red]Error: use command requires a program name[/red]")
                    return
                self.current_program = args[1]
                self.save_active_program()
                self.console.print(f"[green]Using program: {self.current_program}[/green]")
                return

            if cmd == 'exit' or cmd == 'quit':
                self.running = False
                return

            # For commands that require a program context
            program_required_commands = {'config', 'add', 'del', 'show', 'list', 'workflow', 'sendjob'}
            if cmd in program_required_commands and not await self.validate_active_program():
                return

            if cmd == 'program':
                if len(args) < 2:
                    self.console.print("[red]Error: program command requires an action[/red]")
                    return
                await self.handle_program_commands(args[1], args[2:] if len(args) > 2 else [])

            elif cmd == 'system':
                if len(args) < 3:
                    self.console.print("[red]Error: system command requires at least 2 arguments[/red]")
                    return
                if len(args) == 3:
                    await self.handle_system_commands_with_2_args(args[1], args[2])
                else:
                    await self.handle_system_commands_with_3_args(args[1], args[2], args[3])

            elif cmd == 'worker':
                if len(args) < 3:
                    self.console.print("[red]Error: worker command requires at least 2 arguments[/red]")
                    return
                if len(args) == 3:
                    await self.handle_worker_commands(args[1], args[2])
                else:
                    await self.handle_worker_commands_with_3_args(args[1], args[2], args[3])

            elif cmd == 'config':
                if len(args) < 3:
                    self.console.print("[red]Error: config command requires action and type[/red]")
                    return
                value = args[3] if len(args) > 3 else None
                await self.handle_config_commands(args[1], args[2], self.current_program, value)

            elif cmd == 'show':
                if len(args) < 2:
                    self.console.print("[red]Error: show command requires a type[/red]")
                    return
                await self.handle_show_commands(args[1], self.current_program)

            elif cmd == 'list':
                if len(args) < 2:
                    self.console.print("[red]Error: list command requires a type[/red]")
                    return
                await self.handle_list_commands(args[1], self.current_program)

            elif cmd == 'add':
                if len(args) < 3:
                    self.console.print("[red]Error: add command requires type and item[/red]")
                    return
                items = [args[2]]
                if '--stdin' in args:
                    items = []
                    for line in sys.stdin:
                        line = line.strip()
                        if line:
                            items.append(line)
                await self.handle_add_commands(args[1], self.current_program, items)

            elif cmd == 'workflow':
                if len(args) < 3:
                    self.console.print("[red]Error: workflow command requires name and target[/red]")
                    return
                targets = [args[2]]
                if args[2] == '-':
                    targets = []
                    for line in sys.stdin:
                        line = line.strip()
                        if line:
                            targets.append(line)
                await self.handle_workflow_command(args[1], self.current_program, targets)

            elif cmd == 'sendjob':
                if len(args) < 3:
                    self.console.print("[red]Error: sendjob command requires function name and target[/red]")
                    return
                params = args[3:] if len(args) > 3 else []
                await self.handle_sendjob_command(
                    function_name=args[1],
                    target=args[2],
                    params=params,
                    program=self.current_program
                )

            else:
                self.console.print(f"[red]Unknown command: {cmd}[/red]")

        except Exception as e:
            if self.debug:
                import traceback
                self.console.print(f"[red]Error: {str(e)}[/red]")
                self.console.print(traceback.format_exc())
            else:
                self.console.print(f"[red]Error: {str(e)}[/red]")

    async def run(self) -> None:
        """Run the interactive console"""
        # Load config synchronously
        self.load_active_program()
        
        # Validate program asynchronously
        await self.validate_active_program()
        
        self.console.print("[bold green]Welcome to H3xRecon Interactive Console[/]")
        self.console.print("Type 'help' for available commands\n")

        while self.running:
            try:
                prompt = f"h3xrecon{f'({self.current_program})' if self.current_program else ''}> "
                command = await self.session.prompt_async(
                    prompt,
                    completer=self.completer,
                    style=self.style,
                )
                await self.handle_command(command.strip())
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

    async def handle_system_commands(self, arg1: str, arg2: str, args: list = None) -> None:
        """Handle system management commands by delegating to appropriate handler"""
        if arg1 == 'queue' and len(args) == 0:
            await self.handle_system_commands_with_3_args(arg1, arg2, args[0] if args else None)
        else:
            if len(args) == 0:
                await self.handle_system_commands_with_2_args(arg1, arg2)
            else:
                await self.handle_system_commands_with_3_args(arg1, arg2, args[0])