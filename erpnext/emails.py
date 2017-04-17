# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

def get_welcome_email():
	return {
		"subject": _("Welcome to ERPNext"),
		"template": "templates/emails/new_user.html"
	}