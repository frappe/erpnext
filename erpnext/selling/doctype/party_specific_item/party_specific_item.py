# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import IfNull


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
			frappe.throw(_("This item filter has already been applied for the {0}").format(self.party_type))


def get_restricted_items_condition(party_type, party):
	"""Return a condition matching items reserved for other parties and not for this party."""
	group_type = f"{party_type} Group"
	rules = frappe.get_all(
		"Party Specific Item",
		filters={"party_type": ("in", [party_type, group_type])},
		fields=["party_type", "party", "restrict_based_on", "based_on_value"],
	)
	if not rules:
		return None

	party_group = frappe.db.get_value(party_type, party, frappe.scrub(group_type))
	own_rules, other_rules = [], []
	for rule in rules:
		allowed_party = party if rule.party_type == party_type else party_group
		if rule.party == allowed_party:
			own_rules.append(rule)
		else:
			other_rules.append(rule)

	if not other_rules:
		return None
	if not own_rules:
		return get_rules_condition(other_rules)
	return get_rules_condition(other_rules) & ~get_rules_condition(own_rules)


def get_rules_condition(rules):
	"""Return a condition matching items covered by any of the rules."""
	item = frappe.qb.DocType("Item")
	values = defaultdict(list)
	for rule in rules:
		values[rule.restrict_based_on].append(rule.based_on_value)

	conditions = []
	if values["Item"]:
		conditions.append(item.name.isin(values["Item"]))
	if values["Item Group"]:
		conditions.append(item.item_group.isin(get_item_group_subtree_query(values["Item Group"])))
	if values["Brand"]:
		conditions.append(IfNull(item.brand, "").isin(values["Brand"]))
	return Criterion.any(conditions)


def get_item_group_subtree_query(item_groups):
	"""Return a query for the item groups and all their sub-groups."""
	group = frappe.qb.DocType("Item Group")
	parent = frappe.qb.DocType("Item Group").as_("parent_group")
	return (
		frappe.qb.from_(group)
		.join(parent)
		.on((group.lft >= parent.lft) & (group.rgt <= parent.rgt))
		.select(group.name)
		.where(parent.name.isin(item_groups))
	)
