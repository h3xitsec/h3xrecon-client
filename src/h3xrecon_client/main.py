#!/usr/bin/env python3

__doc__ = """H3XRecon Client

Usage:
    h3xrecon ( program ) ( list ) 
    h3xrecon ( program ) ( add | del) ( - | <program> )
    h3xrecon ( program ) ( import ) ( <file> )
    h3xrecon ( system ) ( queue ) ( show | messages | flush ) ( worker | job | data )
    h3xrecon ( system ) ( cache ) ( flush | show )
    h3xrecon ( list | show ) ( domains | ips | urls | services | nuclei )
    h3xrecon ( list | show ) ( domains | ips ) [--resolved] [--unresolved]
    h3xrecon ( list | show ) ( nuclei ) [--severity <severity>]
    h3xrecon [ -p <program> ] ( config ) ( add | del ) ( cidr | scope ) ( - | <item> )
    h3xrecon [ -p <program> ] ( config ) ( list ) ( cidr | scope )
    h3xrecon [ -p <program> ] ( config ) ( database ) ( drop)
    h3xrecon [ -p <program> ] ( list | show ) ( domains | ips | urls | services | nuclei )
    h3xrecon [ -p <program> ] ( list | show ) ( domains | ips ) [--resolved] [--unresolved]
    h3xrecon [ -p <program> ] ( list | show ) ( nuclei ) [--severity <severity>]
    h3xrecon [ -p <program> ] ( add | del ) ( domain | ip | url ) ( - | <item> )
    h3xrecon [ -p <program> ] ( sendjob ) ( <function> ) ( - | <target> ) [ <extra_param>... ] [--force]

Options:
    -p --program     Program to work on.
    --resolved       Show only resolved items.
    --unresolved    Show only unresolved items.
    --force         Force execution of job.
    --severity      Show only nuclei results with the specified severity.
"""

import asyncio
import sys, os
from docopt import docopt
from .client import Client

VERSION = "0.0.1"

def main():
    try:
        # Parse arguments
        arguments = docopt(__doc__, argv=sys.argv[1:], version=VERSION)
        # Pass parsed arguments to H3XReconClient
        client = Client(arguments)
        asyncio.run(client.run())
    except Exception as e:
        print('[ERROR] ' + str(e))

if __name__ == '__main__':
    main()