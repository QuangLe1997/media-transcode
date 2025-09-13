# Development Guide

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

### Code Quality Improvements

After applying Black formatting:
- **Previous Pylint score**: 6.04/10
- **New Pylint score**: 7.52/10 
- **Improvement**: +1.48 points

### Files Formatted

Black has been applied to all Python files in the `src/` directory:
- 24 files reformatted
- 3 files left unchanged
- All files now comply with Black formatting standards

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