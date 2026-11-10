# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.contacts.address_and_contact import (
	delete_contact_and_address,
	load_address_and_contact,
)
from frappe.model.document import Document


class Shareholder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.share_balance.share_balance import ShareBalance

		company: DF.Link
		contact_list: DF.Code | None
		folio_no: DF.Data | None
		is_company: DF.Check
		naming_series: DF.Literal["ACC-SH-.YYYY.-"]
		share_balance: DF.Table[ShareBalance]
		title: DF.Data
	# end: auto-generated types

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)

	def validate(self):
		if self.is_new():
			balance_changed = bool(self.share_balance)
		else:
			balance_changed = not self.is_child_table_same("share_balance")
			previous = self.get_doc_before_save()
			if (self.has_value_changed("company") or self.has_value_changed("is_company")) and (
				previous.share_balance or previous.has_submitted_share_transfers()
			):
				frappe.throw(
					_(
						"Cannot change the company or company shareholder status while shares or submitted share transfers exist"
					),
					title=_("Not Allowed"),
				)

		if balance_changed and not self.flags.from_share_transfer:
			frappe.throw(
				_("Share balances can only be changed through Share Transfer"), title=_("Not Allowed")
			)

	def on_trash(self):
		if self.share_balance or self.has_submitted_share_transfers():
			frappe.throw(
				_("Cannot delete a shareholder with shares or submitted share transfers"),
				title=_("Not Allowed"),
			)

		delete_contact_and_address("Shareholder", self.name)

	def before_save(self):
		for entry in self.share_balance:
			entry.amount = entry.no_of_shares * entry.rate

	def has_submitted_share_transfers(self):
		or_filters = {"from_shareholder": self.name, "to_shareholder": self.name}
		if self.is_company:
			or_filters["company"] = self.company

		return bool(
			frappe.get_all(
				"Share Transfer",
				filters={"docstatus": 1},
				or_filters=or_filters,
				pluck="name",
				limit_page_length=1,
			)
		)
