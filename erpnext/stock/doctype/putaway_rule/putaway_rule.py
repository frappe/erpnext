# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import copy
from collections import defaultdict
from frappe import _
from frappe.utils import flt, floor, nowdate
from frappe.model.document import Document
from erpnext.stock.utils import get_stock_balance

class PutawayRule(Document):
	def validate(self):
		self.validate_duplicate_rule()
		self.validate_warehouse_and_company()
		self.validate_capacity()
		self.validate_priority()

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
		balance_qty = get_stock_balance(self.item_code, self.warehouse, nowdate())
		if flt(self.stock_capacity) < flt(balance_qty):
			frappe.throw(_("Warehouse Capacity for Item '{0}' must be greater than the existing stock level of {1} qty.")
				.format(self.item_code, frappe.bold(balance_qty)), title=_("Insufficient Capacity"))

@frappe.whitelist()
def get_ordered_putaway_rules(item_code, company):
	"""Returns an ordered list of putaway rules to apply on an item."""
	rules = frappe.get_all("Putaway Rule", fields=["name", "stock_capacity", "priority", "warehouse"],
		filters={"item_code": item_code, "company": company, "disable": 0},
		order_by="priority asc, capacity desc")

	if not rules:
		return False, None

	for rule in rules:
		balance_qty = get_stock_balance(rule.item_code, rule.warehouse, nowdate())
		free_space = flt(rule.stock_capacity) - flt(balance_qty)
		if free_space > 0:
			rule["free_space"] = free_space
		else:
			del rule

	if not rules:
		# After iterating through rules, if no rules are left
		# then there is not enough space left in any rule
		return True, None

	rules = sorted(rules, key = lambda i: (i['priority'], -i['free_space']))
	return False, rules

@frappe.whitelist()
def apply_putaway_rule(items, company):
	""" Applies Putaway Rule on line items.

		items: List of Purchase Receipt Item objects
		company: Company in the Purchase Receipt
	"""
	items_not_accomodated, updated_table = [], []
	item_wise_rules = defaultdict(list)

	def add_row(item, to_allocate, warehouse):
		new_updated_table_row = copy.deepcopy(item)
		new_updated_table_row.name = ''
		new_updated_table_row.idx = 1 if not updated_table else flt(updated_table[-1].idx) + 1
		new_updated_table_row.qty = to_allocate
		new_updated_table_row.warehouse = warehouse
		updated_table.append(new_updated_table_row)

	for item in items:
		conversion = flt(item.conversion_factor)
		uom_must_be_whole_number = frappe.db.get_value('UOM', item.uom, 'must_be_whole_number')
		pending_qty, pending_stock_qty, item_code = flt(item.qty), flt(item.stock_qty), item.item_code

		if not pending_qty:
			add_row(item, pending_qty, item.warehouse)
			continue

		at_capacity, rules = get_ordered_putaway_rules(item_code, company)

		if not rules:
			if at_capacity:
				# rules available, but no free space
				add_row(item, pending_qty, '')
				items_not_accomodated.append([item_code, pending_qty])
			else:
				# no rules to apply
				add_row(item, pending_qty, item.warehouse)
			continue

		# maintain item wise rules, to handle if item is entered twice
		# in the table, due to different price, etc.
		if not item_wise_rules[item_code]:
			item_wise_rules[item_code] = rules

		for rule in item_wise_rules[item_code]:
			if pending_stock_qty > 0 and rule.free_space:
				stock_qty_to_allocate = flt(rule.free_space) if pending_stock_qty >= flt(rule.free_space) else pending_stock_qty
				qty_to_allocate = stock_qty_to_allocate / (conversion or 1)

				if uom_must_be_whole_number:
					qty_to_allocate = floor(qty_to_allocate)
					stock_qty_to_allocate = qty_to_allocate * conversion

				if not qty_to_allocate: break

				add_row(item, qty_to_allocate, rule.warehouse)

				pending_stock_qty -= stock_qty_to_allocate
				pending_qty -= qty_to_allocate
				rule["free_space"] -= stock_qty_to_allocate

				if not pending_stock_qty: break

		# if pending qty after applying all rules, add row without warehouse
		if pending_stock_qty > 0:
			add_row(item, pending_qty, '')
			items_not_accomodated.append([item.item_code, pending_qty])

	if items_not_accomodated:
		msg = _("The following Items, having Putaway Rules, could not be accomodated:") + "<br><br><ul><li>"
		formatted_item_qty = [entry[0] + " : " + str(entry[1]) for entry in items_not_accomodated]
		msg += "</li><li>".join(formatted_item_qty)
		msg += "</li></ul>"
		frappe.msgprint(msg, title=_("Insufficient Capacity"), is_minimizable=True, wide=True)

	return updated_table if updated_table else items
	# TODO: check pricing rule, item tax impact