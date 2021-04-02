# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.setup.install import default_mail_footer

def execute():
	return
	mail_footer = frappe.db.get_default('mail_footer') or ''
	mail_footer += default_mail_footer
	frappe.db.set_value("Outgoing Email Settings", "Outgoing Email Settings", "footer", mail_footer)
