# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Criterion, Order
from frappe.query_builder.functions import Count, IfNull, Max
from frappe.utils import formatdate

ORDER_DOCTYPES = {"Customer": "Sales Order", "Supplier": "Purchase Order"}


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
			frappe.throw(
				_("This item filter has already been applied for the {0}").format(_(self.party_type))
			)


def get_allowed_items_condition(party_type, party):
	rules = get_party_rules(party_type, party, ignore_permissions=True)
	return get_rules_condition(rules) if rules else None


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


@frappe.whitelist()
def get_frequently_ordered_items(party_type: str, party: str):
	order_doctype = validate_party(party_type, party)
	frappe.has_permission(order_doctype, throw=True)

	history = get_order_history(party_type, party, limit=5)
	items = {
		item.name: item
		for item in frappe.get_list(
			"Item",
			filters={"name": ("in", [row.item_code for row in history] or [""])},
			fields=["name", "item_name", "disabled"],
		)
	}
	return [{**row, **items[row.item_code]} for row in history if row.item_code in items]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def party_item_query(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict):
	party_type, party = filters.get("party_type"), filters.get("party")
	validate_party(party_type, party)

	or_filters = (
		[["Item", "name", "like", f"%{txt}%"], ["Item", "item_name", "like", f"%{txt}%"]] if txt else None
	)
	items = get_items_ranked_by_orders(
		party_type,
		party,
		filters=[["Item", "disabled", "=", 0]],
		or_filters=or_filters,
		fields=["name", "item_name"],
		start=start,
		page_length=page_len,
	)
	return [(item.name, item.item_name, get_order_hint(party_type, item)) for item in items]


@frappe.whitelist()
def get_party_specific_items(party_type: str, party: str):
	validate_party(party_type, party)
	rules = get_party_rules(party_type, party)

	can_read_items = frappe.has_permission("Item")
	item_names = {}
	if can_read_items:
		item_names = dict(
			frappe.get_list(
				"Item",
				filters={
					"name": ("in", [r.based_on_value for r in rules if r.restrict_based_on == "Item"] or [""])
				},
				fields=["name", "item_name"],
				as_list=True,
			)
		)
	counts = count_rule_items(rules) if can_read_items else {}
	for rule in rules:
		if rule.restrict_based_on == "Item":
			rule.item_name = item_names.get(rule.based_on_value)
			rule.item_count = 1
		elif can_read_items:
			rule.item_count = counts.get((rule.restrict_based_on, rule.based_on_value), 0)

	rules.sort(
		key=lambda rule: (
			rule.party_type != party_type,
			rule.restrict_based_on == "Item",
			(rule.item_name or rule.based_on_value).lower(),
		)
	)
	for rule in rules:
		if rule.party_type == party_type:
			rule.pop("party_type")
			rule.pop("party")
	return rules


def get_party_rules(party_type, party, ignore_permissions=False):
	group_type = f"{party_type} Group"
	party_group = frappe.db.get_value(party_type, party, frappe.scrub(group_type))
	# a group rule applies to the party's group and every group above it in the tree
	party_groups = get_group_ancestors(group_type, party_group) if party_group else []
	rules = frappe.get_list(
		"Party Specific Item",
		filters={"party_type": ("in", [party_type, group_type])},
		or_filters=[["party", "=", party], ["party", "in", party_groups or [""]]],
		fields=["name", "party_type", "party", "restrict_based_on", "based_on_value"],
		ignore_permissions=ignore_permissions,
	)
	return [
		rule
		for rule in rules
		if (rule.party == party if rule.party_type == party_type else rule.party in party_groups)
	]


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


def validate_party(party_type, party):
	if party_type not in ORDER_DOCTYPES or not party:
		frappe.throw(_("A customer or supplier is required"), title=_("Missing Party"))
	frappe.has_permission(party_type, doc=party, throw=True)
	return ORDER_DOCTYPES[party_type]


def get_items_ranked_by_orders(party_type, party, filters, or_filters, fields, start, page_length):
	history = {}
	if frappe.has_permission(ORDER_DOCTYPES[party_type], "read"):
		history = {row.item_code: row for row in get_order_history(party_type, party)}

	rank = {item_code: idx for idx, item_code in enumerate(history)}
	ordered = frappe.get_list(
		"Item",
		filters=[*filters, ["Item", "name", "in", list(history) or [""]]],
		or_filters=or_filters,
		fields=fields,
	)
	ordered.sort(key=lambda item: rank[item.name])
	page = ordered[start : start + page_length]

	if len(page) < page_length:
		not_ordered = [*filters, ["Item", "name", "not in", list(history)]] if history else filters
		page += frappe.get_list(
			"Item",
			filters=not_ordered,
			or_filters=or_filters,
			fields=fields,
			order_by="`tabItem`.item_name asc",
			start=max(start - len(ordered), 0),
			limit=page_length - len(page),
		)

	for item in page:
		row = history.get(item.name)
		item.order_count = row.order_count if row else 0
		item.last_ordered = row.last_ordered if row else None
	return page


def get_order_history(party_type, party, limit=None):
	order_doctype = ORDER_DOCTYPES[party_type]
	party_field = frappe.scrub(party_type)
	permitted_orders = frappe.qb.get_query(
		order_doctype,
		fields=["name"],
		filters={party_field: party, "docstatus": 1},
		ignore_permissions=False,
	)
	permitted_items = frappe.qb.get_query("Item", fields=["name"], ignore_permissions=False)
	order = frappe.qb.DocType(order_doctype)
	order_item = frappe.qb.DocType(f"{order_doctype} Item")
	order_count = Count(order.name).distinct()
	last_ordered = Max(order.transaction_date)
	query = (
		frappe.qb.from_(order_item)
		.join(order)
		.on(order.name == order_item.parent)
		.select(order_item.item_code, order_count.as_("order_count"), last_ordered.as_("last_ordered"))
		.where(
			(order[party_field] == party)
			& order.name.isin(permitted_orders)
			& order_item.item_code.isin(permitted_items)
		)
		.groupby(order_item.item_code)
		.orderby(order_count, order=Order.desc)
		.orderby(last_ordered, order=Order.desc)
		.orderby(order_item.item_code)
	)
	if limit:
		query = query.limit(limit)
	return query.run(as_dict=True)


def get_order_hint(party_type, item):
	if party_type == "Supplier":
		if not item.order_count:
			return _("Not bought from this supplier yet")
		if item.order_count == 1:
			return _("Bought once, on {0}").format(formatdate(item.last_ordered))
		return _("Bought {0} times, last on {1}").format(item.order_count, formatdate(item.last_ordered))

	if not item.order_count:
		return _("Not ordered by this customer yet")
	if item.order_count == 1:
		return _("Ordered once, on {0}").format(formatdate(item.last_ordered))
	return _("Ordered {0} times, last on {1}").format(item.order_count, formatdate(item.last_ordered))


def count_rule_items(rules):
	item = frappe.qb.DocType("Item")
	permitted_items = frappe.qb.get_query(
		"Item", fields=["name"], filters={"disabled": 0}, ignore_permissions=False
	)
	brands = [rule.based_on_value for rule in rules if rule.restrict_based_on == "Brand"]
	groups = [rule.based_on_value for rule in rules if rule.restrict_based_on == "Item Group"]
	counts = {}

	if brands:
		rows = (
			frappe.qb.from_(item)
			.select(item.brand, Count(item.name))
			.where(item.brand.isin(brands) & item.name.isin(permitted_items))
			.groupby(item.brand)
			.run()
		)
		counts.update({("Brand", brand): count for brand, count in rows})

	if groups:
		group = frappe.qb.DocType("Item Group")
		parent = frappe.qb.DocType("Item Group").as_("parent_group")
		rows = (
			frappe.qb.from_(item)
			.join(group)
			.on(item.item_group == group.name)
			.join(parent)
			.on((group.lft >= parent.lft) & (group.rgt <= parent.rgt))
			.select(parent.name, Count(item.name))
			.where(parent.name.isin(groups) & item.name.isin(permitted_items))
			.groupby(parent.name)
			.run()
		)
		counts.update({("Item Group", name): count for name, count in rows})

	return counts
