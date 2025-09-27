# docs: Add development setup documentation and configuration to resolve import errors

## Description

This PR addresses the common issue where developers encounter "Import 'frappe' could not be resolved" errors when working with ERPNext code. The PR provides comprehensive documentation and configuration files to help developers set up their development environment correctly.

## Changes

### Added Documentation
- **DEVELOPMENT_SETUP.md**: Comprehensive guide explaining the root cause of import issues and providing solutions for different platforms (Unix/Linux, macOS, and Windows)
- **README-DEV.md**: Developer-focused README with quick start instructions and IDE configuration guidance

### Added Configuration Files
- **.vscode/settings.json**: VS Code configuration to help resolve import errors by setting the correct Python interpreter and paths
- **requirements-dev.txt**: Development requirements file listing dependencies needed for development work

## Root Cause of Import Issues

The "Import 'frappe' could not be resolved" error occurs because:
1. The `frappe` module is not a standard Python package
2. It's part of the Frappe Framework which needs to be installed separately
3. IDEs don't know where to find the module without proper configuration

## Solutions Provided

1. **Documentation**: Clear instructions for setting up development environments on different platforms
2. **IDE Configuration**: Pre-configured settings for VS Code to resolve import errors
3. **Development Dependencies**: Requirements file for installing necessary development tools
4. **Docker/WSL Recommendations**: Guidance for Windows users who may face platform-specific issues

## Testing

No functional code changes were made. The PR only adds documentation and configuration files that help developers set up their environments correctly.

## Benefits

- Reduces onboarding friction for new contributors
- Provides clear solutions for common development environment issues
- Improves developer experience by resolving import errors
- Offers platform-specific guidance for Windows, macOS, and Linux users

## Related Issues

This addresses common developer onboarding issues and helps reduce friction for new contributors to the ERPNext project.

 closes #XXXX