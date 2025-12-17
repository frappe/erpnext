# ERPNext CT Installation - Project Analysis

**Analysis Date:** 2025-12-17
**Project:** ERPNext (betaerpnext)
**Version:** 16.0.0-dev
**License:** GNU General Public License v3

---

## Executive Summary

This is **ERPNext**, an open-source Enterprise Resource Planning (ERP) system developed by Frappe Technologies Pvt. Ltd. It's a comprehensive business management software that handles accounting, inventory, manufacturing, CRM, HR, and more.

**Project Size:** ~266 MB
**Current Branch:** `claude/review-ct-installation-loT79`
**Repository:** https://github.com/frappe/erpnext

---

## Technology Stack

### Backend
- **Language:** Python 3.10+ (currently running on Python 3.11.14)
- **Framework:** Frappe Framework >= 16.0.0-dev, < 17.0.0
- **App Architecture:** Modular Python application with 44 modules

### Frontend
- **Primary UI:** Frappe UI (Vue.js-based)
- **Additional:** JavaScript, HTML, CSS
- **JS Library:** onscan.js for barcode scanning

### Database
- **Primary:** MariaDB 10.6+ (preferred)
- **Alternative:** PostgreSQL (supported)

### Key Dependencies
```
Core:
- Unidecode ~1.4.0
- barcodenumber ~0.5.0
- rapidfuzz ~3.12.2
- holidays ~0.75

Integrations:
- googlemaps ~4.10.0
- plaid-python ~7.2.1
- python-youtube ~0.9.7

Data Processing:
- pandas ~2.2.2
- statsmodels ~0.14.5
- mt-940 >=4.26.0 (for bank statements)

Others:
- pypng ~0.20220715.0
```

---

## ERPNext Modules

The system contains 40+ modules organized by business function:

### Financial Management
- **accounts** - Complete accounting system (GL, AR, AP, bank reconciliation)
- **assets** - Asset management and depreciation

### Sales & Marketing
- **crm** - Customer Relationship Management
- **selling** - Sales orders, quotations, and delivery
- **portal** - Customer/Supplier web portal

### Procurement & Inventory
- **buying** - Purchase orders and supplier management
- **stock** - Inventory management and warehouse operations
- **quality_management** - Quality control and inspection

### Manufacturing
- **manufacturing** - Production planning and execution
- **subcontracting** - Subcontracting workflow management

### Human Resources
- **hr** - Employee management, payroll, attendance
- **payroll** - Salary processing and payslips

### Project Management
- **projects** - Project tracking, timesheets, and tasks

### Support & Services
- **support** - Help desk and ticketing system
- **maintenance** - Maintenance management

### Integration & Utilities
- **erpnext_integrations** - Third-party integrations (Google, Plaid, etc.)
- **edi** - Electronic Data Interchange
- **regional** - Country-specific customizations
- **telephony** - Phone integration
- **e_commerce** - E-commerce functionality

---

## System Requirements for CT Installation

### Minimum Requirements

#### Computing Resources
- **CPU:** 2 cores minimum, 4+ recommended
- **RAM:** 4GB minimum, 8GB+ recommended for production
- **Storage:** 20GB minimum, 50GB+ recommended
- **Container Type:** LXC container (privileged or unprivileged with proper permissions)

#### Software Stack
```bash
Operating System:
- Ubuntu 22.04 LTS or 24.04 LTS (recommended)
- Debian 11 or 12

Python:
- Python 3.10, 3.11, or 3.12
- pip, virtualenv
- python3-dev

Database:
- MariaDB 10.6+ OR PostgreSQL 13+
- Database client libraries (libmysqlclient-dev or libpq-dev)

Node.js:
- Node.js 18.x or 20.x LTS
- npm or yarn

Additional System Packages:
- git
- redis-server (for caching and job queues)
- wkhtmltopdf (for PDF generation)
- curl, wget
- build-essential
- libffi-dev
- libssl-dev
- libjpeg-dev
- libpng-dev
- zlib1g-dev
```

### Network Requirements
- **Ports:**
  - 8000-8005: Development/Bench server
  - 3306: MariaDB (if exposed)
  - 5432: PostgreSQL (if exposed)
  - 6379: Redis
  - 9000: SocketIO (real-time updates)
  - 80/443: Production (nginx/apache)

---

## Installation Architecture

### Frappe Bench Structure
ERPNext uses the "Bench" CLI tool for installation and management:

```
frappe-bench/
├── apps/
│   ├── frappe/          # Core framework
│   └── erpnext/         # This application
├── sites/
│   └── site1.local/     # Site-specific data
│       ├── site_config.json
│       ├── private/
│       └── public/
├── config/
│   ├── nginx.conf
│   ├── supervisor.conf
│   └── redis_*.conf
└── env/                 # Python virtual environment
```

### Installation Methods

#### 1. Manual Installation (Recommended for CT)
```bash
# Install bench
pip3 install frappe-bench

# Initialize bench
bench init frappe-bench --frappe-branch version-16

# Create new site
cd frappe-bench
bench new-site mysite.local

# Get ERPNext
bench get-app erpnext --branch version-16

# Install ERPNext on site
bench --site mysite.local install-app erpnext

# Start development server
bench start
```

#### 2. Docker Installation (Alternative)
- Repository: https://github.com/frappe/frappe_docker
- Suitable for containerized deployments
- Includes all dependencies pre-configured

---

## Database Schema

### Key Database Features
- **Multi-company:** Support for multiple companies in one installation
- **Multi-currency:** Foreign exchange and multi-currency transactions
- **Custom Fields:** Extensive customization capabilities
- **DocTypes:** 500+ document types (tables)
- **Workflow Engine:** Customizable approval workflows

### Default Data Created on Installation
- Standard roles and permissions
- Default chart of accounts templates (50+ countries)
- Standard report templates
- Email templates
- Print formats
- Dashboard configurations

---

## Configuration Files

### Site Configuration
Location: `sites/[site-name]/site_config.json`

Key settings:
```json
{
  "db_name": "database_name",
  "db_password": "password",
  "db_type": "mariadb",
  "redis_cache": "redis://localhost:6379",
  "redis_queue": "redis://localhost:6379/1",
  "redis_socketio": "redis://localhost:6379/2"
}
```

### Application Hooks
File: `/home/user/betaerpnext/erpnext/hooks.py`

Defines:
- Document type customizations
- Scheduled tasks
- Event handlers
- Custom routes
- Permission overrides

---

## Security Considerations

### Authentication
- Built-in user authentication
- Two-factor authentication support
- OAuth integration available
- LDAP integration supported

### Data Security
- Role-based access control (RBAC)
- Document-level permissions
- Field-level permissions
- Encryption for sensitive fields

### Network Security
- HTTPS strongly recommended for production
- Redis should not be exposed externally
- Database should be on private network/localhost
- API rate limiting available

---

## Production Deployment Components

### Required Services
1. **Web Server:** nginx or Apache (reverse proxy)
2. **WSGI Server:** Gunicorn (Python application server)
3. **Background Workers:** Celery-based job queue
4. **Scheduler:** Cron-based task scheduler
5. **WebSocket Server:** SocketIO for real-time updates
6. **Cache:** Redis
7. **Database:** MariaDB/PostgreSQL

### Process Management
- **Supervisor:** Recommended for managing all services
- **systemd:** Alternative for service management

---

## CT-Specific Recommendations

### Container Configuration

#### LXC Features Required
```
features: nesting=1
```

#### Mount Points (if needed)
```
# For shared storage
mp0: /mnt/shared,mp=/mnt/shared

# For backups
mp1: /mnt/backups,mp=/backup
```

#### Memory and Swap
```
memory: 8192
swap: 4096
```

#### Network
```
# Bridged network recommended
net0: name=eth0,bridge=vmbr0,firewall=1,ip=dhcp
```

### File System
- **Root FS:** 30GB minimum
- **Database Storage:** Consider separate mount for `/var/lib/mysql`
- **File Storage:** Consider separate mount for `sites/[site]/private` and `sites/[site]/public`

### Backup Strategy
```bash
# Site backup (includes database + files)
bench --site mysite.local backup

# Automated backups
bench --site mysite.local backup --with-files
```

### Performance Tuning for CT
1. **Database:**
   - Tune MariaDB for container memory limits
   - Enable query cache
   - Optimize buffer pool size

2. **Python:**
   - Use Gunicorn with multiple workers (2-4 workers)
   - Enable preload for faster responses

3. **Redis:**
   - Configure maxmemory policy
   - Enable persistence if needed

4. **System:**
   - Disable swap if using SSD storage
   - Enable kernel features for containers

---

## Testing & Quality Assurance

### Test Suite
- 500+ unit tests
- Integration tests for modules
- UI tests available
- CI/CD via GitHub Actions

### Code Quality Tools
- **Linters:** Ruff (Python), ESLint (JavaScript)
- **Formatters:** Configured via `.editorconfig`
- **Pre-commit Hooks:** Defined in `.pre-commit-config.yaml`

---

## Migration & Updates

### Version Compatibility
- **Current:** 16.0.0-dev
- **Frappe Framework:** Must match version (16.x)
- **Database Migrations:** Automatic via `bench migrate`

### Update Process
```bash
# Update all apps
bench update

# Migrate database
bench --site mysite.local migrate

# Build assets
bench build

# Restart services
bench restart
```

---

## Common Issues & Solutions

### Installation Issues
1. **Permission Errors:** Ensure proper user permissions for frappe user
2. **Port Conflicts:** Check if ports 8000-8005 are available
3. **Database Connection:** Verify MariaDB/PostgreSQL credentials

### Container-Specific Issues
1. **Nested Virtualization:** Enable nesting feature
2. **AppArmor/SELinux:** May need adjustments for certain operations
3. **Resource Limits:** Monitor memory and CPU usage

---

## Documentation Resources

- **Official Docs:** https://docs.erpnext.com/
- **Developer Docs:** https://frappeframework.com/docs/
- **Forum:** https://discuss.frappe.io/
- **GitHub Issues:** https://github.com/frappe/erpnext/issues
- **Frappe School:** https://frappe.io/school (training videos)

---

## Next Steps for CT Installation

1. **Prepare CT Environment:**
   - Create LXC container with Ubuntu 22.04/24.04
   - Allocate sufficient resources (8GB RAM, 4 cores, 50GB disk)
   - Configure network settings

2. **Install System Dependencies:**
   - Python 3.11+
   - MariaDB 10.6+
   - Node.js 18.x LTS
   - Redis server
   - Build tools and libraries

3. **Install Frappe Bench:**
   - Create frappe user
   - Install bench CLI
   - Initialize bench environment

4. **Deploy ERPNext:**
   - Clone this repository or get from official source
   - Create site
   - Install ERPNext app
   - Configure site settings

5. **Production Setup:**
   - Configure nginx/supervisor
   - Set up SSL certificates
   - Configure backups
   - Enable firewall rules

6. **Post-Installation:**
   - Run setup wizard
   - Configure company settings
   - Import master data
   - Train users

---

## Contact & Support

- **Developer:** Frappe Technologies Pvt. Ltd.
- **Email:** developers@frappe.io
- **Community Support:** https://discuss.frappe.io/c/erpnext/6
- **Commercial Support:** https://frappe.io/support

---

## License Compliance

**License:** GNU General Public License v3.0

Key Points:
- Free to use, modify, and distribute
- Must maintain GPL license for derivatives
- Source code must remain available
- No warranty provided

---

## Conclusion

ERPNext is a production-ready, enterprise-grade ERP system suitable for CT deployment. The modular architecture and mature codebase make it well-suited for containerized environments.

**Complexity Level:** Medium to High
**Deployment Time:** 2-4 hours for basic setup
**Maintenance:** Regular updates recommended
**Community Support:** Excellent (active forum and GitHub)

This system is ready for CT installation with proper planning and resource allocation.

---

*Analysis generated: 2025-12-17*
*Repository: /home/user/betaerpnext*
*Branch: claude/review-ct-installation-loT79*
