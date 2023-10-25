# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.model.document import Document
from frappe.utils import cint

from erpnext.stock.utils import check_pending_reposting


class AccountsSettings(Document):
	def validate(self):
		old_doc = self.get_doc_before_save()
		clear_cache = False

		if old_doc.add_taxes_from_item_tax_template != self.add_taxes_from_item_tax_template:
			frappe.db.set_default(
				"add_taxes_from_item_tax_template", self.get("add_taxes_from_item_tax_template", 0)
			)
			clear_cache = True

		if old_doc.enable_common_party_accounting != self.enable_common_party_accounting:
			frappe.db.set_default(
				"enable_common_party_accounting", self.get("enable_common_party_accounting", 0)
			)
			clear_cache = True

		self.validate_stale_days()

		if old_doc.show_payment_schedule_in_print != self.show_payment_schedule_in_print:
			self.enable_payment_schedule_in_print()

		if old_doc.acc_frozen_upto != self.acc_frozen_upto:
			self.validate_pending_reposts()

		if clear_cache:
			frappe.clear_cache()

	def validate_stale_days(self):
		if not self.allow_stale and cint(self.stale_days) <= 0:
			frappe.msgprint(
				_("Stale Days should start from 1."), title="Error", indicator="red", raise_exception=1
			)

	def enable_payment_schedule_in_print(self):
		show_in_print = cint(self.show_payment_schedule_in_print)
		for doctype in ("Sales Order", "Sales Invoice", "Purchase Order", "Purchase Invoice"):
			make_property_setter(
				doctype, "due_date", "print_hide", show_in_print, "Check", validate_fields_for_doctype=False
			)
			make_property_setter(
				doctype,
				"payment_schedule",
				"print_hide",
				0 if show_in_print else 1,
				"Check",
				validate_fields_for_doctype=False,
			)

	def validate_pending_reposts(self):
		if self.acc_frozen_upto:
			check_pending_reposting(self.acc_frozen_upto)
