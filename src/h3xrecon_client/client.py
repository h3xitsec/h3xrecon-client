#!/usr/bin/env python3
import asyncio
import sys
import re
import yaml
from docopt import docopt
from tabulate import tabulate
from loguru import logger
from .api import ClientAPI
from .queue import ClientQueue
from .config import ClientConfig

class Client:
    arguments = None
    
    def __init__(self, arguments):
        self.config = ClientConfig()
        if not self.config:
            logger.error("Failed to load client configuration")
            sys.exit(1)
        # Add console handler
        logger.remove()
        logger.add(
            sink=lambda msg: print(msg),
            level=self.config.logging.level,
            format=self.config.logging.format
        )
        logger.debug("Initializing Client")
        self.client_api = ClientAPI()
        self.client_queue = ClientQueue()

        # Initialize arguments only if properly parsed by docopt
        if arguments:
            self.arguments = arguments
        else:
            raise ValueError("Invalid arguments provided.")
    
    
    async def import_programs(self, file_path: str):
        """Import programs from a JSON file"""
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
            logger.debug(f"importing programs: {data}")
            for program in data['programs']:
                try:
                    print("Importing program: ", program.get('name'))
                    logger.debug(f"adding program: {program.get('name')}")
                    result = await self.client_api.add_program(program.get('name'))
                    if not result.success:
                        print(f"[-] Program '{program.get('name')}' already exists")
                    elif result.data:
                        print(f"[+] Program '{program.get('name')}' added successfully")
                    elif result.error:
                        print(f"[!] Error adding program: {result.error}")
                except Exception as e:
                    logger.error(f"Error adding program: {e}")
                if program.get('scope'):
                    for scope in program.get('scope'):
                        result = await self.client_api.add_program_scope(program.get('name'), scope)
                        if not result.success:
                            print(f"[-] Scope '{scope}' already exists in program '{program.get('name')}'")
                        elif result.data:
                            print(f"[+] Scope '{scope}' added successfully to program '{program.get('name')}'")
                        elif result.error:
                            print(f"[!] Error adding scope '{scope}' to program '{program.get('name')}': {result.error}")
                if program.get('cidr'):
                    for cidr in program.get('cidr'):
                        result = await self.client_api.add_program_cidr(program.get('name'), cidr)
                        if not result.success:
                            print(f"[-] CIDR '{cidr}' already exists in program '{program.get('name')}'")
                        elif result.data:
                            print(f"[+] CIDR '{cidr}' added successfully to program '{program.get('name')}'")
                        elif result.error:
                            print(f"[!] Error adding CIDR '{cidr}' to program '{program.get('name')}': {result.error}")
                print("")
        
    async def run(self):
        logger.debug("Running Client")
        # h3xrecon program
        try:
            if self.arguments.get('program'):
                
                # h3xrecon program list
                if self.arguments.get('list'):
                    programs = await self.client_api.get_programs()
                    [print(r.get("name")) for r in programs.data]
                
                # h3xrecon program add
                elif self.arguments.get('add'):
                    result = await self.client_api.add_program(self.arguments['<program>'])
                    logger.debug(f"db.add_programresult: {result}")
                    if result.failed:
                        print(f"Error adding program: {result.error}")
                    elif result.data == 0:
                        print(f"Program '{self.arguments['<program>']}' already exists")
                    else:
                        print(f"Program '{self.arguments['<program>']}' added successfully")
                
                # h3xrecon program del
                elif self.arguments.get('del'):
                    items = []
                    if isinstance(self.arguments['<program>'], str):
                        items = [self.arguments['<program>']]
                    if self.arguments.get('-'):
                        items.extend([u.rstrip() for u in process_stdin()])
                    for i in items:
                        result = await self.client_api.remove_program(i)
                        if result.success:
                            if result.data == "DELETE 1":
                                print(f"Program '{i}' removed successfully")
                            elif result.data == "DELETE 0":
                                print(f"Program '{i}' not found")
                        elif result.error:
                            print(f"Error removing program '{i}': {result.error}")

                # h3xrecon program import
                elif self.arguments.get('import'):
                    await self.import_programs(self.arguments['<file>']) 

            # h3xrecon -p program config
            elif self.arguments.get('config'):
            
                # h3xrecon -p program config add/del
                if self.arguments.get('add') or self.arguments.get('del'):
                    if self.arguments.get('scope'): 
                        if self.arguments.get('-'):
                            for i in [u.rstrip() for u in process_stdin()]:
                                await self.client_api.add_program_scope(self.arguments['<program>'], i)
                        else:
                            await self.client_api.add_program_scope(self.arguments['<program>'], self.arguments['<item>'])
                    elif self.arguments.get('cidr'):
                        if self.arguments.get('-'):
                            for i in [u.rstrip() for u in process_stdin()]:
                                await self.client_api.add_program_cidr(self.arguments['<program>'], i)
                        else:
                            await self.client_api.add_program_cidr(self.arguments['<program>'], self.arguments['<item>'])

                # h3xrecon -p program config list scope/cidr
                elif self.arguments.get('list'):
                    if self.arguments.get('scope'):
                        scopes = await self.client_api.get_program_scope(self.arguments['<program>'])
                        [print(r.get('regex')) for r in scopes.data]
                    elif self.arguments.get('cidr'):
                        cidrs = await self.client_api.get_program_cidr(self.arguments['<program>'])
                        [print(r.get('cidr')) for r in cidrs.data]
                
                # h3xrecon -p program config database drop
                elif self.arguments.get('database'):
                    if self.arguments.get('drop'):
                        await self.client_api.drop_program_data(self.arguments['<program>'])
            
            # h3xrecon system
            elif self.arguments.get('system'):
                # h3xrecon system cache
                if self.arguments.get('cache'):
                    if self.arguments.get('flush'):
                        await self.client_api.flush_cache()
                    elif self.arguments.get('show'):
                        keys = await self.client_api.show_cache_keys_values()
                        [print(k) for k in keys]
                # h3xrecon system queue
                if self.arguments.get('queue'):
                    if self.arguments['worker']:
                        stream = 'FUNCTION_EXECUTE'
                    elif self.arguments['job']:
                        stream = 'FUNCTION_OUTPUT'
                    elif self.arguments['data']:
                        stream = 'RECON_DATA'

                    if self.arguments.get('show'):
                        result = await self.client_queue.get_stream_info(stream)
                        headers = result[0].keys()
                        rows = [x.values() for x in result]
                        print(tabulate(rows, headers=headers, tablefmt='grid'))

                    elif self.arguments.get('messages'):
                        result = await self.client_queue.get_stream_messages(stream)
                        headers = result[0].keys()
                        rows = [x.values() for x in result]
                        print(tabulate(rows, headers=headers, tablefmt='grid'))

                    elif self.arguments.get('flush'):
                        result = await self.client_queue.flush_stream(stream)
                        print(result)
            
            # h3xrecon -p program add domain/ip/url
            elif self.arguments.get('add'):
                if any(self.arguments.get(t) for t in ['domain', 'ip', 'url']):
                    item_type = next(t for t in ['domain', 'ip', 'url'] if self.arguments.get(t))
                    items = []
                    if isinstance(self.arguments['<item>'], str):
                        items = [self.arguments['<item>']]
                    if self.arguments.get('-'):
                        items.extend([u.rstrip() for u in process_stdin()])
                    await self.client_api.add_item(item_type, self.arguments['<program>'], items)

            # h3xrecon -p program del domain/ip/url
            elif self.arguments.get('del'):
                if any(self.arguments.get(t) for t in ['domain', 'ip', 'url']):
                    item_type = next(t for t in ['domain', 'ip', 'url'] if self.arguments.get(t))
                    items = []
                    if isinstance(self.arguments['<item>'], str):
                        items = [self.arguments['<item>']]
                    if self.arguments.get('-'):
                        items.extend([u.rstrip() for u in process_stdin()])
                    await self.remove_item(item_type, self.arguments['<program>'], items)

            # h3xrecon -p program list domains/ips/urls
            elif self.arguments.get('list'):          
                # h3xrecon -p program list domains
                if self.arguments.get('domains'):
                    if self.arguments.get('--resolved'):
                        domains = await self.client_api.get_resolved_domains(self.arguments['<program>'])
                        try:
                            [print(f"{r['domain']} -> {r['resolved_ips']}") for r in domains.data]
                        except BrokenPipeError:
                            sys.exit(0)
                    elif self.arguments.get('--unresolved'):
                        domains = await self.client_api.get_unresolved_domains(self.arguments['<program>'])
                        try:
                            [print(r['domain']) for r in domains.data]
                        except BrokenPipeError:
                            sys.exit(0)
                    else:
                        domains = await self.client_api.get_domains(self.arguments['<program>'])
                        try:
                            [print(r.get("domain")) for r in domains.data]
                        except BrokenPipeError:
                            sys.exit(0)

                # h3xrecon -p program list ips
                elif self.arguments.get('ips'):
                    if self.arguments.get('--resolved'):
                        ips = await self.client_api.get_reverse_resolved_ips(self.arguments['<program>'])
                        try:
                            [print(f"{r['ip']} -> {r['ptr']}") for r in ips.data]
                        except BrokenPipeError:
                            sys.exit(0)
                    elif self.arguments.get('--unresolved'):
                        ips = await self.client_api.get_not_reverse_resolved_ips(self.arguments['<program>'])
                        try:
                            [print(r['ip']) for r in ips.data]
                        except BrokenPipeError:
                            sys.exit(0)
                    else:
                        ips = await self.client_api.get_ips(self.arguments['<program>'])
                        try:
                            [print(r['ip']) for r in ips.data]
                        except BrokenPipeError:
                            sys.exit(0)

                # h3xrecon -p program list urls
                elif self.arguments.get('urls'):
                    if self.arguments.get('--details'):
                        result = await self.get_urls_details(self.arguments['<program>'])
                        headers = result[0].keys()
                        rows = [x.values() for x in result]
                        print(tabulate(rows, headers=headers, tablefmt='grid'))

                    else:
                        urls = await self.client_api.get_urls(self.arguments['<program>'])
                        try:
                            [print(r['url']) for r in urls.data]
                        except BrokenPipeError:
                            sys.exit(0)
                    
                # h3xrecon -p program list services
                elif self.arguments.get('services'):
                    services = await self.client_api.get_services(self.arguments['<program>'])
                    try:
                        [print(f"{r.get('protocol')}:{r.get('ip')}:{r.get('port')}") for r in services.data]
                    except BrokenPipeError:
                        sys.exit(0)

                # h3xrecon -p program list nuclei
                elif self.arguments.get('nuclei'):
                    result = await self.client_api.get_nuclei(self.arguments['<program>'], severity=self.arguments['<severity>'])
                    items = set([r.get('url') for r in result.data])
                    try:
                        [print(i) for i in items]
                    except BrokenPipeError:
                        sys.exit(0)
                
                # h3xrecon -p program list certificates
                elif self.arguments.get('certificates'):
                    result = await self.client_api.get_certificates(self.arguments['<program>'])
                    try:
                        for r in result.data:
                            print(f"{r.get('subject_cn')}")
                    except BrokenPipeError:
                        sys.exit(0)
                
            # h3xrecon -p program show domains/ips/urls
            elif self.arguments.get('show'):
                result = None
                #if self.arguments['<program>']:
                # h3xrecon -p program show domains
                if self.arguments.get('domains'):
                    result = await self.client_api.get_domains(self.arguments['<program>'])
                    
                # h3xrecon -p program show ips
                elif self.arguments.get('ips'):
                    result = await self.client_api.get_ips(self.arguments['<program>'])
                
                # h3xrecon -p program show urls
                elif self.arguments.get('urls'):
                    result = await self.client_api.get_urls(self.arguments['<program>'])

                # h3xrecon -p program show services
                elif self.arguments.get('services'):
                    result = await self.client_api.get_services(self.arguments['<program>'])
                
                # h3xrecon -p program show nuclei
                elif self.arguments.get('nuclei'):
                    result = await self.client_api.get_nuclei(self.arguments['<program>'], severity=self.arguments['<severity>'])
                
                # h3xrecon -p program show certificates
                elif self.arguments.get('certificates'):
                    result = await self.client_api.get_certificates(self.arguments['<program>'])

                # print the results in a table format
                if result:
                    headers = list(result.data[0].keys())
                    
                    def truncate_value(value, max_length=50):
                        if headers.index(list(headers)[0]) != headers.index(list(headers)[0]) and isinstance(value, str) and len(value) > max_length:
                            return value[:max_length] + '...'
                        return value
                    
                    rows = [[truncate_value(val) for val in x.values()] for x in result.data]
                    print(tabulate(rows, headers=headers, tablefmt='grid'))

            # h3xrecon -p program sendjob
            elif self.arguments.get('sendjob'):
                targets = []
                if isinstance(self.arguments['<target>'], str):
                    targets = [self.arguments['<target>']]
                if self.arguments.get('-'):
                    targets.extend([u.rstrip() for u in process_stdin()])
                for target in targets:
                    await self.client_api.send_job(
                        function_name=self.arguments['<function>'],
                        program_name=self.arguments['<program>'],
                        params={
                            "target": target,
                            "extra_params": [a for a in self.arguments['<extra_param>'] if a != "--"]
                        },
                        force=self.arguments['--force']
                    )

            else:
                raise ValueError("No valid argument found")
        except Exception as e:
            logger.exception(e)

def process_stdin():
    # Process standard input and filter out empty lines
    return list(filter(lambda x: not re.match(r'^\s*$', x),  sys.stdin.read().split('\n')))

if __name__ == "__main__":
    raise ImportError("This module should not be run directly")