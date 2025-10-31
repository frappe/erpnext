# ERPNext Project

## Overview

This is the **ERPNext** application codebase - an open-source ERP (Enterprise Resource Planning) system built by Frappe Technologies. ERPNext is a comprehensive business management system that handles accounting, inventory, manufacturing, CRM, and more.

## Important Information

### What This Repository Contains

This repository contains **only the ERPNext application code**, not a complete running system. ERPNext is built on top of the **Frappe Framework** and requires a full Frappe development environment to run.

### Architecture

- **Language**: Python 3.10+
- **Framework**: Frappe Framework (full-stack web framework)
- **Database**: MariaDB/PostgreSQL
- **Frontend**: JavaScript, Vue.js (via Frappe UI)
- **Package Manager**: Python (pip/flit), Node.js (yarn)

### Why It Cannot Run Directly in Replit

ERPNext is **not a standalone application**. It requires:

1. **Frappe Framework** - The underlying framework (not included in this repo)
2. **Bench** - A CLI tool for managing Frappe sites and apps
3. **MariaDB/PostgreSQL** - Database server
4. **Redis** - For caching and job queues
5. **A Frappe site** - ERPNext installs as an "app" on a Frappe site

The typical development setup involves:
```bash
# Install bench
pip install frappe-bench

# Create a new bench
bench init frappe-bench

# Create a site
bench new-site mysite.local

# Get ERPNext app
bench get-app erpnext

# Install ERPNext on the site
bench --site mysite.local install-app erpnext

# Start the server
bench start
```

### What Would Be Needed to Run This

To run ERPNext in any environment (including Replit), you would need:

1. **Full Frappe Framework installation**
2. **Frappe Bench setup**
3. **MariaDB or PostgreSQL database** (with specific configuration)
4. **Redis server** (for background jobs and caching)
5. **Node.js** (for building frontend assets)
6. **System dependencies** (wkhtmltopdf for PDF generation, etc.)

This would be a **very complex setup** requiring significant system resources and configuration.

## Recommended Alternatives

### For Development/Testing ERPNext:

1. **Frappe Cloud** (https://frappecloud.com)
   - Managed hosting specifically for Frappe/ERPNext
   - Free trial available
   - Handles all infrastructure

2. **Local Docker Setup**
   ```bash
   git clone https://github.com/frappe/frappe_docker
   cd frappe_docker
   docker compose -f pwd.yml up -d
   ```
   - Complete development environment
   - Accessible at localhost:8080
   - Default credentials: Administrator/admin

3. **Full Local Installation**
   - Follow: https://frappeframework.com/docs/user/en/installation
   - Requires more setup but gives full control

### For Learning About This Codebase:

This repository is useful for:
- Understanding ERPNext's code structure
- Contributing to ERPNext development
- Building custom modules/extensions
- Learning the Frappe framework patterns

## Project Structure

```
erpnext/
├── accounts/          # Accounting module
├── assets/           # Asset management
├── buying/           # Purchase management
├── crm/              # Customer relationship management
├── manufacturing/    # Production and manufacturing
├── projects/         # Project management
├── selling/          # Sales management
├── stock/            # Inventory management
├── setup/            # Setup and configuration
├── public/           # Static assets (CSS, JS, images)
├── www/              # Web pages and portals
└── hooks.py          # Frappe hooks configuration
```

## Dependencies

### Python Dependencies (pyproject.toml)
- Core: Unidecode, barcodenumber, rapidfuzz, holidays
- Integrations: googlemaps, plaid-python, python-youtube
- Data: pandas, statsmodels, mt-940

### JavaScript Dependencies (package.json)
- onscan.js: Barcode scanner support

### Framework Dependency
- Frappe Framework: >=16.0.0-dev,<17.0.0

## Recent Changes

**October 31, 2025**: Repository imported into Replit. Documented that this is an ERPNext application that requires the Frappe Framework ecosystem to run.

## User Preferences

None set yet.

## Notes

This is a **reference/development repository only** in its current state. To actually run ERPNext, you need the complete Frappe infrastructure as described above.
