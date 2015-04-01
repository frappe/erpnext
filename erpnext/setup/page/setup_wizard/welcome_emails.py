# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import add_days, nowdate, get_fullname
import markdown2

def setup_welcome_emails():
	for email in (
		{"fname": "email-1.md", "subject": "Setting up ERPNext", "after": 1},
		{"fname": "email-2.md", "subject": "Getting ERPNext Help", "after": 3},
	):
		content = frappe.get_template("setup/page/setup_wizard/emails/" \
			+ email["fname"]).render({"fullname": get_fullname()})

		frappe.sendmail(recipients = frappe.session.user, subject = email["subject"],
			sender = "hello@erpnext.com",
			content=markdown2.markdown(content), as_bulk = True,
			send_after= add_days(nowdate(), email["after"]))
