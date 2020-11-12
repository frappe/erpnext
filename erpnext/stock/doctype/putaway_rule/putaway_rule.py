# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import copy
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document

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
		# check if capacity is lesser than current balance in warehouse
		pass

@frappe.whitelist()
def get_ordered_putaway_rules(item_code, company, qty):
	"""Returns an ordered list of putaway rules to apply on an item."""

	# get enabled putaway rules for this item code in this company that have pending capacity
	# order the rules by priority first
	# if same priority, order by pending capacity (capacity - get how much stock is in the warehouse)
	# return this list
	# [{'name': "something", "free space": 20}, {'name': "something", "free space": 10}]

@frappe.whitelist()
def apply_putaway_rule(items, company):
	""" Applies Putaway Rule on line items.

		items: List of line items in a Purchase Receipt
		company: Company in Purchase Receipt
	"""
	items_not_accomodated = []
	for item in items:
		item_qty = item.qty
		at_capacity, rules = get_ordered_putaway_rules(item.item_code, company, item_qty)

		if not rules:
			if at_capacity:
				items_not_accomodated.append([item.item_code, item_qty])
			continue

		item_row_updated = False
		for rule in rules:
			while item_qty > 0:
				if not item_row_updated:
					# update pre-existing row
					item.qty = rule.qty
					item.warehouse = rule.warehouse
					item_row_updated = True
				else:
					# add rows for split quantity
					added_row = copy.deepcopy(item)
					added_row.qty = rule.qty
					added_row.warehouse = rule.warehouse
					items.append(added_row)

				item_qty -= flt(rule.qty)

		# if pending qty after applying rules, add row without warehouse
		if item_qty > 0:
			added_row = copy.deepcopy(item)
			added_row.qty = item_qty
			added_row.warehouse = ''
			items.append(added_row)
			items_not_accomodated.append([item.item_code, item_qty])

	# need to check pricing rule, item tax impact