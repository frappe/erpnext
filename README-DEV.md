# ERPNext Development Setup

This document provides quick setup instructions for ERPNext development.

## Quick Start

1. Install Frappe Bench:
   ```bash
   pip install frappe-bench
   ```

2. Initialize bench with ERPNext:
   ```bash
   bench init frappe-bench --frappe-branch version-15
   cd frappe-bench
   bench get-app erpnext --branch version-15
   ```

3. Create and setup site:
   ```bash
   bench new-site erpnext.local
   bench --site erpnext.local install-app erpnext
   ```

4. Start development server:
   ```bash
   bench start
   ```

## IDE Setup

Configure your IDE to use the Python interpreter from your bench environment. For VS Code:
- Install the Python extension
- Select the correct Python interpreter from your virtual environment or bench setup

## Running Tests

```bash
bench run-tests --app erpnext
```

Or for specific modules:
```bash
bench run-tests --module erpnext.accounts.tests.test_accounts
```

## Additional Documentation

See [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md) for detailed setup instructions.