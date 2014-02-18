# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from erpnext.setup.page.setup_wizard.test_setup_data import args
from erpnext.setup.page.setup_wizard.setup_wizard import setup_account

if __name__=="__main__":
	frappe.connect()
	frappe.local.form_dict = frappe._dict(args)
	setup_account()
	