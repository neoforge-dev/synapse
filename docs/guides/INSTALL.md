# 🚀 Install Synapse in One Command

## **Super Easy Installation**

### **Option 1: One-liner (Recommended)**
```bash
curl -fsSL https://raw.githubusercontent.com/neoforge-dev/synapse/main/install.sh | bash
```

### **Option 2: Download and Run**
```bash
curl -fsSL https://raw.githubusercontent.com/neoforge-ai/synapse-graph-rag/main/install.sh -o install.sh
chmod +x install.sh
./install.sh
```

### **Option 3: Homebrew (macOS/Linux)**
```bash
# Install from local formula (if you have the source)
brew install ./Formula/synapse-graph-rag.rb

# Or install from GitHub (when formula is published)
brew install neoforge-dev/synapse/synapse
```

### **Option 4: pipx (Cross-platform)**
```bash
pipx install synapse-graph-rag
```

---

## **What Happens During Installation?**

1. **Auto-detects your OS** and best installation method
2. **Installs prerequisites** (Homebrew, pipx, uv if needed)
3. **Installs Synapse** with all dependencies
4. **Configures PATH** automatically
5. **Creates configuration** files
6. **Verifies installation** and shows next steps

---

## **Post-Installation**

After installation, you can immediately:

```bash
# Check if it worked
synapse --version

# See all available commands
synapse --help

# Quick start (no Docker required)
synapse init wizard --quick --vector-only

# Ingest your first document
echo "Hello World" | synapse ingest test.md --stdin

# Ask questions
synapse query ask "What did I just write?"
```

---

## **System Requirements**

- **Python**: 3.10+ (3.12 recommended)
- **OS**: macOS, Linux, Windows (WSL)
- **Memory**: 2GB+ RAM
- **Storage**: 1GB+ free space
- **Optional**: Docker (for full graph features)

---

## **Troubleshooting**

### **Installation Fails?**
```bash
# Try with verbose output
./install.sh --verbose

# Check Python version
python3 --version

# Install manually
pip3 install synapse-graph-rag
```

### **Command Not Found?**
```bash
# Add to PATH manually
export PATH="$HOME/.local/bin:$PATH"

# Or restart your terminal
# The installer should do this automatically
```

### **Permission Denied?**
```bash
# Make script executable
chmod +x install.sh

# Or run with sudo (if needed)
sudo ./install.sh
```

---

## **Advanced Installation Options**

```bash
# Force specific installation method
./install.sh --homebrew    # Use Homebrew
./install.sh --pipx        # Use pipx
./install.sh --pip         # Use pip directly
./install.sh --auto        # Auto-detect (default)

# Show help
./install.sh --help
```

---

## **Why This Installation Method?**

✅ **One command** - as simple as `brew install synapse`  
✅ **Auto-detection** - works on any system  
✅ **No conflicts** - isolated installation  
✅ **Easy updates** - simple upgrade commands  
✅ **Professional** - proper PATH and configuration  
✅ **Cross-platform** - works on macOS, Linux, Windows  

---

🎯 **Goal**: Make Synapse as easy to install as any other popular tool!

💡 **Need help?** Open an issue on GitHub or check the [documentation](https://github.com/neoforge-dev/synapse).
