#!/usr/bin/env python3
"""
Synapse Local Installation Script
Makes it easy to install Synapse locally using uv and pyproject.toml.
"""

import os
import platform
import subprocess
import sys


def run_command(cmd, check=True, capture_output=False):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=capture_output,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            print(f"❌ Command failed: {cmd}")
            print(f"Error: {e}")
            sys.exit(1)
        return e

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("❌ Python 3.10+ is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")

def check_uv():
    """Check if uv is available and install if needed."""
    if run_command("which uv", check=False).returncode == 0:
        print("✅ uv is already installed")
        return True
    else:
        print("📦 Installing uv (fast Python package manager)...")
        try:
            if platform.system() == "Darwin":
                run_command("brew install uv")
            else:
                run_command("curl -LsSf https://astral.sh/uv/install.sh | sh")
                # Add to PATH for this session
                home = os.path.expanduser("~")
                os.environ["PATH"] = f"{home}/.cargo/bin:{os.environ.get('PATH', '')}"
            return True
        except Exception as e:
            print(f"⚠️  Could not install uv: {e}")
            print("   Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/")
            return False

def install_dependencies():
    """Install required dependencies using uv."""
    print("📦 Installing dependencies with uv...")

    if not check_uv():
        print("❌ uv is required for installation")
        sys.exit(1)

    try:
        # Install in development mode using uv
        run_command("uv pip install -e .[dev]")
        print("✅ Dependencies installed successfully")
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        sys.exit(1)

def create_symlink():
    """Create a symlink to make synapse available system-wide."""
    print("🔗 Creating system symlink...")

    # Find the synapse binary using uv
    try:
        result = run_command("uv run which synapse", capture_output=True)
        if result.returncode == 0:
            synapse_path = result.stdout.strip()
        else:
            print("⚠️  Could not find synapse binary, trying alternative method...")
            # Try to find it in the virtual environment
            venv_path = run_command("uv venv --path", capture_output=True).stdout.strip()
            synapse_path = os.path.join(venv_path, "bin", "synapse")
            if not os.path.exists(synapse_path):
                print("⚠️  Could not find synapse binary, skipping symlink creation")
                return
    except Exception as e:
        print(f"⚠️  Could not find synapse binary: {e}")
        return

    # Create symlink in a directory that's in PATH
    if platform.system() == "Darwin":  # macOS
        target_dir = "/usr/local/bin"
        if not os.path.exists(target_dir):
            target_dir = os.path.expanduser("~/bin")
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
    else:  # Linux/Windows
        target_dir = os.path.expanduser("~/bin")
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

    target_path = os.path.join(target_dir, "synapse")

    # Remove existing symlink if it exists
    if os.path.exists(target_path):
        os.remove(target_path)

    # Create new symlink
    try:
        os.symlink(synapse_path, target_path)
        print(f"✅ Created symlink: {target_path} -> {synapse_path}")

        # Add to PATH if not already there
        shell_rc = os.path.expanduser("~/.bashrc")
        if platform.system() == "Darwin":
            shell_rc = os.path.expanduser("~/.zshrc")

        path_export = f'export PATH="{target_dir}:$PATH"'

        with open(shell_rc) as f:
            content = f.read()

        if path_export not in content:
            with open(shell_rc, 'a') as f:
                f.write(f"\n# Synapse\nexport PATH=\"{target_dir}:$PATH\"\n")
            print(f"✅ Added {target_dir} to PATH in {shell_rc}")
            print("🔄 Please restart your terminal or run: source ~/.zshrc (or ~/.bashrc)")
        else:
            print(f"✅ {target_dir} is already in PATH")

    except Exception as e:
        print(f"⚠️  Could not create symlink: {e}")
        print(f"   You can still run synapse from: {synapse_path}")

def test_installation():
    """Test if the installation works."""
    print("🧪 Testing installation...")

    try:
        # Test using uv run
        result = run_command("uv run synapse --version", capture_output=True)
        if result.returncode == 0:
            print("✅ Synapse is working!")
            print(f"Version: {result.stdout.strip()}")
        else:
            print("❌ Synapse command failed")
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"❌ Could not test synapse: {e}")

def show_usage():
    """Show how to use the installed Synapse."""
    print()
    print("🚀 Synapse is now installed!")
    print()
    print("You can run Synapse using uv:")
    print("  uv run synapse --help")
    print("  uv run synapse init wizard --quick --vector-only")
    print("  uv run synapse up")
    print()
    print("Or if you created a symlink:")
    print("  synapse --help")
    print("  synapse init wizard --quick --vector-only")
    print("  synapse up")

def main():
    """Main installation function."""
    print("🚀 Synapse Local Installation")
    print("=" * 35)
    print()

    # Check Python version
    check_python_version()

    # Check if pyproject.toml exists
    if not os.path.exists("pyproject.toml"):
        print("❌ pyproject.toml not found!")
        print("   Please run this script from the Synapse project root directory.")
        sys.exit(1)

    print("✅ pyproject.toml found")

    # Install dependencies
    install_dependencies()

    # Create symlink (optional)
    create_symlink()

    # Test installation
    test_installation()

    # Show usage
    show_usage()

    print()
    print("🎉 Installation complete!")
    print()
    print("💡 Pro tip: Use 'uv run synapse' to run Synapse commands")

if __name__ == "__main__":
    main()
