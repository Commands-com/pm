#!/usr/bin/env python3
"""
Deployment Verification Script

Validates Docker and deployment configuration files without requiring
Docker daemon to be running.
"""

import os
import sys
import json
from pathlib import Path


def check_file_exists(file_path: str, description: str) -> bool:
    """Check if a file exists and report status."""
    path = Path(file_path)
    if path.exists():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (NOT FOUND)")
        return False


def validate_dockerfile():
    """Validate Dockerfile syntax and structure."""
    dockerfile_path = Path("Dockerfile")
    
    if not dockerfile_path.exists():
        print("❌ Dockerfile not found")
        return False
    
    content = dockerfile_path.read_text()
    
    # Check for required instructions
    required_instructions = [
        "FROM python:3.11-slim as builder",
        "FROM python:3.11-slim as production",
        "USER appuser",
        "HEALTHCHECK",
        "EXPOSE 8080 8081"
    ]
    
    missing = []
    for instruction in required_instructions:
        if instruction not in content:
            missing.append(instruction)
    
    if missing:
        print("❌ Dockerfile missing required instructions:")
        for item in missing:
            print(f"   - {item}")
        return False
    else:
        print("✅ Dockerfile structure validated")
        return True


def validate_docker_compose():
    """Validate docker-compose.yml content."""
    compose_path = Path("docker-compose.yml")
    
    if not compose_path.exists():
        print("❌ docker-compose.yml not found")
        return False
    
    try:
        content = compose_path.read_text()
        
        # Check for required sections using text search
        required_sections = [
            'services:',
            'project-manager:',
            'build:',
            'ports:',
            'volumes:',
            'environment:',
            'healthcheck:',
            '8080:8080',
            '8081:8081'
        ]
        
        missing = []
        for section in required_sections:
            if section not in content:
                missing.append(section)
        
        if missing:
            print(f"❌ docker-compose.yml missing sections: {', '.join(missing)}")
            return False
        
        print("✅ docker-compose.yml structure validated")
        return True
        
    except Exception as e:
        print(f"❌ docker-compose.yml validation error: {e}")
        return False


def validate_environment_config():
    """Validate production environment configuration."""
    env_path = Path("deploy/production.env")
    
    if not env_path.exists():
        print("❌ deploy/production.env not found")
        return False
    
    content = env_path.read_text()
    lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
    
    # Check for required environment variables
    required_vars = [
        'DATABASE_PATH',
        'LOG_LEVEL',
        'DEFAULT_PORT',
        'MCP_TRANSPORT'
    ]
    
    found_vars = set()
    for line in lines:
        if '=' in line:
            var_name = line.split('=')[0]
            found_vars.add(var_name)
    
    missing = [var for var in required_vars if var not in found_vars]
    
    if missing:
        print(f"❌ production.env missing variables: {', '.join(missing)}")
        return False
    else:
        print("✅ production.env configuration validated")
        return True


def validate_health_check():
    """Validate health check script."""
    script_path = Path("deploy/docker-healthcheck.py")
    
    if not script_path.exists():
        print("❌ deploy/docker-healthcheck.py not found")
        return False
    
    content = script_path.read_text()
    
    # Check for required functions
    required_functions = [
        'def check_port_listening',
        'def check_http_endpoint',
        'def check_database_file',
        'def main'
    ]
    
    missing = []
    for func in required_functions:
        if func not in content:
            missing.append(func)
    
    if missing:
        print(f"❌ docker-healthcheck.py missing functions: {', '.join(missing)}")
        return False
    else:
        print("✅ docker-healthcheck.py structure validated")
        return True


def main():
    """Main validation function."""
    print("🔍 Validating deployment configuration...\n")
    
    # Change to project root if needed
    if not Path("pyproject.toml").exists():
        project_root = Path(__file__).parent.parent
        os.chdir(project_root)
        print(f"Changed directory to: {project_root}\n")
    
    results = []
    
    # Check file existence
    files_to_check = [
        ("Dockerfile", "Multi-stage Docker configuration"),
        ("docker-compose.yml", "Docker Compose orchestration"),
        ("deploy/production.env", "Production environment config"),
        ("deploy/docker-healthcheck.py", "Docker health check script"),
        ("pyproject.toml", "Python package configuration"),
        ("src/task_manager/api.py", "FastAPI application"),
        ("src/task_manager/database.py", "Database layer")
    ]
    
    for file_path, description in files_to_check:
        results.append(check_file_exists(file_path, description))
    
    print()
    
    # Validate file contents
    validation_functions = [
        validate_dockerfile,
        validate_docker_compose,
        validate_environment_config,
        validate_health_check
    ]
    
    for func in validation_functions:
        results.append(func())
    
    print()
    
    # Summary
    success_count = sum(results)
    total_count = len(results)
    
    if success_count == total_count:
        print(f"🎉 All {total_count} validation checks passed!")
        print("\n📋 Deployment ready:")
        print("   1. Build: docker-compose build")
        print("   2. Start: docker-compose up -d")
        print("   3. Check: docker-compose ps")
        print("   4. Health: curl http://localhost:8080/healthz")
        print("   5. Metrics: curl http://localhost:8080/api/metrics")
        sys.exit(0)
    else:
        failed_count = total_count - success_count
        print(f"❌ {failed_count}/{total_count} validation checks failed!")
        print("\n🔧 Fix the issues above before deployment.")
        sys.exit(1)


if __name__ == "__main__":
    main()