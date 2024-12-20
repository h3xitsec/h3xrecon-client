import typer
from typing import Optional, List
from .handlers import CommandHandlers
import asyncio

app = typer.Typer(
    name="h3xrecon",
    help="H3xRecon - Advanced Reconnaissance Framework Client",
    add_completion=True,
)

handlers = CommandHandlers()

# Add program option to the main app
program_option = typer.Option(None, "--program", "-p", help="Program to work on")

@app.callback()
def main(program: Optional[str] = program_option):
    """
    H3xRecon - Advanced Reconnaissance Framework Client
    """
    if program:
        handlers.current_program = program

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
    component: str = typer.Argument(..., help="Component: killjob, cache, queue, workers, pause, unpause, report"),
    action: str = typer.Argument(..., help="Action to perform"),
    args: Optional[List[str]] = typer.Argument(None, help="Additional arguments")
):
    """System management commands"""
    asyncio.run(handlers.handle_system_commands(component, action, args or []))

@app.command("config")
def config_commands(
    action: str = typer.Argument(..., help="Action: add, del, list"),
    type: str = typer.Argument(..., help="Type: cidr, scope"),
    value: Optional[str] = typer.Argument(None, help="Value for add/del actions"),
    program: Optional[str] = program_option
):
    """Configuration commands"""
    program = get_program(program)
    if not program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)
    asyncio.run(handlers.handle_config_commands(action, type, program, value))

@app.command("list")
def list_commands(
    type: str = typer.Argument(..., help="Type: domains, ips, urls, services, nuclei, certificates"),
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
    asyncio.run(handlers.handle_list_commands(type, program, resolved, unresolved, severity))

@app.command("show")
def show_commands(
    type: str = typer.Argument(..., help="Type: domains, ips, urls, services, nuclei, certificates"),
    resolved: bool = typer.Option(False, "--resolved", help="Show only resolved items"),
    unresolved: bool = typer.Option(False, "--unresolved", help="Show only unresolved items"),
    severity: Optional[str] = typer.Option(None, "--severity", help="Severity for nuclei findings"),
    program: Optional[str] = program_option
):
    """Show reconnaissance assets in table format"""
    program = get_program(program)
    if not program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)
    asyncio.run(handlers.handle_show_commands(type, program, resolved, unresolved, severity))

@app.command("sendjob")
def sendjob_command(
    function: str = typer.Argument(..., help="Function to execute"),
    target: str = typer.Argument(..., help="Target for the function"),
    force: bool = typer.Option(False, "--force", help="Force job execution"),
    params: Optional[List[str]] = typer.Argument(None, help="Additional parameters"),
    program: Optional[str] = program_option
):
    """Send job to worker"""
    program = get_program(program)
    if not program:
        typer.echo("Error: No program specified. Use -p/--program option.")
        raise typer.Exit(1)
    asyncio.run(handlers.handle_sendjob_command(function, target, program, force, params or []))

@app.command("console")
def console_mode():
    """Start interactive console mode"""
    from .console import H3xReconConsole
    console = H3xReconConsole()
    asyncio.run(console.run())

if __name__ == "__main__":
    app()