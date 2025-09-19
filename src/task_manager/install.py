"""
Claude Assets Installation Module

Provides functionality to install Claude agents and commands from the package
to user-specified locations. Supports selective installation and conflict handling.
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple, List

import click


class ClaudeAssetInstaller:
    """
    Handles installation of Claude agents and commands to target directories.

    Supports copying from package installation or development directory.
    """

    def __init__(self):
        """Initialize installer with package source paths."""
        self.package_root = self._find_package_root()
        self.agents_source = self.package_root / ".claude" / "agents"
        self.commands_source = self.package_root / ".claude" / "commands"

    def _find_package_root(self) -> Path:
        """
        Find the package root directory containing .claude assets.

        Checks in order:
        1. Development directory (relative to this module)
        2. Package installation directory
        3. Current working directory

        Returns:
            Path to package root directory

        Raises:
            FileNotFoundError: If .claude directory not found
        """
        # Try development directory (relative to this module)
        module_dir = Path(__file__).parent
        dev_root = module_dir.parent.parent
        if (dev_root / ".claude").exists():
            return dev_root

        # Try package installation directory
        # When installed, package might be in site-packages
        try:
            import task_manager
            pkg_dir = Path(task_manager.__file__).parent.parent
            if (pkg_dir / ".claude").exists():
                return pkg_dir
        except ImportError:
            pass

        # Try current working directory
        cwd = Path.cwd()
        if (cwd / ".claude").exists():
            return cwd

        raise FileNotFoundError(
            "Could not find .claude directory. "
            "Ensure you're running from the project root or have the package properly installed."
        )

    def validate_sources(self) -> Tuple[bool, List[str]]:
        """
        Validate that source directories exist and contain files.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if not self.agents_source.exists():
            errors.append(f"Agents directory not found: {self.agents_source}")
        elif not any(self.agents_source.iterdir()):
            errors.append(f"Agents directory is empty: {self.agents_source}")

        if not self.commands_source.exists():
            errors.append(f"Commands directory not found: {self.commands_source}")
        elif not any(self.commands_source.iterdir()):
            errors.append(f"Commands directory is empty: {self.commands_source}")

        return len(errors) == 0, errors

    def install_assets(
        self,
        target_dir: str,
        force: bool = False,
        agents_only: bool = False,
        commands_only: bool = False
    ) -> Tuple[bool, str, List[str]]:
        """
        Install Claude assets to target directory.

        Args:
            target_dir: Destination directory path
            force: Overwrite existing files if True
            agents_only: Install only agents directory
            commands_only: Install only commands directory

        Returns:
            Tuple of (success, message, installed_files)
        """
        target_path = Path(target_dir).expanduser().resolve()

        # Validate sources
        is_valid, errors = self.validate_sources()
        if not is_valid:
            return False, f"Source validation failed: {'; '.join(errors)}", []

        # Create target directory if it doesn't exist
        try:
            target_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return False, f"Failed to create target directory: {e}", []

        # Determine what to install
        if agents_only and commands_only:
            return False, "Cannot specify both --agents-only and --commands-only", []

        install_agents = not commands_only
        install_commands = not agents_only

        installed_files = []

        # Install agents
        if install_agents:
            success, files = self._install_directory(
                self.agents_source,
                target_path / ".claude" / "agents",
                force
            )
            if not success:
                return False, f"Failed to install agents: {files}", []
            installed_files.extend(files)

        # Install commands
        if install_commands:
            success, files = self._install_directory(
                self.commands_source,
                target_path / ".claude" / "commands",
                force
            )
            if not success:
                return False, f"Failed to install commands: {files}", []
            installed_files.extend(files)

        # Generate summary message
        components = []
        if install_agents:
            components.append("agents")
        if install_commands:
            components.append("commands")

        message = f"Successfully installed Claude {' and '.join(components)} to {target_path}/.claude/"
        return True, message, installed_files

    def _install_directory(
        self,
        source_dir: Path,
        target_dir: Path,
        force: bool
    ) -> Tuple[bool, List[str]]:
        """
        Install a single directory with conflict handling.

        Args:
            source_dir: Source directory to copy from
            target_dir: Target directory to copy to
            force: Overwrite existing files if True

        Returns:
            Tuple of (success, installed_files_or_error_message)
        """
        installed_files = []

        try:
            # Check for existing directory
            if target_dir.exists():
                if not force:
                    existing_files = list(target_dir.rglob("*"))
                    if existing_files:
                        return False, [f"Target directory exists and contains files: {target_dir}. Use --force to overwrite."]
                else:
                    # Remove existing directory for clean installation
                    shutil.rmtree(target_dir)

            # Create parent directory
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            # Copy directory
            shutil.copytree(source_dir, target_dir)

            # Collect installed files
            for file_path in target_dir.rglob("*"):
                if file_path.is_file():
                    installed_files.append(str(file_path.relative_to(target_dir.parent.parent)))

            return True, installed_files

        except Exception as e:
            return False, [f"Installation error: {e}"]


def install_claude_assets(
    target_dir: str,
    force: bool = False,
    agents_only: bool = False,
    commands_only: bool = False,
    verbose: bool = False
) -> bool:
    """
    Main installation function for CLI integration.

    Args:
        target_dir: Target directory for installation
        force: Overwrite existing files
        agents_only: Install only agents
        commands_only: Install only commands
        verbose: Print detailed output

    Returns:
        True if installation succeeded, False otherwise
    """
    installer = ClaudeAssetInstaller()

    success, message, installed_files = installer.install_assets(
        target_dir=target_dir,
        force=force,
        agents_only=agents_only,
        commands_only=commands_only
    )

    if success:
        print(f"✅ {message}")
        if verbose and installed_files:
            print("\nInstalled files:")
            for file_path in sorted(installed_files):
                print(f"  📁 {file_path}")
        return True
    else:
        print(f"❌ Installation failed: {message}", file=sys.stderr)
        return False


@click.command()
@click.option('--target-dir', '-d', required=True, type=str,
              help='Target directory to install Claude assets')
@click.option('--force', '-f', is_flag=True,
              help='Overwrite existing files')
@click.option('--agents-only', is_flag=True,
              help='Install only agents directory')
@click.option('--commands-only', is_flag=True,
              help='Install only commands directory')
@click.option('--verbose', '-v', is_flag=True,
              help='Show detailed installation output')
def main(target_dir: str, force: bool, agents_only: bool, commands_only: bool, verbose: bool):
    """
    Install Claude agents and commands to a target directory.

    This command copies the .claude/agents and .claude/commands directories
    from this package to your specified location.

    Examples:
      pm-install-claude-assets --target-dir ~/my-project
      pm-install-claude-assets -d ./frontend --agents-only --force
      pm-install-claude-assets -d /workspace --commands-only -v
    """
    success = install_claude_assets(
        target_dir=target_dir,
        force=force,
        agents_only=agents_only,
        commands_only=commands_only,
        verbose=verbose
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()