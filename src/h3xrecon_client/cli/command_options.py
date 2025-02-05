from dataclasses import dataclass
from typing import Optional, Dict, Any
import typer

@dataclass
class ShowCommandOptions:
    """Options specific to the show command"""
    resolved: bool = False
    unresolved: bool = False
    severity: Optional[str] = None
    domain: Optional[str] = None
    filter: Optional[str] = None

    @classmethod
    def get_options(cls) -> Dict[str, Any]:
        return {
            "resolved": typer.Option(False, "--resolved", help="Show only resolved items"),
            "unresolved": typer.Option(False, "--unresolved", help="Show only unresolved items"),
            "severity": typer.Option(None, "--severity", help="Severity for nuclei findings"),
            "domain": typer.Option(None, "--domain", "-d", help="Domain to show DNS records for"),
            "filter": typer.Option(None, "--filter", "-f", help="Filter show command output")
        }

@dataclass
class ConfigCommandOptions:
    """Options specific to the config command"""
    wildcard: bool = False
    regex: Optional[str] = None

    @classmethod
    def get_options(cls) -> Dict[str, Any]:
        return {
            "wildcard": typer.Option(False, "--wildcard", help="Use wildcard for domain scope"),
            "regex": typer.Option(None, "--regex", help="Use regex for domain scope")
        }

@dataclass
class JobCommandOptions:
    """Options for job-related commands (sendjob, workflow)"""
    wordlist: Optional[str] = None
    mode: Optional[str] = None
    no_trigger: bool = False
    wait_ack: bool = False
    force: bool = False

    @classmethod
    def get_options(cls) -> Dict[str, Any]:
        return {
            "wordlist": typer.Option(None, "--wordlist", help="Wordlist to use for functions that need it"),
            "mode": typer.Option(None, "--mode", help="Plugin run mode"),
            "no_trigger": typer.Option(False, "--no-trigger", help="Do not trigger new jobs after processing"),
            "wait_ack": typer.Option(False, "--wait-ack", "-w", help="Wait for job request response"),
            "force": typer.Option(False, "--force", help="Force job execution")
        }

@dataclass
class SystemCommandOptions:
    """Options specific to system commands"""
    filter: Optional[str] = None

    @classmethod
    def get_options(cls) -> Dict[str, Any]:
        return {
            "filter": typer.Option(None, "--filter", "-f", help="Filter system command output")
        } 