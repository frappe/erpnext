# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from erpnext.setup.setup_wizard.test_setup_data import args
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
import frappe.utils.scheduler

if __name__=="__main__":
	frappe.connect()
	frappe.local.form_dict = frappe._dict(args)
	setup_complete()
	frappe.utils.scheduler.disable_scheduler()
