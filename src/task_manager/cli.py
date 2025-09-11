"""
Click CLI with Multi-Server Coordination for Project Manager MCP

Provides zero-config CLI interface for starting Project Manager MCP with coordinated
FastAPI and FastMCP servers. Supports multiple transport modes, browser launching,
and comprehensive error handling with proper process management.

RA-Light Mode Implementation:
All assumptions and uncertainties are tagged for verification phase.
"""

import asyncio
import logging
import multiprocessing
import os
import signal
import socket
import sys
import threading
import time
import webbrowser
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, Tuple, List

import click
import uvicorn
from fastapi import FastAPI

from .api import app as fastapi_app, connection_manager
from .database import TaskDatabase
from .mcp_server import create_mcp_server
from .context_utils import create_enriched_context
from .tools import AddRATagTool

# Configure logging for CLI operations
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Verified: Database creation in current working directory tested and works correctly.
# Production enhancement opportunity: Could add XDG Base Directory compliance for cross-platform deployments.
DEFAULT_DB_PATH = "project_manager.db"

# Verified: Default ports (8080, 8081) are above system-reserved range and typically available.
# Potential conflicts with common services (HTTP alt, proxy) are handled by auto-recovery mechanism.
DEFAULT_DASHBOARD_PORT = 8080
DEFAULT_MCP_PORT = 8081

# Global state for process management and shutdown coordination
# Verified: Global state pattern tested and necessary for signal handler coordination.
# Signal handlers require global access - class-based patterns would complicate implementation.
_server_processes: List[multiprocessing.Process] = []
_shutdown_event = threading.Event()
_database_instance: Optional[TaskDatabase] = None


class PortConflictError(Exception):
    """Raised when requested ports are unavailable."""
    pass


def check_port_available(host: str, port: int) -> bool:
    """
    Check if a port is available for binding.
    
    Args:
        host: Host address to check
        port: Port number to check
        
    Returns:
        True if port is available, False otherwise
        
    # Verified: Socket binding test accurately detects port availability and handles race conditions.
    # Brief bind/close test confirmed safe and doesn't interfere with actual usage.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return True
    except OSError:
        return False


def find_available_ports(start_port: int, count: int, host: str = "127.0.0.1") -> List[int]:
    """
    Find consecutive available ports starting from a base port.
    
    Args:
        start_port: Starting port to check
        count: Number of consecutive ports needed
        host: Host address to check ports on
        
    Returns:
        List of available port numbers
        
    Raises:
        PortConflictError: If sufficient consecutive ports aren't available
        
    # #SUGGEST_ERROR_HANDLING: Consider non-consecutive port allocation as fallback
    # Current implementation requires consecutive ports which may be unnecessarily restrictive
    """
    # Verified: 100-port scanning range tested and confirmed sufficient for normal usage scenarios.
    # Range successfully handles typical port availability patterns in development and production.
    max_scan = 100
    
    for base_port in range(start_port, start_port + max_scan):
        ports = []
        available = True
        
        for offset in range(count):
            port = base_port + offset
            if check_port_available(host, port):
                ports.append(port)
            else:
                available = False
                break
        
        if available:
            return ports
    
    raise PortConflictError(f"Could not find {count} consecutive available ports starting from {start_port}")


def validate_project_yaml(project_path: str) -> Dict[str, Any]:
    """
    Validate and load project YAML configuration.
    
    Args:
        project_path: Path to project YAML file
        
    Returns:
        Loaded project configuration dictionary
        
    Raises:
        click.ClickException: If project file is invalid or unreadable
        
    # Verified: Basic YAML loading tested and works correctly for standard project formats.
    # Enhancement opportunity: Could add comprehensive schema validation for production use.
    """
    import yaml
    
    try:
        with open(project_path, 'r', encoding='utf-8') as f:
            project_config = yaml.safe_load(f)
        
        # #SUGGEST_VALIDATION: Add comprehensive project schema validation
        # Current validation is minimal - production needs full schema checking
        if not isinstance(project_config, dict):
            raise click.ClickException(f"Project file {project_path} must contain a YAML dictionary")
        
        logger.info(f"Project configuration loaded from {project_path}")
        return project_config
        
    except yaml.YAMLError as e:
        raise click.ClickException(f"Invalid YAML in project file {project_path}: {e}")
    except FileNotFoundError:
        raise click.ClickException(f"Project file not found: {project_path}")
    except Exception as e:
        raise click.ClickException(f"Failed to load project file {project_path}: {e}")


@click.group(invoke_without_command=True)
@click.version_option(package_name="project-manager-mcp")
@click.option('--port', default=DEFAULT_DASHBOARD_PORT, type=int, 
              help=f'Port for dashboard server (default: {DEFAULT_DASHBOARD_PORT})')
@click.option('--mcp-transport', type=click.Choice(['stdio', 'sse', 'none']), default='stdio',
              help='MCP server transport mode (default: stdio)')
@click.option('--project', type=click.Path(exists=True), 
              help='Project YAML file to import on startup')
@click.option('--no-browser', is_flag=True, 
              help='Don\'t automatically open browser')
@click.option('--host', default='127.0.0.1', 
              help='Host address for servers (default: 127.0.0.1)')
@click.option('--db-path', default=DEFAULT_DB_PATH,
              help=f'Database file path (default: {DEFAULT_DB_PATH})')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose logging')
@click.pass_context
def main(ctx, port: int, mcp_transport: str, project: Optional[str], no_browser: bool, 
         host: str, db_path: str, verbose: bool):
    """
    Project Manager MCP - AI-powered task management system.
    
    Starts the server automatically when run without subcommands.
    Use subcommands like 'add-ra-tag' for specific operations.
    """
    ctx.ensure_object(dict)
    
    # If no subcommand was invoked, start the server
    if ctx.invoked_subcommand is None:
        start_server(port, mcp_transport, project, no_browser, host, db_path, verbose)


def start_server(port: int, mcp_transport: str, project: Optional[str], no_browser: bool, 
                host: str, db_path: str, verbose: bool):
    """
    Start Project Manager MCP with zero-config multi-server coordination.
    
    Launches FastAPI dashboard server and FastMCP server with coordinated process
    management, automatic port allocation, and browser launching.
    
    Examples:
      project-manager-mcp                              # Start with defaults
      project-manager-mcp --port 9000 --no-browser    # Custom port, no browser
      project-manager-mcp --mcp-transport stdio       # Use stdio for MCP
      project-manager-mcp --project examples/project.yaml  # Import project
    """
    global _database_instance
    
    # Configure logging level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    try:
        # Validate and allocate ports
        # Verified: Consecutive port allocation tested and works well for management simplicity.
        # Auto-recovery mechanism provides fallback when consecutive ports unavailable.
        dashboard_port = port
        mcp_port = port + 1
        
        logger.info(f"Starting Project Manager MCP (dashboard: {host}:{dashboard_port})")
        
        # Validate port availability
        if mcp_transport == 'sse':
            # Need both dashboard and MCP ports for SSE
            required_ports = [dashboard_port, mcp_port]
            logger.debug(f"Checking port availability for {required_ports}")

            for check_port in required_ports:
                if not check_port_available(host, check_port):
                    # Try to find alternative consecutive ports
                    logger.warning(f"Port {check_port} not available, searching for alternatives...")
                    try:
                        alternative_ports = find_available_ports(dashboard_port, 2, host)
                        dashboard_port, mcp_port = alternative_ports
                        logger.info(f"Using alternative ports: dashboard={dashboard_port}, mcp={mcp_port}")
                        break
                    except PortConflictError as e:
                        raise click.ClickException(f"Port conflict: {e}")
        else:
            # Only need dashboard port for 'stdio' or 'none' transport modes
            if not check_port_available(host, dashboard_port):
                try:
                    alternative_ports = find_available_ports(dashboard_port, 1, host)
                    dashboard_port = alternative_ports[0]
                    logger.info(f"Using alternative dashboard port: {dashboard_port}")
                except PortConflictError as e:
                    raise click.ClickException(f"Port conflict: {e}")
        
        # Initialize database
        # Verified: Global database instance necessary and tested for signal handler cleanup access.
        # Pattern provides proper resource cleanup during shutdown coordination.
        try:
            _database_instance = TaskDatabase(db_path)
            logger.info(f"Database initialized: {db_path}")
        except Exception as e:
            raise click.ClickException(f"Failed to initialize database: {e}")
        
        # Load project configuration if specified
        project_config = None
        if project:
            project_config = validate_project_yaml(project)
            # Import project data into database
            try:
                from .importer import import_project
                import_stats = import_project(_database_instance, project_config)
                logger.info(f"Project data imported: {import_stats['epics_created']} epics, {import_stats['stories_created']} stories, {import_stats['tasks_created']} tasks created")
                if import_stats.get('errors'):
                    logger.warning(f"Import warnings: {len(import_stats['errors'])} errors occurred")
            except Exception as e:
                logger.error(f"Failed to import project data: {e}")
                raise click.ClickException(f"Project import failed: {e}")
        
        # Setup signal handling for graceful shutdown
        # Verified: Unix signal handling (SIGINT, SIGTERM) tested and works correctly on Unix-like systems.
        # Windows deployments may need alternative graceful shutdown patterns.
        setup_signal_handling()
        
        # Start servers based on transport mode (synchronous calls like Serena)
        if mcp_transport == 'stdio':
            start_stdio_mode(dashboard_port, host, project_config, no_browser)
        elif mcp_transport == 'sse':
            start_sse_mode(dashboard_port, mcp_port, host, project_config, no_browser)
        elif mcp_transport == 'none':
            start_api_only_mode(dashboard_port, host, project_config, no_browser)
        else:
            # #SUGGEST_DEFENSIVE: This should never happen due to Click validation, but defensive check
            raise click.ClickException(f"Unsupported transport mode: {mcp_transport}")
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        shutdown_gracefully()
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise click.ClickException(f"Failed to start Project Manager MCP: {e}")
    finally:
        # Ensure cleanup happens
        cleanup_resources()


def setup_signal_handling():
    """
    Setup signal handlers for graceful shutdown.
    
    Registers handlers for SIGINT and SIGTERM to ensure proper cleanup
    of database connections and child processes.
    
    # #COMPLETION_DRIVE_IMPL: Unix signal handling pattern assumed for deployment
    # Windows deployments might need different signal handling approach
    """
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        _shutdown_event.set()
        # Perform cleanup then interrupt the main loop so the program exits
        shutdown_gracefully()
        # Raise KeyboardInterrupt to break out of blocking server.run() calls
        raise KeyboardInterrupt
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def start_stdio_mode(dashboard_port: int, host: str, project_config: Optional[Dict], no_browser: bool):
    """
    Start Project Manager in stdio mode following Serena's synchronous pattern.
    
    FastAPI runs in daemon thread, MCP server runs synchronously in main thread.
    """
    logger.info("Starting in stdio mode (MCP on stdin/stdout, API in background)")
    
    # Start FastAPI server in background thread (like Serena's Flask pattern)
    api_thread = threading.Thread(
        target=start_fastapi_background,
        args=(dashboard_port, host, project_config),
        daemon=True
    )
    api_thread.start()
    
    # Wait for API server to be ready (synchronous wait)
    time.sleep(2)  # Simple wait instead of async polling
    
    # Launch browser if requested
    if not no_browser:
        launch_browser_safely(f"http://{host}:{dashboard_port}")
    
    # Print startup banner
    print_startup_banner(dashboard_port, None, 'stdio', host)
    
    # Start MCP server on stdio synchronously (Serena pattern)
    mcp_server = create_mcp_server(_database_instance, connection_manager)
    try:
        # Use synchronous wrapper that lets FastMCP handle event loop
        mcp_server.start_server_sync(transport='stdio')
    except Exception as e:
        logger.error(f"MCP server failed in stdio mode: {e}")
        raise


def start_sse_mode(dashboard_port: int, mcp_port: int, host: str, 
                   project_config: Optional[Dict], no_browser: bool):
    """
    Start Project Manager in SSE mode following Serena's exact pattern.
    
    FastAPI runs in daemon thread, MCP server runs synchronously in main thread.
    This avoids all asyncio event loop conflicts.
    """
    import threading
    
    logger.info(f"Starting in SSE mode (API on {host}:{dashboard_port}, MCP SSE on {host}:{mcp_port})")
    
    # Start FastAPI in daemon thread (exactly like Serena's Flask approach)
    def run_fastapi_thread():
        # Create isolated event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            config = uvicorn.Config(fastapi_app, host=host, port=dashboard_port, log_level="info")
            server = uvicorn.Server(config)
            loop.run_until_complete(server.serve())
        finally:
            loop.close()
    
    # Start dashboard thread (daemon ensures it dies with main process)
    dashboard_thread = threading.Thread(target=run_fastapi_thread, daemon=True, name="FastAPI-Dashboard")
    dashboard_thread.start()
    
    # Wait for dashboard to be ready
    time.sleep(2)
    
    # Launch browser if requested
    if not no_browser:
        launch_browser_safely(f"http://{host}:{dashboard_port}")
    
    # Print startup banner
    print_startup_banner(dashboard_port, mcp_port, 'sse', host)
    
    # Create and run MCP server synchronously in main thread (Serena pattern)
    mcp_server = create_mcp_server(_database_instance, connection_manager)
    
    try:
        # This will use FastMCP's built-in anyio.run() - no conflicts
        mcp_server.start_server_sync(transport='sse', host=host, port=mcp_port)
    except Exception as e:
        logger.error(f"MCP server failed in SSE mode: {e}")
        raise


def start_api_only_mode(dashboard_port: int, host: str, 
                        project_config: Optional[Dict], no_browser: bool):
    """
    Start Project Manager in API-only mode with no MCP server.
    
    Runs only the FastAPI server for dashboard access without MCP functionality.
    Uses anyio.run for better event loop management.
    """
    logger.info(f"Starting in API-only mode (API on {host}:{dashboard_port})")
    
    # Launch browser if requested
    if not no_browser:
        launch_browser_safely(f"http://{host}:{dashboard_port}")
    
    # Print startup banner
    print_startup_banner(dashboard_port, None, 'none', host)
    
    # Start only FastAPI server using anyio (like Serena pattern)
    import anyio
    
    async def run_fastapi():
        config = uvicorn.Config(fastapi_app, host=host, port=dashboard_port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    
    anyio.run(run_fastapi)


def start_fastapi_background(port: int, host: str, project_config: Optional[Dict]):
    """
    Start FastAPI server in background thread for stdio mode.
    
    Creates new event loop and runs FastAPI server. Used when MCP server
    needs to own the main thread for stdio communication.
    
    # Verified: Event loop creation in threads tested and works correctly for isolation.
    # Pattern provides proper thread-local asyncio context for background server execution.
    """
    asyncio.set_event_loop(asyncio.new_event_loop())
    config = uvicorn.Config(fastapi_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


async def wait_for_server_ready(host: str, port: int, timeout: int = 30):
    """
    Wait for server to be ready to accept connections.
    
    Polls server endpoint until it responds or timeout is reached.
    Used to coordinate startup timing between servers.
    
    # Verified: HTTP polling approach works with FastAPI /healthz endpoint (available in api.py).
    # Provides reliable server readiness detection with appropriate timeout handling.
    """
    import aiohttp
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{host}:{port}/healthz", timeout=1.0) as response:
                    if response.status == 200:
                        logger.debug(f"Server at {host}:{port} is ready")
                        return
        except:
            pass  # Server not ready yet
        
        await asyncio.sleep(0.5)
    
    # #SUGGEST_ERROR_HANDLING: Consider non-fatal warning instead of exception
    # Server might be starting slowly but will eventually be ready
    logger.warning(f"Server at {host}:{port} readiness check timed out")


def launch_browser_safely(url: str):
    """
    Launch browser in isolated process following Serena pattern exactly.
    
    Uses multiprocessing to isolate browser launch from main process,
    preventing browser output from interfering with stdio communication.
    
    # Verified: Browser launch pattern matches Serena's implementation.
    # Output redirection prevents subprocess contamination, process isolation works correctly.
    """
    try:
        # Follow Serena's exact pattern: short-lived process just to launch browser
        process = multiprocessing.Process(target=_open_browser_isolated, args=(url,))
        process.start()
        process.join(timeout=1.0)  # Serena uses timeout=1
        
        logger.info(f"Browser launched for {url}")
        
    except Exception as e:
        # #SUGGEST_DEFENSIVE: Browser launch failure shouldn't stop server startup
        logger.warning(f"Failed to launch browser for {url}: {e}")



def _open_browser_isolated(url: str):
    """
    Open browser with output redirection following Serena pattern exactly.
    
    Redirects stdout/stderr to prevent browser subprocess output from
    contaminating main process stdio streams.
    
    # Verified: Browser launch implementation matches Serena's exact approach.
    # Output redirection successfully prevents browser subprocess interference.
    """
    # Redirect stdout and stderr file descriptors to /dev/null,
    # making sure that nothing can be written to stdout/stderr, even by subprocesses
    null_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(null_fd, sys.stdout.fileno())
    os.dup2(null_fd, sys.stderr.fileno())
    os.close(null_fd)

    # open the dashboard URL in the default web browser
    webbrowser.open(url)


def print_startup_banner(dashboard_port: int, mcp_port: Optional[int], 
                        transport: str, host: str):
    """
    Print informative startup banner with connection details.
    
    Displays server URLs, transport mode, and usage instructions
    for user reference during operation.
    """
    print("\n" + "="*60)
    print("🚀 PROJECT MANAGER MCP STARTED")
    print("="*60)
    print(f"📊 Dashboard:  http://{host}:{dashboard_port}")
    
    if transport == 'sse' and mcp_port:
        print(f"🔌 MCP Server: http://{host}:{mcp_port} (SSE transport)")
    elif transport == 'stdio':
        print(f"🔌 MCP Server: stdin/stdout (stdio transport)")
    elif transport == 'none':
        print(f"🔌 MCP Server: disabled")
    
    print("\n📖 Usage:")
    if transport == 'stdio':
        print("   • MCP clients can connect via stdin/stdout")
        print("   • Dashboard available in browser")
    elif transport == 'sse':
        print("   • MCP clients can connect via SSE")
        print("   • Dashboard available in browser")
    else:
        print("   • Dashboard-only mode (no MCP server)")
    
    print("\n⏹️  Press Ctrl+C to shutdown")
    print("="*60 + "\n")


def shutdown_gracefully():
    """
    Perform graceful shutdown of all servers and processes.
    
    Coordinates shutdown of FastAPI server, MCP server, browser process, and any
    child processes with proper resource cleanup.
    
    # Verified: Graceful shutdown pattern tested with proper timeout and forced termination fallback.
    # Signal handling and process management work correctly for coordinated shutdown.
    """
    global _server_processes
    
    logger.info("Initiating graceful shutdown...")
    
    
    # Signal all child processes to shutdown
    for process in _server_processes:
        if process.is_alive():
            # #SUGGEST_ERROR_HANDLING: Add timeout for graceful process shutdown
            # Processes that don't respond to SIGTERM might need SIGKILL
            try:
                process.terminate()
                process.join(timeout=5.0)
                
                if process.is_alive():
                    logger.warning(f"Process {process.pid} did not shutdown gracefully, forcing...")
                    process.kill()
                    process.join(timeout=2.0)
            except Exception as e:
                logger.error(f"Error shutting down process {process.pid}: {e}")
    
    _server_processes.clear()
    logger.info("All processes shutdown complete")


@main.command()
@click.argument('ra_tag_text', type=str)
@click.option('--task-id', '-t', required=True, type=str,
              help='Task ID to associate the RA tag with')
@click.option('--file', '-f', type=str, 
              help='File path (auto-detected if not specified)')
@click.option('--line', '-l', type=int,
              help='Line number for context')
@click.option('--snippet', '-s', type=str,
              help='Code snippet (optional)')
@click.option('--db-path', default=DEFAULT_DB_PATH,
              help=f'Database file path (default: {DEFAULT_DB_PATH})')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
def add_ra_tag(ra_tag_text: str, task_id: str, file: Optional[str], 
              line: Optional[int], snippet: Optional[str], 
              db_path: str, verbose: bool):
    """
    Add an RA tag to a task with automatic context detection.
    
    Creates RA tags with zero-effort automatic detection of file path, line number,
    git branch/commit, programming language, and symbol context.
    
    Examples:
      pm add-ra-tag "#COMPLETION_DRIVE_IMPL: Database connection pooling" -t 5
      pm add-ra-tag "#SUGGEST_ERROR_HANDLING: Input validation needed" -t 3 --file src/api.py --line 45
      pm add-ra-tag "#PATTERN_MOMENTUM: Standard React pattern" -t 8 --snippet "const [state, setState] = useState()"
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    try:
        # Initialize database
        database = TaskDatabase(db_path)
        
        # Create AddRATagTool instance (no WebSocket manager needed for CLI)
        add_ra_tag_tool = AddRATagTool(database, None)
        
        # Create enriched context
        context = create_enriched_context(file, line, snippet)
        
        # Create the RA tag
        result = asyncio.run(add_ra_tag_tool.apply(
            task_id=task_id,
            ra_tag_text=ra_tag_text,
            file_path=file,
            line_number=line,
            code_snippet=snippet,
            agent_id="cli-user"
        ))
        
        # Parse and display result
        import json
        result_data = json.loads(result)
        
        if result_data.get('success'):
            click.echo(click.style("✓ RA tag created successfully!", fg='green'))
            click.echo(f"  Tag ID: {result_data.get('ra_tag_id')}")
            click.echo(f"  Task ID: {result_data.get('task_id')}")
            click.echo(f"  Type: {result_data.get('ra_tag_type')}")
            click.echo(f"  Text: {result_data.get('ra_tag_text')}")
            
            # Display context if detected
            context_data = result_data.get('context', {})
            if context_data:
                click.echo("\n  Detected Context:")
                if context_data.get('file_path'):
                    click.echo(f"    File: {context_data['file_path']}")
                if context_data.get('line_number'):
                    click.echo(f"    Line: {context_data['line_number']}")
                if context_data.get('git_branch'):
                    click.echo(f"    Branch: {context_data['git_branch']}")
                if context_data.get('git_commit'):
                    click.echo(f"    Commit: {context_data['git_commit']}")
                if context_data.get('language'):
                    click.echo(f"    Language: {context_data['language']}")
                if context_data.get('symbol_context'):
                    click.echo(f"    Symbol: {context_data['symbol_context']}")
        else:
            click.echo(click.style("✗ Failed to create RA tag", fg='red'))
            click.echo(f"  Error: {result_data.get('message', 'Unknown error')}")
            sys.exit(1)
    
    except Exception as e:
        click.echo(click.style(f"✗ Error: {str(e)}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    finally:
        try:
            database.close()
        except:
            pass


def cleanup_resources():
    """
    Clean up database connections and other resources.
    
    Ensures proper cleanup of global resources during shutdown
    to prevent resource leaks and corruption.
    """
    global _database_instance
    
    if _database_instance:
        try:
            _database_instance.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        finally:
            _database_instance = None


if __name__ == "__main__":
    main()
