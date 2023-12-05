# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


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

	def on_trash(self):
		delete_contact_and_address("Shareholder", self.name)

	def before_save(self):
		for entry in self.share_balance:
			entry.amount = entry.no_of_shares * entry.rate
