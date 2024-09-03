# Loki: Goldfish ERP System

## Overview
Goldfish is an Enterprise Resource Planning (ERP) system, refactored from ERPNext. It provides a comprehensive suite of business management tools including inventory management, manufacturing, and reporting capabilities.

## Refactor Status
The project is currently undergoing a major refactor from ERPNext to Goldfish. This README outlines the current status and remaining tasks.

## Completed Tasks
- Renamed main application from 'erpnext' to 'goldfish'
- Updated import statements in core Python files
- Renamed configuration variables

## Remaining Tasks

### 1. Code Base Updates
- [ ] Review all Python files for any remaining 'erpnext' references
- [ ] Update any hardcoded strings referencing 'ERPNext' or 'erpnext'
- [ ] Refactor any Frappe-specific code that may need adjustment

### 2. Database
- [ ] Update database table names if they include 'erpnext'
- [ ] Modify any stored procedures or functions referencing 'erpnext'
- [ ] Update database connection strings in configuration files

### 3. Frontend
- [ ] Update all JavaScript/TypeScript files to use 'goldfish' instead of 'erpnext'
- [ ] Modify any Vue/React components that may reference 'erpnext'
- [ ] Update CSS class names and IDs that include 'erpnext'

### 4. API
- [ ] Review and update API endpoints
- [ ] Modify API documentation to reflect new 'Goldfish' naming

### 5. Configuration
- [ ] Update all configuration files (e.g., .ini, .conf, .json) to use 'Goldfish' settings
- [ ] Modify environment variables in deployment scripts

### 6. Documentation
- [ ] Update all documentation files (.md, .rst) to reflect 'Goldfish' naming
- [ ] Revise user manuals and guides

### 7. Testing
- [ ] Update test cases to use 'Goldfish' naming and imports
- [ ] Run comprehensive tests to ensure functionality is maintained post-refactor

### 8. Deployment
- [ ] Update Docker files and docker-compose configurations
- [ ] Modify CI/CD pipelines to reflect new naming conventions

### 9. Third-party Integrations
- [ ] Review and update any integrations that may be using 'erpnext' naming

### 10. Frappe Framework Considerations
- [ ] Review Frappe dependencies and update as necessary
- [ ] Modify any Frappe-specific configurations to align with 'Goldfish' naming
- [ ] Update Frappe hooks and overrides

## Getting Started
(Include instructions for setting up the development environment, running the application, and contributing to the project)

## Contributing
(Outline the process for contributing to the Goldfish project, including coding standards and pull request procedures)

## License
(Include license information)

## Support
(Provide information on how to get support or contact the maintainers)