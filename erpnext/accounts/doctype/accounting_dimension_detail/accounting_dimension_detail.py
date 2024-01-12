# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class AccountingDimensionDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		automatically_post_balancing_accounting_entry: DF.Check
		company: DF.Link | None
		default_dimension: DF.DynamicLink | None
		mandatory_for_bs: DF.Check
		mandatory_for_pl: DF.Check
		offsetting_account: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reference_document: DF.Link | None
	# end: auto-generated types

	pass
