# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe.model.document import Document


class AccountsSettings(Document):
	def on_update(self):
		pass

	def validate(self):
		self.validate_stale_days()

	def validate_stale_days(self):
		if not self.allow_stale and cint(self.stale_days) <= 0:
			frappe.msgprint(
				"Stale Days should start from 1.", title='Error', indicator='red',
				raise_exception=1)

