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
				"name": ("!=", self.name),
			},
		)
		if exists:
			frappe.throw(_("This item filter has already been applied for the {0}").format(self.party_type))


def get_allowed_items_condition(party_type, party):
	group_type = f"{party_type} Group"
	party_group = frappe.db.get_value(party_type, party, frappe.scrub(group_type))
	rules = frappe.get_all(
		"Party Specific Item",
		filters={"party_type": party_type, "party": party},
		fields=["restrict_based_on", "based_on_value"],
	)
	# a group rule applies to the party's group and every group above it in the tree
	party_groups = get_group_ancestors(group_type, party_group) if party_group else []
	if party_groups:
		rules += frappe.get_all(
			"Party Specific Item",
			filters={"party_type": group_type, "party": ("in", party_groups)},
			fields=["restrict_based_on", "based_on_value"],
		)
	return get_rules_condition(rules) if rules else None


def get_group_ancestors(group_type, group):
	"""Return the group and all its ancestor groups (nested set)."""
	node = frappe.qb.DocType(group_type)
	ancestor = frappe.qb.DocType(group_type).as_("ancestor")
	return (
		frappe.qb.from_(node)
		.join(ancestor)
		.on((node.lft >= ancestor.lft) & (node.rgt <= ancestor.rgt))
		.select(ancestor.name)
		.where(node.name == group)
		.run(pluck=True)
	)


def get_rules_condition(rules):
	"""Return a condition matching items covered by any of the rules."""
	item = frappe.qb.DocType("Item")
	values = defaultdict(list)
	for rule in rules:
		values[rule.restrict_based_on].append(rule.based_on_value)

	conditions = []
	if values["Item"]:
		conditions.append(item.name.isin(values["Item"]) | IfNull(item.variant_of, "").isin(values["Item"]))
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
