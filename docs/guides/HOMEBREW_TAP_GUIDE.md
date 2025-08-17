# 🍺 Publishing the Synapse Homebrew Tap

This guide will help you publish the Synapse Homebrew tap so users can simply run `brew install synapse`.

## 🎯 What We're Building

A Homebrew tap that allows users to install Synapse with:
```bash
brew tap neoforge-dev/synapse
brew install synapse
```

## 📋 Prerequisites

1. **GitHub CLI** (`gh`) - for creating repositories
2. **Homebrew** - for testing formulas
3. **Git** - for version control
4. **GitHub account** - with appropriate permissions

## 🚀 Quick Start (Automated)

### **Option 1: Use the Publisher Script**
```bash
# Make sure you're in the Synapse project root
cd /path/to/synapse

# Run the publisher script
./publish-tap.sh
```

The script will:
- Ask for your GitHub username/organization
- Create the tap repository
- Set up the formula
- Test everything
- Show you the final installation commands

### **Option 2: Manual Setup**
If you prefer to do it manually, follow the steps below.

## 🔧 Manual Setup Steps

### **Step 1: Create the Tap Repository**

```bash
# Create a new repository on GitHub
gh repo create neoforge-dev/synapse \
  --public \
  --description "Homebrew tap for Synapse" \
  --homepage "https://github.com/neoforge-dev/synapse"
```

### **Step 2: Clone and Setup the Tap**

```bash
# Clone the tap repository
git clone https://github.com/neoforge-dev/synapse.git homebrew-tap
cd homebrew-tap

# Copy the formula
mkdir -p Formula
cp ../Formula/synapse.rb Formula/
```

### **Step 3: Test the Formula**

```bash
# Test the formula locally
brew audit --strict Formula/synapse.rb
brew style Formula/synapse.rb

# Test installation (optional)
brew install ./Formula/synapse.rb
```

### **Step 4: Push to GitHub**

```bash
# Add and commit files
git add .
git commit -m "Initial commit: Synapse Homebrew tap"
git push -u origin main
```

## 📁 Tap Repository Structure

Your tap repository should look like this:
```
synapse/ (tap repository)
├── README.md
├── Formula/
│   └── synapse.rb
└── .github/
    └── workflows/
        └── update-formula.yml
```

## 🔄 Automatic Updates

The tap includes a GitHub Action that automatically updates the formula when you create new releases:

1. **Create a GitHub release** in the main Synapse repository
2. **The Action runs automatically** and updates the formula
3. **Users can upgrade** with `brew upgrade synapse`

## 🧪 Testing Your Tap

### **Test the Formula Locally**
```bash
# From the tap directory
brew audit --strict Formula/synapse.rb
brew style Formula/synapse.rb
```

### **Test Installation from Tap**
```bash
# Add your tap
brew tap neoforge-dev/synapse

# Install Synapse
brew install synapse

# Test the installation
synapse --version
synapse --help
```

### **Test Updates**
```bash
# Update the tap
brew update

# Check for updates
brew outdated

# Upgrade Synapse
brew upgrade synapse
```

## 📝 Formula Maintenance

### **Updating the Formula Manually**
```bash
# Get the SHA256 of a new release
curl -sL "https://github.com/neoforge-dev/synapse/archive/refs/tags/v1.0.0.tar.gz" | shasum -a 256

# Update the formula file
sed -i 's|sha256 ".*"|sha256 "NEW_SHA256_HASH"|' Formula/synapse.rb
sed -i 's|url ".*"|url "NEW_URL"|' Formula/synapse.rb
```

### **Adding Dependencies**
If you need to add new dependencies to the formula:

```ruby
# Add to the depends_on section
depends_on "python@3.11"
depends_on "node" => :optional  # Optional dependency

# Add Python packages as resources
resource "new-package" do
  url "https://files.pythonhosted.org/packages/source/n/new-package/new-package-1.0.0.tar.gz"
  sha256 "SHA256_HASH"
end
```

## 🚨 Common Issues and Solutions

### **Formula Fails Audit**
```bash
# Check specific issues
brew audit --strict Formula/synapse.rb

# Common fixes:
# - Update SHA256 hashes
# - Fix URL formats
# - Add missing dependencies
# - Fix style issues
```

### **Installation Fails**
```bash
# Check Homebrew doctor
brew doctor

# Check formula info
brew info synapse

# Check logs
brew install synapse --verbose
```

### **GitHub Action Fails**
- Check the workflow file syntax
- Verify repository permissions
- Check if the release tarball is accessible
- Verify the formula syntax

## 📊 Publishing Checklist

Before publishing your tap, ensure:

- [ ] Formula passes `brew audit --strict`
- [ ] Formula passes `brew style`
- [ ] Formula installs successfully
- [ ] README.md is complete and helpful
- [ ] GitHub Action is properly configured
- [ ] Repository is public
- [ ] Formula has proper descriptions and metadata

## 🎉 After Publishing

Once your tap is published, users can install Synapse with:

```bash
# Method 1: Add tap then install
brew tap neoforge-dev/synapse
brew install synapse

# Method 2: Install directly
brew install neoforge-dev/synapse/synapse

# Method 3: Update existing installation
brew upgrade synapse
```

## 🔗 Useful Links

- **Homebrew Documentation**: https://docs.brew.sh/
- **Formula Cookbook**: https://docs.brew.sh/Formula-Cookbook
- **GitHub CLI**: https://cli.github.com/
- **Synapse Project**: https://github.com/neoforge-dev/synapse

## 💡 Pro Tips

1. **Test locally first** - Always test your formula before pushing
2. **Use semantic versioning** - Follow semver for releases
3. **Automate everything** - Let GitHub Actions handle updates
4. **Document well** - Clear README helps users
5. **Monitor issues** - Respond to user feedback quickly

---

🎯 **Goal**: Make Synapse installation as simple as `brew install synapse`!

🚀 **Ready to publish?** Run `./publish-tap.sh` to get started!
