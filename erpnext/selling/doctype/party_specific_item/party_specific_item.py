# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

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
		party: DF.DynamicLink
		party_type: DF.Literal["Customer", "Customer Group", "Supplier", "Supplier Group"]
		restrict_based_on: DF.Literal["Item", "Item Group", "Brand"]
	# end: auto-generated types

	def validate(self):
		exists = frappe.db.exists(
			"Party Specific Item",
			{
				"party_type": self.party_type,
				"party": self.party,
				"restrict_based_on": self.restrict_based_on,
				"based_on_value": self.based_on_value,
			},
		)
		if exists:
			frappe.throw(
				_("This item filter has already been applied for the {0}").format(_(self.party_type))
			)


def get_party_item_restrictions(party_type, party):
	"""Return item values assigned to other parties and not allowed for this party."""
	group_type = f"{party_type} Group"
	rules = frappe.get_all(
		"Party Specific Item",
		filters={"party_type": ("in", [party_type, group_type])},
		fields=["party_type", "party", "restrict_based_on", "based_on_value"],
	)
	if not rules:
		return {}

	party_group = frappe.db.get_value(party_type, party, frappe.scrub(group_type))
	allowed_items = defaultdict(set)
	restricted_items = defaultdict(set)
	for rule in rules:
		field = "name" if rule.restrict_based_on == "Item" else frappe.scrub(rule.restrict_based_on)
		allowed_party = party if rule.party_type == party_type else party_group
		if rule.party == allowed_party:
			allowed_items[field].add(rule.based_on_value)
		else:
			restricted_items[field].add(rule.based_on_value)

	return {
		field: values - allowed_items[field]
		for field, values in restricted_items.items()
		if values - allowed_items[field]
	}
