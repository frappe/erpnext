# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import copy
import json
from collections import defaultdict
from six import string_types
from frappe import _
from frappe.utils import flt, floor, nowdate, cint
from frappe.model.document import Document
from erpnext.stock.utils import get_stock_balance
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

class PutawayRule(Document):
	def validate(self):
		self.validate_duplicate_rule()
		self.validate_warehouse_and_company()
		self.validate_capacity()
		self.validate_priority()
		self.set_stock_capacity()

	def validate_duplicate_rule(self):
		existing_rule = frappe.db.exists("Putaway Rule", {"item_code": self.item_code, "warehouse": self.warehouse})
		if existing_rule and existing_rule != self.name:
			frappe.throw(_("Putaway Rule already exists for Item {0} in Warehouse {1}.")
				.format(frappe.bold(self.item_code), frappe.bold(self.warehouse)),
				title=_("Duplicate"))

	def validate_priority(self):
		if self.priority < 1:
			frappe.throw(_("Priority cannot be lesser than 1."), title=_("Invalid Priority"))

	def validate_warehouse_and_company(self):
		company = frappe.db.get_value("Warehouse", self.warehouse, "company")
		if company != self.company:
			frappe.throw(_("Warehouse {0} does not belong to Company {1}.")
				.format(frappe.bold(self.warehouse), frappe.bold(self.company)),
				title=_("Invalid Warehouse"))

	def validate_capacity(self):
		stock_uom = frappe.db.get_value("Item", self.item_code, "stock_uom")
		balance_qty = get_stock_balance(self.item_code, self.warehouse, nowdate())

		if flt(self.stock_capacity) < flt(balance_qty):
			frappe.throw(_("Warehouse Capacity for Item '{0}' must be greater than the existing stock level of {1} {2}.")
				.format(self.item_code, frappe.bold(balance_qty), stock_uom),
				title=_("Insufficient Capacity"))

		if not self.capacity:
			frappe.throw(_("Capacity must be greater than 0"), title=_("Invalid"))

	def set_stock_capacity(self):
		self.stock_capacity = (flt(self.conversion_factor) or 1) * flt(self.capacity)

@frappe.whitelist()
def get_available_putaway_capacity(rule):
	stock_capacity, item_code, warehouse = frappe.db.get_value("Putaway Rule", rule,
		["stock_capacity", "item_code", "warehouse"])
	balance_qty = get_stock_balance(item_code, warehouse, nowdate())
	free_space = flt(stock_capacity) - flt(balance_qty)
	return free_space if free_space > 0 else 0

@frappe.whitelist()
def apply_putaway_rule(doctype, items, company, sync=None, purpose=None):
	""" Applies Putaway Rule on line items.

		items: List of Purchase Receipt/Stock Entry Items
		company: Company in the Purchase Receipt/Stock Entry
		doctype: Doctype to apply rule on
		purpose: Purpose of Stock Entry
		sync (optional): Sync with client side only for client side calls
	"""
	if isinstance(items, string_types):
		items = json.loads(items)

	items_not_accomodated, updated_table = [], []
	item_wise_rules = defaultdict(list)

	for item in items:
		if isinstance(item, dict):
			item = frappe._dict(item)

		source_warehouse = item.get("s_warehouse")
		serial_nos = get_serial_nos(item.get("serial_no"))
		item.conversion_factor = flt(item.conversion_factor) or 1.0
		pending_qty, item_code = flt(item.qty), item.item_code
		pending_stock_qty = flt(item.transfer_qty) if doctype == "Stock Entry" else flt(item.stock_qty)
		uom_must_be_whole_number = frappe.db.get_value('UOM', item.uom, 'must_be_whole_number')

		if not pending_qty or not item_code:
			updated_table = add_row(item, pending_qty, source_warehouse or item.warehouse, updated_table)
			continue

		at_capacity, rules = get_ordered_putaway_rules(item_code, company, source_warehouse=source_warehouse)

		if not rules:
			warehouse = source_warehouse or item.warehouse
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
				stock_qty_to_allocate = flt(rule.free_space) if pending_stock_qty >= flt(rule.free_space) else pending_stock_qty
				qty_to_allocate = stock_qty_to_allocate / item.conversion_factor

				if uom_must_be_whole_number:
					qty_to_allocate = floor(qty_to_allocate)
					stock_qty_to_allocate = qty_to_allocate * item.conversion_factor

				if not qty_to_allocate: break

				updated_table = add_row(item, qty_to_allocate, rule.warehouse, updated_table,
					rule.name, serial_nos=serial_nos)

				pending_stock_qty -= stock_qty_to_allocate
				pending_qty -= qty_to_allocate
				rule["free_space"] -= stock_qty_to_allocate

				if not pending_stock_qty > 0: break

		# if pending qty after applying all rules, add row without warehouse
		if pending_stock_qty > 0:
			items_not_accomodated.append([item.item_code, pending_qty])

	if items_not_accomodated:
		show_unassigned_items_message(items_not_accomodated)

	items[:] = updated_table if updated_table else items # modify items table

	if sync and json.loads(sync): # sync with client side
		return items

def get_ordered_putaway_rules(item_code, company, source_warehouse=None):
	"""Returns an ordered list of putaway rules to apply on an item."""
	filters = {
		"item_code": item_code,
		"company": company,
		"disable": 0
	}
	if source_warehouse:
		filters.update({"warehouse": ["!=", source_warehouse]})

	rules = frappe.get_all("Putaway Rule",
		fields=["name", "item_code", "stock_capacity", "priority", "warehouse"],
		filters=filters,
		order_by="priority asc, capacity desc")

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

	vacant_rules = sorted(vacant_rules, key = lambda i: (i['priority'], -i['free_space']))

	return False, vacant_rules

def add_row(item, to_allocate, warehouse, updated_table, rule=None, serial_nos=None):
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
	if serial_nos:
		new_updated_table_row.serial_no = get_serial_nos_to_allocate(serial_nos, to_allocate)

	updated_table.append(new_updated_table_row)
	return updated_table

def show_unassigned_items_message(items_not_accomodated):
	msg = _("The following Items, having Putaway Rules, could not be accomodated:") + "<br><br>"
	formatted_item_rows = ""

	for entry in items_not_accomodated:
		item_link = frappe.utils.get_link_to_form("Item", entry[0])
		formatted_item_rows += """
			<td>{0}</td>
			<td>{1}</td>
		</tr>""".format(item_link, frappe.bold(entry[1]))

	msg += """
		<table class="table">
			<thead>
				<td>{0}</td>
				<td>{1}</td>
			</thead>
			{2}
		</table>
	""".format(_("Item"), _("Unassigned Qty"), formatted_item_rows)

	frappe.msgprint(msg, title=_("Insufficient Capacity"), is_minimizable=True, wide=True)

def get_serial_nos_to_allocate(serial_nos, to_allocate):
	if serial_nos:
		allocated_serial_nos = serial_nos[0: cint(to_allocate)]
		serial_nos[:] = serial_nos[cint(to_allocate):] # pop out allocated serial nos and modify list
		return "\n".join(allocated_serial_nos) if allocated_serial_nos else ""
	else: return ""