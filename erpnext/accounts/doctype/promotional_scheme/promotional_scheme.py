# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr
from frappe.model.naming import make_autoname
from frappe.model.document import Document

pricing_rule_fields = ['apply_on', 'mixed_conditions', 'is_cumulative', 'other_item_code', 'other_item_group'
	'apply_rule_on_other', 'other_brand', 'selling', 'buying', 'applicable_for', 'valid_from',
	'valid_upto', 'customer', 'customer_group', 'territory', 'sales_partner', 'campaign', 'supplier',
	'supplier_group', 'company', 'currency']

other_fields = ['min_qty', 'max_qty', 'min_amt', 'max_amt', 'priority',
	'warehouse', 'validate_applied_rule']

price_discount_fields = ['rate_or_discount', 'apply_discount_on', 'apply_on_price_list_rate',
	'rate', 'discount_amount', 'discount_percentage']

product_discount_fields = ['free_item', 'free_qty', 'free_item_uom', 'free_item_rate']

class PromotionalScheme(Document):
	def validate(self):
		if not (self.price_discount_slabs
			or self.product_discount_slabs):
			frappe.throw(_("Price or product discount slabs are required"))

	def on_update(self):
		data = frappe.get_all('Pricing Rule', fields = ["promotional_scheme_id", "name"],
			filters = {'promotional_scheme': self.name}) or {}

		self.update_pricing_rules(data)

	def update_pricing_rules(self, data):
		rules = {}
		count = 0

		for d in data:
			rules[d.get('promotional_scheme_id')] = d.get('name')

		docs = get_pricing_rules(self, rules)

		for doc in docs:
			doc.run_method("validate")
			if doc.get("__islocal"):
				count += 1
				doc.insert()
			else:
				doc.save()
				frappe.msgprint(_("Pricing Rule {0} is updated").format(doc.name))

		if count:
			frappe.msgprint(_("New {0} pricing rules are created").format(count))

	def on_trash(self):
		for d in frappe.get_all('Pricing Rule',
			{'promotional_scheme': self.name}):
			frappe.delete_doc('Pricing Rule', d.name)

def get_pricing_rules(doc, rules = {}):
	new_doc = []
	for child_doc, fields in {'price_discount_slabs': price_discount_fields,
		'product_discount_slabs': product_discount_fields}.items():
		if doc.get(child_doc):
			new_doc.extend(_get_pricing_rules(doc, child_doc, fields, rules))

	return new_doc

def _get_pricing_rules(doc, child_doc, discount_fields, rules = {}):
	new_doc = []
	args = get_args_for_pricing_rule(doc)
	for d in doc.get(child_doc):
		if d.name in rules:
			pr = frappe.get_doc('Pricing Rule', rules.get(d.name))
		else:
			pr = frappe.new_doc("Pricing Rule")
			pr.title = make_autoname(doc.name + "-.####")

		pr.update(args)
		for field in (other_fields + discount_fields):
			pr.set(field, d.get(field))

		pr.promotional_scheme_id = d.name
		pr.promotional_scheme = doc.name
		pr.disable = d.disable if d.disable else doc.disable
		pr.price_or_product_discount = ('Price'
			if child_doc == 'price_discount_slabs' else 'Product')

		for field in ['items', 'item_groups', 'brands']:
			if doc.get(field):
				pr.set(field, [])

			apply_on = frappe.scrub(doc.get('apply_on'))
			for d in doc.get(field):
				pr.append(field, {
					apply_on: d.get(apply_on),
					'uom': d.uom
				})

		new_doc.append(pr)

	return new_doc

def get_args_for_pricing_rule(doc):
	args = { 'promotional_scheme': doc.name }

	for d in pricing_rule_fields:
		args[d] = doc.get(d)

	return args