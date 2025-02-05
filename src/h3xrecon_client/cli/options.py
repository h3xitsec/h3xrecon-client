from dataclasses import dataclass
from typing import Optional, Dict, Any
import typer

@dataclass
class GlobalOptions:
    """Global options that affect the entire application"""
    # Program context
    program: Optional[str] = None
    
    # Display behavior
    no_pager: bool = False
    quiet: bool = False
    
    # Performance and behavior
    timeout: int = 300
    debug: bool = False
    
    @classmethod
    def get_options(cls) -> Dict[str, Any]:
        """Get all global options as Typer options"""
        return {
            # Program context
            "program": typer.Option(
                None, 
                "--program", 
                "-p", 
                help="Program to work on"
            ),
            
            # Display behavior
            "no_pager": typer.Option(
                False, 
                "--no-pager", 
                help="Disable pagination and show all results at once"
            ),
            "quiet": typer.Option(
                False, 
                "--quiet", 
                "-q", 
                help="Suppress non-essential output"
            ),
            
            # Performance and behavior
            "timeout": typer.Option(
                300, 
                "--timeout", 
                help="Global timeout for operations in seconds"
            ),
            "debug": typer.Option(
                False, 
                "--debug", 
                "-d", 
                help="Enable debug mode with additional output"
            )
        }

    def update(self, **kwargs):
        """Update options with new values"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value) 