# ERPNext Development Setup

This document provides instructions for setting up a development environment for ERPNext.

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.10 or higher
- Node.js and npm
- Git
- A code editor (VS Code recommended)

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/frappe/erpnext.git
   cd erpnext
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Install frappe framework**:
   The frappe framework needs to be installed separately. See [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md) for detailed instructions.

## Resolving Import Errors

If you see "Import 'frappe' could not be resolved" errors:

1. Make sure you have installed the frappe framework
2. Configure your IDE to use the correct Python interpreter
3. Refer to [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md) for detailed instructions

## IDE Configuration

### VS Code

1. Install the Python extension
2. Open the workspace settings (`.vscode/settings.json`)
3. Select the Python interpreter from the virtual environment

### Other IDEs

Configure your IDE to:
1. Use the Python interpreter from the virtual environment
2. Include the frappe directory in the Python path

## Testing

To run tests:
```bash
# Run all tests
python -m pytest

# Run specific tests
python -m pytest erpnext/accounts/test/test_accounts.py
```

## Contributing

Please read [CONTRIBUTING.md](.github/CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Additional Resources

- [Frappe Framework Documentation](https://frappeframework.com/docs)
- [ERPNext Documentation](https://docs.erpnext.com/)
- [Development Setup Guide](DEVELOPMENT_SETUP.md)