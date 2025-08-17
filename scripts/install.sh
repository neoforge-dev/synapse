#!/bin/bash

# Synapse GraphRAG - Easy Installation Script
# Makes Synapse as easy to install as 'brew install synapse'

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Function to install Homebrew (macOS/Linux)
install_homebrew() {
    if ! command_exists brew; then
        print_status "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for this session
        if [[ "$OSTYPE" == "darwin"* ]]; then
            if [[ "$(uname -m)" == "arm64" ]]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            else
                eval "$(/usr/local/bin/brew shellenv)"
            fi
        else
            eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
        fi
    else
        print_success "Homebrew already installed"
    fi
}

# Function to install pipx
install_pipx() {
    if ! command_exists pipx; then
        print_status "Installing pipx..."
        if command_exists brew; then
            brew install pipx
        elif command_exists pip3; then
            pip3 install --user pipx
            export PATH="$HOME/.local/bin:$PATH"
        else
            print_error "Could not install pipx. Please install Python and pip first."
            exit 1
        fi
    else
        print_success "pipx already installed"
    fi
}

# Function to install uv
install_uv() {
    if ! command_exists uv; then
        print_status "Installing uv (fast Python package manager)..."
        if command_exists brew; then
            brew install uv
        elif command_exists curl; then
            curl -LsSf https://astral.sh/uv/install.sh | sh
            export PATH="$HOME/.cargo/bin:$PATH"
        else
            print_warning "Could not install uv. Falling back to pip."
        fi
    else
        print_success "uv already installed"
    fi
}

# Function to install Synapse via Homebrew
install_via_homebrew() {
    print_status "Installing Synapse via Homebrew..."
    
    # Check if we're in the Synapse project directory
    if [[ -f "Formula/synapse-graph-rag.rb" ]]; then
        print_status "Found local Homebrew formula, installing from source..."
        brew install ./Formula/synapse-graph-rag.rb
    else
        print_status "Installing from GitHub repository..."
        brew install neoforge-ai/synapse-graph-rag/synapse-graph-rag
    fi
}

# Function to install Synapse via pipx
install_via_pipx() {
    print_status "Installing Synapse via pipx..."
    
    # Build the package first
    if command_exists uv; then
        print_status "Building package with uv..."
        uv build
    else
        print_status "Building package with pip..."
        pip3 install build
        python3 -m build
    fi
    
    # Install with pipx
    pipx install dist/*.whl
    
    # Add to PATH if not already there
    if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
        print_warning "Adding ~/.local/bin to PATH..."
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc 2>/dev/null || true
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

# Function to install Synapse via pip
install_via_pip() {
    print_status "Installing Synapse via pip..."
    
    if command_exists uv; then
        uv pip install synapse-graph-rag
    else
        pip3 install synapse-graph-rag
    fi
}

# Function to verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    if command_exists synapse; then
        # Test if synapse actually works
        if synapse --version >/dev/null 2>&1; then
            print_success "Synapse installed successfully!"
            echo
            echo "🎉 Installation complete! Here's what you can do next:"
            echo
            echo "1. Check Synapse version:"
            echo "   synapse --version"
            echo
            echo "2. See available commands:"
            echo "   synapse --help"
            echo
            echo "3. Quick start (vector-only mode, no Docker required):"
            echo "   synapse init wizard --quick --vector-only"
            echo
            echo "4. Full setup with Docker:"
            echo "   synapse up"
            echo
            echo "5. Ingest your first document:"
            echo "   echo 'Hello World' | synapse ingest test.md --stdin"
            echo
            echo "6. Ask questions:"
            echo "   synapse query ask 'What did I just write?'"
            echo
            return 0
        else
            print_warning "Synapse command exists but doesn't work properly. This might be a broken installation."
            print_status "Attempting to fix installation..."
            return 1
        fi
    else
        print_error "Synapse installation failed!"
        return 1
    fi
}

# Function to show installation options
show_options() {
    echo
    echo "🚀 Synapse GraphRAG Installation Options"
    echo "========================================"
    echo
    echo "1. Homebrew (recommended for macOS/Linux)"
    echo "   - System-wide installation"
    echo "   - Automatic PATH configuration"
    echo "   - Easy updates and management"
    echo
    echo "2. pipx (recommended for cross-platform)"
    echo "   - Isolated installation"
    echo "   - No system conflicts"
    echo "   - Easy updates"
    echo
    echo "3. pip (simple but less isolated)"
    echo "   - Direct installation"
    echo "   - May conflict with system packages"
    echo
    echo "4. Auto-detect (let the script choose)"
    echo "   - Automatically selects best method"
    echo
}

# Function to auto-detect best installation method
auto_detect_method() {
    local os=$(detect_os)
    
    if [[ "$os" == "macos" ]]; then
        echo "homebrew"
    elif [[ "$os" == "linux" ]]; then
        if command_exists brew; then
            echo "homebrew"
        else
            echo "pipx"
        fi
    else
        echo "pipx"
    fi
}

# Main installation function
main() {
    echo "🚀 Welcome to Synapse GraphRAG Installation!"
    echo "============================================="
    echo
    
    # Check if Synapse is already installed
    if command_exists synapse; then
        print_success "Synapse is already installed!"
        synapse --version
        echo
        echo "To update, run: brew upgrade synapse-graph-rag (if installed via Homebrew)"
        echo "Or: pipx upgrade synapse-graph-rag (if installed via pipx)"
        exit 0
    fi
    
    # Parse command line arguments
    INSTALL_METHOD=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --homebrew)
                INSTALL_METHOD="homebrew"
                shift
                ;;
            --pipx)
                INSTALL_METHOD="pipx"
                shift
                ;;
            --pip)
                INSTALL_METHOD="pip"
                shift
                ;;
            --auto)
                INSTALL_METHOD="auto"
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo
                echo "Options:"
                echo "  --homebrew    Install via Homebrew (macOS/Linux)"
                echo "  --pipx        Install via pipx (cross-platform)"
                echo "  --pip         Install via pip (simple)"
                echo "  --auto        Auto-detect best method (default)"
                echo "  --help, -h    Show this help message"
                echo
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Auto-detect if no method specified
    if [[ -z "$INSTALL_METHOD" ]]; then
        INSTALL_METHOD="auto"
    fi
    
    if [[ "$INSTALL_METHOD" == "auto" ]]; then
        INSTALL_METHOD=$(auto_detect_method)
        print_status "Auto-detected installation method: $INSTALL_METHOD"
    fi
    
    # Install prerequisites based on method
    case $INSTALL_METHOD in
        "homebrew")
            install_homebrew
            install_via_homebrew
            ;;
        "pipx")
            install_pipx
            install_via_pipx
            ;;
        "pip")
            install_via_pip
            ;;
        *)
            print_error "Unknown installation method: $INSTALL_METHOD"
            exit 1
            ;;
    esac
    
    # Verify installation
    if verify_installation; then
        print_success "🎉 Synapse is now ready to use!"
        echo
        echo "💡 Pro tip: Run 'synapse init wizard' to get started quickly!"
        exit 0
    else
        print_error "Installation failed. Please check the error messages above."
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
