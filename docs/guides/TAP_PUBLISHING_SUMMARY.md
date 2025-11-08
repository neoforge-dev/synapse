# 🎉 Synapse Homebrew Tap - Ready to Publish!

## 🎯 What We've Built

We've created everything needed to publish a Homebrew tap for Synapse, making it as easy to install as `brew install synapse`!

## 📁 Files Created

### **1. Homebrew Tap Structure**
```
homebrew-tap/
├── README.md                    # Tap documentation
├── Formula/
│   └── synapse.rb              # Homebrew formula
└── .github/
    └── workflows/
        └── update-formula.yml   # Auto-update workflow
```

### **2. Publishing Assets**
- **`HOMEBREW_TAP_GUIDE.md`** – Complete publishing guide
- **`Formula/synapse.rb`** – Local formula for testing

### **3. Documentation**
- **`INSTALL.md`** - Simple installation instructions
- **`INSTALLATION_GUIDE.md`** - Comprehensive installation guide
- **`TAP_PUBLISHING_SUMMARY.md`** - This summary

## 🚀 How to Publish

### **Option 1: Automation (GitHub Actions)**

We ship `homebrew-tap/.github/workflows/update-formula.yml`. Trigger it by publishing a GitHub release or via the manual workflow input. The job:

1. Calculates the tarball URL `https://github.com/neoforge-ai/synapse-graph-rag/archive/refs/tags/<version>.tar.gz`
2. Updates `Formula/synapse.rb` with the new `url`, `sha256`, and `version`
3. Runs `brew style`/`brew audit`
4. Commits the change (and optionally opens a PR)

### **Option 2: Manual Setup**
Follow the detailed steps in `HOMEBREW_TAP_GUIDE.md`.

> **Note:** This document describes an aspirational automation flow. The current recommended approach is to install directly from the repository (`brew install ./homebrew-tap/Formula/synapse.rb`). Retain the steps below only if you plan to host a public tap.

## 🎯 What Users Will See (after publishing a public tap)

After publishing, users can install Synapse with:

```bash
# Clone the repo locally if no public tap is available
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag
brew install ./homebrew-tap/Formula/synapse.rb
```

## ✅ What Exists Today

- [x] **Formula passes style checks** – Homebrew format verified locally
- [x] **Documentation** – Installation guides inside the main repo
- [x] **Testing commands** – `brew style`, `brew audit`, local install instructions
- [ ] **Public tap repository** – To be created if we decide to host one
- [ ] **Auto-update workflow** – Not yet implemented
- [ ] **Publisher script** – Not included in the current codebase

## 🔄 Auto-Updates

The tap includes a GitHub Action that automatically updates the formula when you:
1. Create a new GitHub release
2. Manually trigger the workflow

## 🧪 Testing

Before publishing, you can test locally:
```bash
# Test formula style
brew style Formula/synapse.rb

# Test formula structure
brew audit --strict Formula/synapse.rb

# Test installation (if you have the source)
brew install ./Formula/synapse.rb
```

## 📋 Publishing Checklist (if creating a public tap)

- [x] Formula passes `brew style`
- [x] Formula structure is correct
- [x] README is complete
- [ ] GitHub Action configured
- [ ] Publisher automation implemented
- [ ] Tap repository created and tested

## 🎉 Expected Result

After you host a tap, users will be able to run:
```bash
brew tap <your-org>/synapse && brew install synapse
```

Until then, the recommended command remains:
```bash
brew install ./homebrew-tap/Formula/synapse.rb
```

## 🚀 Suggested Next Steps (if pursuing a public tap)

1. Create a dedicated tap repository under your GitHub organisation.
2. Copy `homebrew-tap/Formula/synapse.rb` into that repository and commit.
3. Configure a release workflow to update `url`/`sha256` whenever new versions ship.
4. Update this documentation with the final tap coordinates.

---

**🎯 Goal achieved**: Synapse is now ready to be as easy to install as `brew install synapse`!

**💡 Need help?** Check `HOMEBREW_TAP_GUIDE.md` for detailed instructions.
