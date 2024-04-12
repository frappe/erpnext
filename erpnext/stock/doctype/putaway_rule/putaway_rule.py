# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import copy
import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, floor, flt, nowdate

from erpnext.stock.utils import get_stock_balance


class PutawayRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		capacity: DF.Float
		company: DF.Link
		conversion_factor: DF.Float
		disable: DF.Check
		item_code: DF.Link
		item_name: DF.Data | None
		priority: DF.Int
		stock_capacity: DF.Float
		stock_uom: DF.Link | None
		uom: DF.Link | None
		warehouse: DF.Link
	# end: auto-generated types

	def validate(self):
		self.validate_duplicate_rule()
		self.validate_warehouse_and_company()
		self.validate_capacity()
		self.validate_priority()
		self.set_stock_capacity()

	def validate_duplicate_rule(self):
		existing_rule = frappe.db.exists(
			"Putaway Rule", {"item_code": self.item_code, "warehouse": self.warehouse}
		)
		if existing_rule and existing_rule != self.name:
			frappe.throw(
				_("Putaway Rule already exists for Item {0} in Warehouse {1}.").format(
					frappe.bold(self.item_code), frappe.bold(self.warehouse)
				),
				title=_("Duplicate"),
			)

	def validate_priority(self):
		if self.priority < 1:
			frappe.throw(_("Priority cannot be lesser than 1."), title=_("Invalid Priority"))

	def validate_warehouse_and_company(self):
		company = frappe.db.get_value("Warehouse", self.warehouse, "company")
		if company != self.company:
			frappe.throw(
				_("Warehouse {0} does not belong to Company {1}.").format(
					frappe.bold(self.warehouse), frappe.bold(self.company)
				),
				title=_("Invalid Warehouse"),
			)

	def validate_capacity(self):
		stock_uom = frappe.db.get_value("Item", self.item_code, "stock_uom")
		balance_qty = get_stock_balance(self.item_code, self.warehouse, nowdate())

		if flt(self.stock_capacity) < flt(balance_qty):
			frappe.throw(
				_(
					"Warehouse Capacity for Item '{0}' must be greater than the existing stock level of {1} {2}."
				).format(self.item_code, frappe.bold(balance_qty), stock_uom),
				title=_("Insufficient Capacity"),
			)

		if not self.capacity:
			frappe.throw(_("Capacity must be greater than 0"), title=_("Invalid"))

	def set_stock_capacity(self):
		self.stock_capacity = (flt(self.conversion_factor) or 1) * flt(self.capacity)


@frappe.whitelist()
def get_available_putaway_capacity(rule):
	stock_capacity, item_code, warehouse = frappe.db.get_value(
		"Putaway Rule", rule, ["stock_capacity", "item_code", "warehouse"]
	)
	balance_qty = get_stock_balance(item_code, warehouse, nowdate())
	free_space = flt(stock_capacity) - flt(balance_qty)
	return free_space if free_space > 0 else 0


@frappe.whitelist()
def apply_putaway_rule(doctype, items, company, sync=None, purpose=None):
	"""Applies Putaway Rule on line items.

	items: List of Purchase Receipt/Stock Entry Items
	company: Company in the Purchase Receipt/Stock Entry
	doctype: Doctype to apply rule on
	purpose: Purpose of Stock Entry
	sync (optional): Sync with client side only for client side calls
	"""
	if isinstance(items, str):
		items = json.loads(items)

	items_not_accomodated, updated_table = [], []
	item_wise_rules = defaultdict(list)

	for item in items:
		if isinstance(item, dict):
			item = frappe._dict(item)

		source_warehouse = item.get("s_warehouse")
		item.conversion_factor = flt(item.conversion_factor) or 1.0
		pending_qty, item_code = flt(item.qty), item.item_code
		pending_stock_qty = flt(item.transfer_qty) if doctype == "Stock Entry" else flt(item.stock_qty)
		uom_must_be_whole_number = frappe.db.get_value("UOM", item.uom, "must_be_whole_number")

		if not pending_qty or not item_code:
			updated_table = add_row(item, pending_qty, source_warehouse or item.warehouse, updated_table)
			continue

		at_capacity, rules = get_ordered_putaway_rules(item_code, company, source_warehouse=source_warehouse)

		if not rules:
			warehouse = source_warehouse or item.get("warehouse")
			if at_capacity:
				# rules available, but no free space
				items_not_accomodated.append([item_code, pending_qty])
			else:
				updated_table = add_row(item, pending_qty, warehouse, updated_table)
			continue

		# maintain item/item-warehouse wise rules, to handle if item is entered twice
		# in the table, due to different price, etc.
		key = item_code
		if doctype == "Stock Entry" and purpose == "Material Transfer" and source_warehouse:
			key = (item_code, source_warehouse)

		if not item_wise_rules[key]:
			item_wise_rules[key] = rules

		for rule in item_wise_rules[key]:
			if pending_stock_qty > 0 and rule.free_space:
				stock_qty_to_allocate = (
					flt(rule.free_space) if pending_stock_qty >= flt(rule.free_space) else pending_stock_qty
				)
				qty_to_allocate = stock_qty_to_allocate / item.conversion_factor

				if uom_must_be_whole_number:
					qty_to_allocate = floor(qty_to_allocate)
					stock_qty_to_allocate = qty_to_allocate * item.conversion_factor

				if not qty_to_allocate:
					break

				updated_table = add_row(item, qty_to_allocate, rule.warehouse, updated_table, rule.name)

				pending_stock_qty -= stock_qty_to_allocate
				pending_qty -= qty_to_allocate
				rule["free_space"] -= stock_qty_to_allocate

				if pending_stock_qty <= 0:
					break

		# if pending qty after applying all rules, add row without warehouse
		if pending_stock_qty > 0:
			items_not_accomodated.append([item.item_code, pending_qty])

	if items_not_accomodated:
		show_unassigned_items_message(items_not_accomodated)

	if updated_table and _items_changed(items, updated_table, doctype):
		items[:] = updated_table
		frappe.msgprint(_("Applied putaway rules."), alert=True)

	if sync and json.loads(sync):  # sync with client side
		return items


def _items_changed(old, new, doctype: str) -> bool:
	"""Check if any items changed by application of putaway rules.

	If not, changing item table can have side effects since `name` items also changes.
	"""
	if len(old) != len(new):
		return True

	old = [frappe._dict(item) if isinstance(item, dict) else item for item in old]

	if doctype == "Stock Entry":
		compare_keys = ("item_code", "t_warehouse", "transfer_qty", "serial_no")
		sort_key = lambda item: (  # noqa
			item.item_code,
			cstr(item.t_warehouse),
			flt(item.transfer_qty),
			cstr(item.serial_no),
		)
	else:
		# purchase receipt / invoice
		compare_keys = ("item_code", "warehouse", "stock_qty", "received_qty", "serial_no")
		sort_key = lambda item: (  # noqa
			item.item_code,
			cstr(item.warehouse),
			flt(item.stock_qty),
			flt(item.received_qty),
			cstr(item.serial_no),
		)

	old_sorted = sorted(old, key=sort_key)
	new_sorted = sorted(new, key=sort_key)

	# Once sorted by all relevant keys both tables should align if they are same.
	for old_item, new_item in zip(old_sorted, new_sorted, strict=False):
		for key in compare_keys:
			if old_item.get(key) != new_item.get(key):
				return True
	return False


def get_ordered_putaway_rules(item_code, company, source_warehouse=None):
	"""Returns an ordered list of putaway rules to apply on an item."""
	filters = {"item_code": item_code, "company": company, "disable": 0}
	if source_warehouse:
		filters.update({"warehouse": ["!=", source_warehouse]})

	rules = frappe.get_all(
		"Putaway Rule",
		fields=["name", "item_code", "stock_capacity", "priority", "warehouse"],
		filters=filters,
		order_by="priority asc, capacity desc",
	)

	if not rules:
		return False, None

	vacant_rules = []
	for rule in rules:
		balance_qty = get_stock_balance(rule.item_code, rule.warehouse, nowdate())
		free_space = flt(rule.stock_capacity) - flt(balance_qty)
		if free_space > 0:
			rule["free_space"] = free_space
			vacant_rules.append(rule)

	if not vacant_rules:
		# After iterating through rules, if no rules are left
		# then there is not enough space left in any rule
		return True, None

	vacant_rules = sorted(vacant_rules, key=lambda i: (i["priority"], -i["free_space"]))

	return False, vacant_rules


def add_row(item, to_allocate, warehouse, updated_table, rule=None):
	new_updated_table_row = copy.deepcopy(item)
	new_updated_table_row.idx = 1 if not updated_table else cint(updated_table[-1].idx) + 1
	new_updated_table_row.name = None
	new_updated_table_row.qty = to_allocate

	if item.doctype == "Stock Entry Detail":
		new_updated_table_row.t_warehouse = warehouse
		new_updated_table_row.transfer_qty = flt(to_allocate) * flt(new_updated_table_row.conversion_factor)
	else:
		new_updated_table_row.stock_qty = flt(to_allocate) * flt(new_updated_table_row.conversion_factor)
		new_updated_table_row.warehouse = warehouse
		new_updated_table_row.rejected_qty = 0
		new_updated_table_row.received_qty = to_allocate

	if rule:
		new_updated_table_row.putaway_rule = rule

	new_updated_table_row.serial_and_batch_bundle = ""

	updated_table.append(new_updated_table_row)
	return updated_table


def show_unassigned_items_message(items_not_accomodated):
	msg = _("The following Items, having Putaway Rules, could not be accomodated:") + "<br><br>"
	formatted_item_rows = ""

	for entry in items_not_accomodated:
		item_link = frappe.utils.get_link_to_form("Item", entry[0])
		formatted_item_rows += f"""
			<td>{item_link}</td>
			<td>{frappe.bold(entry[1])}</td>
		</tr>"""

	msg += """
		<table class="table">
			<thead>
				<td>{}</td>
				<td>{}</td>
			</thead>
			{}
		</table>
	""".format(_("Item"), _("Unassigned Qty"), formatted_item_rows)

	frappe.msgprint(msg, title=_("Insufficient Capacity"), is_minimizable=True, wide=True)
