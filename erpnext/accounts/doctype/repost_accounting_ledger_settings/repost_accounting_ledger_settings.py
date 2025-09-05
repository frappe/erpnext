# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger import get_child_docs


class RepostAccountingLedgerSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.repost_allowed_types.repost_allowed_types import RepostAllowedTypes

		allowed_types: DF.Table[RepostAllowedTypes]

	# end: auto-generated types
	def validate(self):
		self.update_property_for_accounting_dimension()

	def update_property_for_accounting_dimension(self):
		doctypes = [entry.document_type for entry in self.allowed_types if entry.allowed]
		if not doctypes:
			return
		doctypes += get_child_docs(doctypes)

		set_allow_on_submit_for_dimension_fields(doctypes)


def set_allow_on_submit_for_dimension_fields(doctypes):
	for dt in doctypes:
		meta = frappe.get_meta(dt)
		for dimension in get_accounting_dimensions():
			df = meta.get_field(dimension)
			if df and not df.allow_on_submit:
				frappe.db.set_value("Custom Field", dt + "-" + dimension, "allow_on_submit", 1)
