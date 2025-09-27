# ERPNext Development Environment Setup

This guide provides step-by-step instructions to set up a proper development environment for ERPNext, resolving common issues like import errors and configuration problems.

## Prerequisites

Before you begin, ensure you have:
- Python 3.10 or higher
- Node.js 16 or higher
- yarn
- A code editor (VS Code recommended)

## Setup Instructions

### 1. Install Frappe Bench

```bash
pip install frappe-bench
```

### 2. Initialize a new bench

```bash
bench init frappe-bench --frappe-branch version-15
cd frappe-bench
```

### 3. Create a new site

```bash
bench new-site erpnext.local
```

### 4. Get ERPNext (pinned to version-15 branch)

```bash
bench get-app erpnext --branch version-15
```

### 5. Install ERPNext on your site

```bash
bench --site erpnext.local install-app erpnext
```

### 6. Start the development server

```bash
bench start
```

## IDE Configuration

### Visual Studio Code

1. Open the project in VS Code
2. Install the recommended extensions:
   - Python
   - Pylint
   - EditorConfig
3. Select the correct Python interpreter from your virtual environment or bench setup

### Other IDEs

For other IDEs, ensure you:
- Configure the Python interpreter to use the one from your bench environment
- Set up proper linting with pylint and flake8
- Configure auto-formatting with black

## Resolving Import Errors

If you encounter "Import 'frappe' could not be resolved" errors:

1. Ensure you're using the correct Python interpreter from your bench environment
2. Check that frappe and erpnext are properly installed in your bench
3. Verify your IDE's Python path includes the bench apps directories

## Running Tests

To run ERPNext tests:

```bash
bench run-tests --app erpnext
```

Or for specific test files:

```bash
bench run-tests --module erpnext.accounts.tests.test_accounts
```

## Additional Resources

- [ERPNext Documentation](https://docs.erpnext.com)
- [Frappe Framework Documentation](https://frappeframework.com)
- [ERPNext GitHub Repository](https://github.com/frappe/erpnext)