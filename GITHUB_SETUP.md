# GitHub Setup for Troya/Cascade CLI

## Create Repository on GitHub

Since `gh` CLI is not installed, create the repo manually:

### Option 1: Via GitHub Web
1. Go to https://github.com/new
2. Name: `troya`
3. Description: `Troya - AI Coding Assistant CLI (Cascade CLI fork)`
4. Make it Public or Private
5. Click "Create repository"

### Option 2: Install gh CLI first
```bash
# macOS with Homebrew
brew install gh

# Login
gh auth login

# Create repo
cd /path/to/cascade-cli
gh repo create troya --public --source=. --push
```

## Push existing code

After creating the repo on GitHub:

```bash
cd /Users/ahmedfares/CascadeProjects/cascade-cli
git remote add origin https://github.com/YOUR_USERNAME/troya.git
git branch -M main
git push -u origin main
```

## Using the `troya` command

After running `pip install -e .` in the project directory, you can use:

```bash
troya                    # Start CLI
troya --version          # Show version
troya --setup            # Run setup wizard
```

Or use the alias (added to ~/.zshrc):
```bash
alias troya='python3 -m cascade.main'
```

## Rename the CLI (optional)

To fully rebrand from "cascade" to "troya", you can:

1. Rename the package directory:
```bash
cd /Users/ahmedfares/CascadeProjects/cascade-cli
mv cascade troya
```

2. Update all internal imports from `cascade.X` to `troya.X`

3. Update `setup.py`:
```python
entry_points={
    "console_scripts": [
        "troya=troya.main:main",
    ],
},
```

4. Reinstall:
```bash
pip install -e .
```
