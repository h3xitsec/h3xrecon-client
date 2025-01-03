from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.keys import Keys
from prompt_toolkit.filters import to_filter
from .handlers import CommandHandlers
import math
import shutil
import json
import os
import asyncio
import shlex

__all__ = ['H3xReconConsole']

class H3xReconConsole(CommandHandlers):
    def __init__(self):
        super().__init__()
        self.session = PromptSession()
        self.running = True
        self.current_program = None  # Initialize to None
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
                'urls': None,
                'services': None,
                'nuclei': {
                    '--severity': None,
                },
                'certificates': None,
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
                'urls': None,
                'services': None,
                'nuclei': {
                    '--severity': None,
                },
                'certificates': None,
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

    async def validate_active_program(self):
        """Validate that the loaded program exists"""
        if self.current_program:
            try:
                programs = await self.api.get_programs()
                if not any(p.get("name") == self.current_program for p in programs.data):
                    self.console.print(f"[yellow]Warning: Saved program '{self.current_program}' no longer exists[/]")
                    self.current_program = None
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not validate program: {str(e)}[/]")
                self.current_program = None

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
            for item in page_items:
                row = " | ".join(
                    f"{str(field):<{w}}" for field, w in zip(item, col_widths)
                )
                self.console.print(row)
        else:
            for item in page_items:
                self.console.print(str(item))

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

    async def handle_list_commands(self, type_name, program, resolved=False, unresolved=False, severity=None):
        """Handle list commands - simple list format"""
        items = await super().handle_list_commands(type_name, program, resolved, unresolved, severity)
        if items:
            # Get the main identifier for each asset type
            identifiers = []
            for item in items:
                if type_name == 'domains':
                    identifiers.append(item[0])  # domain
                elif type_name == 'ips':
                    identifiers.append(item[0])  # ip
                elif type_name == 'urls':
                    identifiers.append(item[0])  # url
                elif type_name == 'services':
                    identifiers.append(f"{item[0]}:{item[1]}")  # ip:port
                elif type_name == 'nuclei':
                    identifiers.append(f"{item[0]} ({item[2]})")  # target (severity)
                elif type_name == 'certificates':
                    identifiers.append(item[0])  # domain
            
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
            'domains': ['Domain', 'IP', 'CatchAll'],
            'ips': ['IP', 'Hostname', 'Status'],
            'urls': ['URL', 'Status', 'Title'],
            'services': ['IP', 'Port', 'Service', 'Version'],
            'nuclei': ['URL', 'Template', 'Severity', 'Name'],
            'certificates': ['Domain', 'Issuer', 'Valid Until']
        }
        return headers_map.get(type_name, None)

    async def handle_command(self, command: str) -> None:
        """Handle console commands"""
        if not command:
            return

        # Split command while preserving quoted strings
        try:
            parts = shlex.split(command)
        except ValueError as e:
            self.console.print(f"[red]Error parsing command: {str(e)}[/]")
            return

        cmd = parts[0].lower()

        if cmd == 'use' and len(parts) > 1:
            programs = await self.api.get_programs()
            program_name = parts[1]
            if any(p.get("name") == program_name for p in programs.data):
                self.current_program = program_name
                self.save_active_program()  # Save to config when program changes
                self.console.print(f"[green]Using program: {program_name}[/]")
            else:
                self.console.print(f"[red]Program '{program_name}' not found[/]")
        
        elif cmd == 'exit':
            self.running = False
            
        elif cmd == 'help':
            self.show_help()
            
        elif cmd == 'program' and len(parts) > 1:
            await self.handle_program_commands(parts[1], parts[2:])
            
        elif cmd == 'system' and len(parts) > 2:
            if parts[1] == 'queue' and len(parts) > 3:
                await self.handle_system_commands_with_3_args(parts[1], parts[2], parts[3])
            else:
                await self.handle_system_commands_with_2_args(parts[1], parts[2])
            
        elif cmd == 'worker' and len(parts) > 1:
            await self.handle_worker_commands(parts[1], parts[2] if len(parts) > 2 else None)
            
        elif cmd == 'config' and len(parts) > 2:
            if not self.current_program:
                self.console.print("[red]No program selected. Use 'use <program>' first[/]")
                return
            value = parts[3] if len(parts) > 3 else None
            await self.handle_config_commands(parts[1], parts[2], self.current_program, value)
            
        elif cmd in ['list', 'show'] and len(parts) > 1:
            if not self.current_program:
                self.console.print("[red]No program selected. Use 'use <program>' first[/]")
                return
                
            type_name = parts[1]
            resolved = '--resolved' in parts
            unresolved = '--unresolved' in parts
            severity = None
            if '--severity' in parts:
                try:
                    severity_idx = parts.index('--severity')
                    severity = parts[severity_idx + 1]
                except (ValueError, IndexError):
                    self.console.print("[red]Missing severity value[/]")
                    return
                    
            if cmd == 'list':
                await self.handle_list_commands(type_name, self.current_program, resolved, unresolved, severity)
            else:
                await self.handle_show_commands(type_name, self.current_program, resolved, unresolved, severity)
                
        elif cmd == 'sendjob' and len(parts) > 2:
            if not self.current_program:
                self.console.print("[red]No program selected. Use 'use <program>' first[/]")
                return
                
            function_name = parts[1]
            target = parts[2]
            force = '--force' in parts
            params = [p for p in parts[3:] if p != '--force']
            await self.handle_sendjob_command(function_name, target, self.current_program, force, params)
            
        elif cmd == 'add' and len(parts) > 2:
            if not self.current_program:
                self.console.print("[red]No program selected. Use 'use <program>' first[/]")
                return
                
            type_name = parts[1]
            items = []
            
            if '--stdin' in parts:
                # Read from stdin
                import sys
                for line in sys.stdin:
                    line = line.strip()
                    if line:  # Skip empty lines
                        items.append(line)
            else:
                items = [parts[2]]
                
            if type_name not in ['domain', 'ip', 'url']:
                self.console.print(f"[red]Invalid type '{type_name}'. Must be one of: domain, ip, url[/]")
                return
                
            await self.handle_add_commands(type_name, self.current_program, items)
            
        elif cmd == 'del' and len(parts) > 2:
            if not self.current_program:
                self.console.print("[red]No program selected. Use 'use <program>' first[/]")
                return
                
            type_name = parts[1]
            item = parts[2]
            if type_name not in ['domain', 'ip', 'url']:
                self.console.print(f"[red]Invalid type '{type_name}'. Must be one of: domain, ip, url[/]")
                return
                
            result = await self.api.remove_item(type_name, self.current_program, item)
            if result:
                self.console.print(f"[green]Successfully removed {type_name} '{item}' from program '{self.current_program}'[/]")
            else:
                self.console.print(f"[red]Failed to remove {type_name} '{item}'[/]")
            
        else:
            self.console.print(f"[red]Unknown command or missing arguments: {command}[/]")

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