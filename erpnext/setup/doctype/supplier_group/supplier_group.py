# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.utils.nestedset import NestedSet, get_root_of


class SupplierGroup(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.party_account.party_account import PartyAccount

		accounts: DF.Table[PartyAccount]
		is_group: DF.Check
		lft: DF.Int
		old_parent: DF.Link | None
		parent_supplier_group: DF.Link | None
		payment_terms: DF.Link | None
		rgt: DF.Int
		supplier_group_name: DF.Data
	# end: auto-generated types
	nsm_parent_field = "parent_supplier_group"

	def validate(self):
		if not self.parent_supplier_group:
			self.parent_supplier_group = get_root_of("Supplier Group")

	def on_update(self):
		NestedSet.on_update(self)
		self.validate_one_root()

	def on_trash(self):
		NestedSet.validate_if_child_exists(self)
		frappe.utils.nestedset.update_nsm(self)
