# 🚀 Synapse Installation Guide

## **🎯 Goal: Make Synapse as Easy to Install as `brew install synapse`**

This guide shows you multiple ways to install Synapse, from the simplest one-liner to advanced development setups.

---

## **🔥 Super Easy Installation (Recommended)**

### **One Command - Works Everywhere**
```bash
curl -fsSL https://raw.githubusercontent.com/neoforge-dev/synapse/main/scripts/install.sh | bash
```

**What this does:**
- ✅ Auto-detects your OS and best installation method
- ✅ Installs all prerequisites automatically
- ✅ Installs Synapse with proper PATH configuration
- ✅ Creates configuration files
- ✅ Verifies everything works

**Perfect for:** New users, quick setup, any system

---

## **🍺 Homebrew Installation (macOS/Linux)**

### **Option 1: Install from Local Formula**
```bash
# Clone the repository first
git clone https://github.com/neoforge-dev/synapse.git
cd synapse

# Install using the local formula
brew install ./Formula/synapse.rb
```

### **Option 2: Install from GitHub Tap (Future)**
```bash
# When we publish the tap
brew tap neoforge-dev/synapse
brew install synapse
```

**What this gives you:**
- ✅ System-wide installation
- ✅ Automatic PATH configuration
- ✅ Easy updates with `brew upgrade synapse`
- ✅ Shell completions
- ✅ Professional installation experience

**Perfect for:** macOS/Linux users who prefer Homebrew

---

## **🐍 Python Package Managers**

### **Option 1: pipx (Recommended for Python users)**
```bash
# Install pipx if you don't have it
pip install --user pipx
export PATH="$HOME/.local/bin:$PATH"

# Install Synapse
pipx install synapse
```

### **Option 2: uv (Fastest Python package manager)**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Synapse
uv pip install synapse
```

### **Option 3: pip (Simple but less isolated)**
```bash
pip install synapse
```

**What this gives you:**
- ✅ Cross-platform compatibility
- ✅ Isolated installations (pipx)
- ✅ Fast installation (uv)
- ✅ Easy updates

**Perfect for:** Python developers, cross-platform users

---

## **🔧 Development Installation**

### **Option 1: Makefile (Recommended for developers)**
```bash
# Clone and setup
git clone https://github.com/neoforge-dev/synapse.git
cd synapse

# Install development environment
make install-dev

# Start services
make up
```

### **Option 2: Python setup script**
```bash
# Clone and setup
git clone https://github.com/neoforge-dev/synapse.git
cd synapse

# Run the modern uv-based installer
python3 scripts/install-local.py
```

### **Option 3: Manual uv install**
```bash
# Clone and setup
git clone https://github.com/neoforge-dev/synapse.git
cd synapse

# Install in development mode using uv
uv pip install -e .[dev]
```

**What this gives you:**
- ✅ Full development environment
- ✅ All dependencies and tools
- ✅ Easy debugging and testing
- ✅ Local development setup

**Perfect for:** Developers, contributors, advanced users

---

## **📱 Platform-Specific Instructions**

### **macOS**
```bash
# Option 1: Homebrew (recommended)
brew install ./Formula/synapse.rb

# Option 2: One-liner installer
curl -fsSL https://raw.githubusercontent.com/neoforge-dev/synapse/main/scripts/install.sh | bash

# Option 3: pipx
pipx install synapse
```

### **Linux**
```bash
# Option 1: One-liner installer
curl -fsSL https://raw.githubusercontent.com/neoforge-dev/synapse/main/scripts/install.sh | bash

# Option 2: pipx
pip install --user pipx
export PATH="$HOME/.local/bin:$PATH"
pipx install synapse

# Option 3: Homebrew (if you have it)
brew install ./Formula/synapse.rb
```

### **Windows (WSL)**
```bash
# Option 1: One-liner installer (in WSL)
curl -fsSL https://raw.githubusercontent.com/neoforge-dev/synapse/main/scripts/install.sh | bash

# Option 2: pipx
pip install --user pipx
export PATH="$HOME/.local/bin:$PATH"
pipx install synapse
```

---

## **🧪 Testing Your Installation**

After installation, verify everything works:

```bash
# Check if synapse is available
which synapse

# Check version
synapse --version

# See help
synapse --help

# Test basic functionality
synapse init check
```

---

## **🚀 Quick Start After Installation**

### **Vector-Only Mode (No Docker Required)**
```bash
# Quick setup wizard
synapse init wizard --quick --vector-only

# Ingest your first document
echo "Hello World" | synapse ingest test.md --stdin

# Ask questions
synapse query ask "What did I just write?"
```

### **Full Mode (Docker Required)**
```bash
# Start all services
synapse up

# Ingest documents
synapse ingest ~/Documents

# Query with full graph features
synapse query ask "What are the main themes in my documents?"
```

---

## **🔧 Troubleshooting**

### **Installation Issues**
```bash
# Check Python version (need 3.10+)
python3 --version

# Check if command exists
which synapse

# Check PATH
echo $PATH

# Try manual installation
pip install synapse
```

### **Command Not Found**
```bash
# Add to PATH manually
export PATH="$HOME/.local/bin:$PATH"

# Or restart terminal
# The installer should do this automatically
```

### **Permission Issues**
```bash
# Make script executable
chmod +x scripts/install.sh

# Or use sudo (if needed)
sudo ./scripts/install.sh
```

---

## **📊 Installation Method Comparison**

| Method | Ease | Isolation | Updates | Cross-Platform | Best For |
|--------|------|-----------|---------|----------------|----------|
| **One-liner** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | New users, quick setup |
| **Homebrew** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | macOS/Linux users |
| **pipx** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Python developers |
| **uv** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Fast development |
| **Development** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Contributors, debugging |

---

## **🎯 Next Steps**

1. **Choose your installation method** from above
2. **Run the installation command**
3. **Verify installation** with `synapse --version`
4. **Quick start** with `synapse init wizard --quick --vector-only`
5. **Explore features** with `synapse --help`

---

## **💡 Pro Tips**

- **For new users**: Use the one-liner installer
- **For macOS users**: Homebrew gives the best experience
- **For developers**: Use the development setup
- **For production**: Use pipx or Homebrew for isolation
- **For testing**: Vector-only mode works without Docker

---

🎉 **Goal achieved**: Synapse is now as easy to install as `brew install synapse`!

💬 **Need help?** Open an issue on GitHub or check the [documentation](https://github.com/neoforge-dev/synapse).
