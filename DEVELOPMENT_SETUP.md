# Development Environment Setup for ERPNext

## Issue: "Import 'frappe' could not be resolved"

This is a common issue when working with ERPNext/Frappe development where the Python interpreter or linter cannot find the frappe module.

## Root Cause

The error occurs because the Python interpreter or linter (basedpyright) cannot locate the `frappe` module. This is a common issue in ERPNext/Frappe development environments for the following reasons:

1. **Missing Development Environment Setup**: The `frappe` module is not a standard Python package that can be installed via pip. It's part of the Frappe Framework which needs to be properly set up in a development environment.

2. **Incorrect Python Path**: The Python interpreter doesn't know where to find the `frappe` module because it's not in the standard Python path.

3. **Missing Frappe Framework**: The `frappe` module is the core framework that ERPNext runs on, but it's not included in the ERPNext repository itself - it needs to be installed separately.

## Solutions

### Option 1: Set up proper development environment using Bench (Recommended for Unix/Linux/macOS)

1. **Install prerequisites**:
   - Python 3.10+ (as specified in pyproject.toml)
   - Node.js & npm
   - Redis
   - MariaDB
   - wkhtmltopdf

2. **Install Bench CLI**:
   ```bash
   pip install frappe-bench
   ```

3. **Initialize a new bench**:
   ```bash
   bench init frappe-bench --frappe-branch version-15
   cd frappe-bench
   ```

4. **Create a new site**:
   ```bash
   bench new-site erpnext.local
   ```

5. **Get ERPNext app**:
   ```bash
   bench get-app erpnext
   ```

6. **Install ERPNext on your site**:
   ```bash
   bench --site erpnext.local install-app erpnext
   ```

7. **Start development server**:
   ```bash
   bench start
   ```

### Option 2: Use Docker development environment (Recommended for Windows)

Based on the documentation, using Docker with VS Code devcontainer is the easiest way to start development:

1. **Install Docker Desktop**

2. **Use frappe_docker with devcontainer**:
   ```bash
   git clone https://github.com/frappe/frappe_docker
   ```

### Option 3: Configure your IDE/editor to recognize the frappe module

If you're working on just the code without running the full environment, you can:

1. **Create a virtual environment**:
   ```bash
   python -m venv erpnext-env
   source erpnext-env/bin/activate  # On Windows: erpnext-env\Scripts\activate
   ```

2. **Install frappe in development mode**:
   You would need to clone the frappe repository and install it in development mode:
   ```bash
   git clone https://github.com/frappe/frappe
   cd frappe
   pip install -e .
   ```

3. **Configure your IDE's Python interpreter** to use the virtual environment where frappe is installed.

## For Windows Users

Setting up Frappe/ERPNext development environments on Windows can be challenging due to Unix-specific dependencies. We recommend:

1. **Use Docker**: This is the most reliable approach for Windows users
2. **Use WSL (Windows Subsystem for Linux)**: Install WSL2 and set up the development environment in a Linux environment
3. **Use GitHub Codespaces**: If available, this provides a cloud-based development environment

## IDE Configuration

To resolve the import error in your IDE:

1. **VS Code**: 
   - Install the Python extension
   - Select the correct Python interpreter from your virtual environment or bench setup
   - Install the Frappe extension for better support

2. **PyCharm**:
   - Configure the Python interpreter to point to your virtual environment
   - Add the frappe directory to the project sources

3. **Other IDEs**:
   - Ensure the Python path includes the frappe module location
   - Configure the interpreter to use the virtual environment where frappe is installed

## Troubleshooting

If you continue to see import errors:

1. Verify that frappe is properly installed in your environment
2. Check that your IDE is using the correct Python interpreter
3. Ensure that the frappe module is in the Python path
4. Restart your IDE after making configuration changes

## Additional Resources

- [Frappe Framework Documentation](https://frappeframework.com/docs)
- [ERPNext Documentation](https://docs.erpnext.com/)
- [Frappe Docker Setup](https://github.com/frappe/frappe_docker)