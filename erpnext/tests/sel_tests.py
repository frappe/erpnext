# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""
Run Selenium Tests

Requires a clean install. After reinstalling fresh db, call

	frappe --execute erpnext.tests.sel_tests.start

"""

from __future__ import unicode_literals
import frappe

from frappe.utils import sel

def start():
	sel.start(verbose=True)
	sel.login("#page-setup-wizard")


# complete setup
# new customer
# new supplier
# new item
# sales cycle
# purchase cycle
