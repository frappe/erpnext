# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe.model.document import Document
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


class AccountsSettings(Document):
	def on_update(self):
		frappe.clear_cache()

	def validate(self):
		self.validate_stale_days()
		self.enable_payment_schedule_in_print()
		self.enable_fields_for_cost_center_settings()

	def validate_stale_days(self):
		if not self.allow_stale and cint(self.stale_days) <= 0:
			frappe.msgprint(
				"Stale Days should start from 1.", title='Error', indicator='red',
				raise_exception=1)

	def enable_payment_schedule_in_print(self):
		show_in_print = cint(self.show_payment_schedule_in_print)
		for doctype in ("Sales Order", "Sales Invoice", "Purchase Order", "Purchase Invoice"):
			make_property_setter(doctype, "due_date", "print_hide", show_in_print, "Check")
			make_property_setter(doctype, "payment_schedule", "print_hide",  0 if show_in_print else 1, "Check")

	def enable_fields_for_cost_center_settings(self):
		show_field = 0 if cint(self.allow_cost_center_in_entry_of_bs_account) else 1
		for doctype in ("Sales Invoice", "Purchase Invoice", "Payment Entry"):
			make_property_setter(doctype, "cost_center", "hidden", show_field, "Check")
