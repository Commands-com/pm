#!/usr/bin/env python3
"""
Docker Health Check Script for Project Manager MCP

Performs comprehensive health checks suitable for Docker HEALTHCHECK
instruction and load balancer health checks.
"""

import os
import sys
import json
import time
import subprocess
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


def check_port_listening(port: int) -> bool:
    """Check if a port is listening using netstat-like approach."""
    try:
        # Check if process is listening on port
        result = subprocess.run(
            ["ss", "-ln", f"sport = :{port}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return str(port) in result.stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        # Fallback if ss command not available
        return True


def check_http_endpoint(url: str, timeout: int = 5) -> dict:
    """Check HTTP endpoint health."""
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return {"status": "healthy", "response": data}
            else:
                return {"status": "unhealthy", "error": f"HTTP {response.status}"}
    except HTTPError as e:
        return {"status": "unhealthy", "error": f"HTTP Error: {e.code}"}
    except URLError as e:
        return {"status": "unhealthy", "error": f"Connection Error: {e.reason}"}
    except json.JSONDecodeError:
        return {"status": "unhealthy", "error": "Invalid JSON response"}
    except Exception as e:
        return {"status": "unhealthy", "error": f"Unexpected error: {str(e)}"}


def check_database_file() -> dict:
    """Check if database file exists and is accessible."""
    db_path = os.getenv("DATABASE_PATH", "/app/data/tasks.db")
    
    try:
        if os.path.exists(db_path):
            # Check if file is readable
            with open(db_path, 'rb') as f:
                # Read first few bytes to ensure it's accessible
                header = f.read(16)
                if b'SQLite' in header:
                    return {"status": "healthy", "database_path": db_path}
                else:
                    return {"status": "unhealthy", "error": "Database file corrupted"}
        else:
            # Database file doesn't exist - might be first startup
            return {"status": "warning", "error": "Database file not found"}
    except Exception as e:
        return {"status": "unhealthy", "error": f"Database check failed: {str(e)}"}


def main():
    """Main health check function."""
    # Configuration
    port = int(os.getenv("DEFAULT_PORT", "8080"))
    base_url = f"http://localhost:{port}"
    
    health_results = {
        "timestamp": time.time(),
        "checks": {}
    }
    
    # Check 1: Port listening
    health_results["checks"]["port"] = {
        "status": "healthy" if check_port_listening(port) else "unhealthy"
    }
    
    # Check 2: HTTP endpoint
    health_endpoint = f"{base_url}/healthz"
    health_results["checks"]["http"] = check_http_endpoint(health_endpoint)
    
    # Check 3: Database file
    health_results["checks"]["database"] = check_database_file()
    
    # Overall status determination
    all_checks = [check["status"] for check in health_results["checks"].values()]
    
    if all(status == "healthy" for status in all_checks):
        health_results["overall"] = "healthy"
        exit_code = 0
    elif any(status == "unhealthy" for status in all_checks):
        health_results["overall"] = "unhealthy"
        exit_code = 1
    else:
        # Some warnings but no failures
        health_results["overall"] = "degraded"
        exit_code = 0
    
    # Output results
    if os.getenv("HEALTH_CHECK_VERBOSE", "false").lower() == "true":
        print(json.dumps(health_results, indent=2))
    else:
        print(f"Health: {health_results['overall']}")
        if exit_code != 0:
            # Show failed checks
            for name, check in health_results["checks"].items():
                if check["status"] == "unhealthy":
                    print(f"Failed: {name} - {check.get('error', 'Unknown error')}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()