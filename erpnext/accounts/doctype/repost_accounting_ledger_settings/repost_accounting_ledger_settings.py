# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class RepostAccountingLedgerSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.repost_allowed_types.repost_allowed_types import RepostAllowedTypes

		allowed_types: DF.Table[RepostAllowedTypes]
	# end: auto-generated types

	pass
