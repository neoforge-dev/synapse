#!/bin/bash

# Synapse Homebrew Tap Publisher
# This script helps you publish the Homebrew tap to GitHub

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

# Function to get user input
get_input() {
    local prompt="$1"
    local default="$2"
    local input
    
    if [[ -n "$default" ]]; then
        read -p "$prompt [$default]: " input
        echo "${input:-$default}"
    else
        read -p "$prompt: " input
        echo "$input"
    fi
}

# Function to create tap repository
create_tap_repo() {
    local org_name="$1"
    local repo_name="$2"
    
    print_status "Creating Homebrew tap repository..."
    
    # Check if gh CLI is available
    if ! command_exists gh; then
        print_error "GitHub CLI (gh) is required to create the repository."
        print_status "Please install it first: https://cli.github.com/"
        return 1
    fi
    
    # Create the repository
    print_status "Creating repository: $org_name/$repo_name"
    
    if gh repo create "$org_name/$repo_name" \
        --public \
        --description "Homebrew tap for Synapse" \
        --homepage "https://github.com/neoforge-ai/synapse-graph-rag" \
        --confirm; then
        
        print_success "Repository created successfully!"
        return 0
    else
        print_error "Failed to create repository"
        return 1
    fi
}

# Function to setup tap repository
setup_tap_repo() {
    local org_name="$1"
    local repo_name="$2"
    local tap_dir="homebrew-tap"
    
    print_status "Setting up tap repository..."
    
    # Create tap directory if it doesn't exist
    if [[ ! -d "$tap_dir" ]]; then
        print_error "Tap directory '$tap_dir' not found!"
        print_status "Please run this script from the Synapse project root."
        return 1
    fi
    
    # Initialize git in tap directory
    cd "$tap_dir"
    
    if [[ ! -d ".git" ]]; then
        print_status "Initializing git repository..."
        git init
        git remote add origin "https://github.com/$org_name/$repo_name.git"
    fi
    
    # Add all files
    git add .
    
    # Initial commit
    if git commit -m "Initial commit: Synapse Homebrew tap"; then
        print_success "Initial commit created"
    else
        print_warning "No changes to commit or commit failed"
    fi
    
    # Push to GitHub
    print_status "Pushing to GitHub..."
    if git push -u origin main; then
        print_success "Tap repository pushed successfully!"
    else
        print_error "Failed to push to GitHub"
        return 1
    fi
    
    cd ..
}

# Function to test the formula
test_formula() {
    local tap_dir="homebrew-tap"
    
    print_status "Testing Homebrew formula..."
    
    cd "$tap_dir"
    
    # Check if formula is valid
    if brew audit --strict Formula/synapse.rb; then
        print_success "Formula passes audit checks"
    else
        print_warning "Formula has some issues (check output above)"
    fi
    
    # Check formula style
    if brew style Formula/synapse.rb; then
        print_success "Formula passes style checks"
    else
        print_warning "Formula has style issues (check output above)"
    fi
    
    cd ..
}

# Function to show usage instructions
show_usage() {
    local org_name="$1"
    local repo_name="$2"
    
    print_success "🎉 Homebrew tap published successfully!"
    echo
    echo "Users can now install Synapse with:"
    echo
    echo "  # Add the tap"
    echo "  brew tap $org_name/$repo_name"
    echo
    echo "  # Install Synapse"
    echo "  brew install synapse"
    echo
    echo "Or in one command:"
    echo "  brew install $org_name/$repo_name/synapse"
    echo
    echo "📚 Documentation:"
    echo "  - Tap README: https://github.com/$org_name/$repo_name"
    echo "  - Main project: https://github.com/neoforge-ai/synapse-graph-rag"
    echo
    echo "🔄 To update the formula for new releases:"
    echo "  1. Create a new GitHub release in the main repository"
    echo "  2. The GitHub Action will automatically update the formula"
    echo "  3. Or manually run the workflow with a specific version"
}

# Main function
main() {
    echo "🍺 Synapse Homebrew Tap Publisher"
    echo "================================="
    echo
    
    # Get organization/username
    local org_name
    if [[ -n "$GITHUB_ORG" ]]; then
        org_name="$GITHUB_ORG"
    else
        org_name=$(get_input "Enter your GitHub username or organization name" "neoforge-ai")
    fi
    
    # Get repository name
    local repo_name
    if [[ -n "$GITHUB_REPO" ]]; then
        repo_name="$GITHUB_REPO"
    else
        repo_name=$(get_input "Enter the repository name for the tap" "synapse")
    fi
    
    echo
    print_status "Will create tap at: $org_name/$repo_name"
    echo
    
    # Confirm
    local confirm
    confirm=$(get_input "Proceed with creating the tap? (y/N)" "N")
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_status "Aborted"
        exit 0
    fi
    
    echo
    
    # Create the repository
    if create_tap_repo "$org_name" "$repo_name"; then
        # Setup the repository
        if setup_tap_repo "$org_name" "$repo_name"; then
            # Test the formula
            test_formula
            
            # Show usage instructions
            show_usage "$org_name" "$repo_name"
        else
            print_error "Failed to setup tap repository"
            exit 1
        fi
    else
        print_error "Failed to create tap repository"
        exit 1
    fi
}

# Check if running from project root
if [[ ! -f "pyproject.toml" ]] || [[ ! -d "homebrew-tap" ]]; then
    print_error "Please run this script from the Synapse project root directory"
    exit 1
fi

# Run main function
main "$@"
