# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PartySpecificItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		based_on_value: DF.DynamicLink
		inclusion_type: DF.Literal["Inclusive", "Exclusive"]
		party: DF.DynamicLink
		party_type: DF.Literal["Customer", "Customer Group", "Supplier", "Supplier Group"]
		restrict_based_on: DF.Literal["Item", "Item Group", "Brand"]
	# end: auto-generated types

	def validate(self):
		party_type = [self.party_type]
		party = [self.party]

		if self.party_type in ["Customer", "Supplier"]:
			if party_group := frappe.get_value(
				self.party_type, self.party, f"{self.party_type.lower()}_group"
			):
				party.append(party_group)
				party_type.append(f"{self.party_type} Group")

		exists = frappe.db.exists(
			"Party Specific Item",
			{
				"party_type": ["in", party_type],
				"party": ["in", party],
				"restrict_based_on": self.restrict_based_on,
				"based_on_value": self.based_on_value,
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(
				_("This item filter has already been applied in {0}").format(
					frappe.utils.get_link_to_form("Party Specific Item", exists)
				)
			)
