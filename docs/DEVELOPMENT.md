# Development Guide

## Automatic Code Cleanup & Formatting

### Quick Commands

```bash
# 🚀 Complete code cleanup (recommended)
python clean_code.py

# 🔍 Just check code quality
python clean_code.py --check-only

# 📝 Format only with Black
python format_code.py
```

## Code Formatting with Black

This project uses [Black](https://github.com/psf/black) for automatic code formatting to ensure consistent code style.

### Configuration

Black is configured in `pyproject.toml`:
- Line length: 100 characters
- Target version: Python 3.11+
- Excludes: `.venv`, `build`, `dist`, etc.

### Usage

#### Option 1: Direct Black command
```bash
# Format all files in src directory
black src/

# Check if files are formatted (without making changes)
black --check src/

# Show what would be changed
black --diff src/
```

#### Option 2: Using the format script
```bash
# Format all files
python format_code.py

# Check formatting without changes
python format_code.py --check
```

#### Option 3: Pre-commit hooks (recommended)
```bash
# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### IDE Integration

#### VS Code
Install the "Black Formatter" extension and add to your settings:
```json
{
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--config", "pyproject.toml"],
    "editor.formatOnSave": true
}
```

#### PyCharm
1. Go to File → Settings → Tools → External Tools
2. Click "+" to add a new tool
3. Set:
   - Name: Black
   - Program: black
   - Arguments: $FilePath$
   - Working directory: $ProjectFileDir$

## Complete Code Cleanup Tools

### clean_code.py - Comprehensive Cleanup
This script runs multiple tools in sequence for complete code cleanup:

1. **autoflake** - Removes unused imports and variables
2. **isort** - Sorts and organizes imports
3. **autopep8** - Fixes PEP8 style issues  
4. **black** - Final consistent formatting

```bash
# Full cleanup
python clean_code.py

# Target specific directory
python clean_code.py --target tests/

# Check quality only
python clean_code.py --check-only
```

### Individual Tools

```bash
# Remove unused imports and variables
autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive src/

# Sort imports (compatible with Black)
isort src/ --profile black --line-length 100

# Fix PEP8 issues
autopep8 --in-place --aggressive --aggressive --recursive src/

# Final Black formatting
black src/
```

### Code Quality Improvements

Evolution of code quality scores:
- **Original score**: 6.04/10
- **After Black**: 7.52/10 (+1.48)
- **After full cleanup**: 7.03/10 (comprehensive fixes applied)

### Files Processed

- ✅ **27 Python files** in src/ directory
- ✅ Unused imports removed
- ✅ Import order standardized
- ✅ PEP8 compliance improved
- ✅ Consistent Black formatting applied

## Running Tests

```bash
# Run pytest
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src/

# Run specific test file
python -m pytest tests/test_api_v2.py -v
```

## Linting

```bash
# Run pylint on src directory
pylint src/

# Run with specific configuration
pylint src/ --disable=missing-module-docstring,missing-class-docstring
```

## Development Workflow

1. Write your code
2. Run tests: `python -m pytest`
3. Format code: `python format_code.py` or `black src/`
4. Check linting: `pylint src/`
5. Commit your changes

### Automated Quality Checks

The pre-commit hooks will automatically:
- Format code with Black
- Check imports with isort  
- Lint code with flake8
- Ensure consistent code quality before commits