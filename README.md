# ERPNext - Open Source + SAAS ERP

Version 2.0

Includes Accounting, Inventory, CRM, Sales, Purchase, Projects, HRMS

Built on Python / MySQL / wnframework

- [Download](http://erpnext.org)
- [Use now as SAAS @ $7/user/month](https://erpnext.com)

## Platform

ERPNext is built on [wnframework](https://github.com/webnotes/wnframework) (Version 2.0)

## Download and Install

For download and install details, please go to [erpnext.org](http://erpnext.org)

## Forums

- [User / Functional](http://groups.google.com/group/erpnext-user-forum)
- [Technical](http://groups.google.com/group/wnframework)

## Changes from wnframework version 1.7

To update from wnframework version 1.

1. set your html folder to the root of erpnext (rather than wnframework)
2. create a symlink in erpnext:

    ln -s path/to/wnframework lib

3. to setup the versions db, run:

    python lib/wnf.py setup

4. copy defs.py from cgi-bin/webnotes to py/webnotes
5. change module_path (point to erpnext/erpnext) in defs.py
6. delete cgi-bin directory
7. delete all old module directories from erpnext

## License

ERPNext is available under the GNU/GPL license.

