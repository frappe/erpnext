# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import copy
from frappe import throw, _
from frappe.utils import flt, cint, getdate

from frappe.model.document import Document

from six import string_types

apply_on_dict = {"Item Code": "items",
	"Item Group": "item_groups", "Brand": "brands"}

class PricingRule(Document):
	def validate(self):
		self.validate_mandatory()
		self.validate_duplicate_apply_on()
		self.validate_applicable_for_selling_or_buying()
		self.validate_min_max_amt()
		self.validate_min_max_qty()
		self.cleanup_fields_value()
		self.validate_rate_or_discount()
		self.validate_max_discount()
		self.validate_price_list_with_currency()
		self.validate_dates()

		if not self.margin_type: self.margin_rate_or_amount = 0.0

	def validate_duplicate_apply_on(self):
		field = apply_on_dict.get(self.apply_on)
		if not field:
			return False

		values = [d.get(frappe.scrub(self.apply_on)) for d in self.get(field)]

		if len(values) != len(set(values)):
			frappe.throw(_("Duplicate {0} found in the table").format(self.apply_on))

	def validate_mandatory(self):
		for apply_on, field in apply_on_dict.items():
			if self.apply_on == apply_on and len(self.get(field) or []) < 1:
				throw(_("{0} is not added in the table").format(apply_on), frappe.MandatoryError)

		tocheck = frappe.scrub(self.get("applicable_for", ""))
		if tocheck and not self.get(tocheck):
			throw(_("{0} is required").format(self.meta.get_label(tocheck)), frappe.MandatoryError)

		if self.price_or_product_discount == 'Price' and not self.rate_or_discount:
			throw(_("Rate or Discount is required for the price discount."), frappe.MandatoryError)

	def validate_applicable_for_selling_or_buying(self):
		if not self.selling and not self.buying:
			throw(_("Atleast one of the Selling or Buying must be selected"))

		if not self.selling and self.applicable_for in ["Customer", "Customer Group",
				"Territory", "Sales Partner", "Campaign"]:
			throw(_("Selling must be checked, if Applicable For is selected as {0}"
				.format(self.applicable_for)))

		if not self.buying and self.applicable_for in ["Supplier", "Supplier Group"]:
			throw(_("Buying must be checked, if Applicable For is selected as {0}"
				.format(self.applicable_for)))

	def validate_min_max_qty(self):
		if self.min_qty and self.max_qty and flt(self.min_qty) > flt(self.max_qty):
			throw(_("Min Qty can not be greater than Max Qty"))

	def validate_min_max_amt(self):
		if self.min_amt and self.max_amt and flt(self.min_amt) > flt(self.max_amt):
			throw(_("Min Amt can not be greater than Max Amt"))

	def cleanup_fields_value(self):
		for logic_field in ["apply_on", "applicable_for", "rate_or_discount"]:
			fieldname = frappe.scrub(self.get(logic_field) or "")

			# reset all values except for the logic field
			options = (self.meta.get_options(logic_field) or "").split("\n")
			for f in options:
				if not f: continue

				f = frappe.scrub(f)
				if f!=fieldname:
					self.set(f, None)

		if self.mixed_conditions and self.get("same_item"):
			self.same_item = 0

	def validate_rate_or_discount(self):
		for field in ["Rate"]:
			if flt(self.get(frappe.scrub(field))) < 0:
				throw(_("{0} can not be negative").format(field))

		if self.price_or_product_discount == 'Product' and not self.free_item:
			if self.mixed_conditions:
				frappe.throw(_("Free item code is not selected"))
			else:
				self.same_item = 1

	def validate_max_discount(self):
		if self.rate_or_discount == "Discount Percentage" and self.get("items"):
			for d in self.items:
				max_discount = frappe.get_cached_value("Item", d.item_code, "max_discount")
				if max_discount and flt(self.discount_percentage) > flt(max_discount):
					throw(_("Max discount allowed for item: {0} is {1}%").format(self.item_code, max_discount))

	def validate_price_list_with_currency(self):
		if self.currency and self.for_price_list:
			price_list_currency = frappe.db.get_value("Price List", self.for_price_list, "currency", True)
			if not self.currency == price_list_currency:
				throw(_("Currency should be same as Price List Currency: {0}").format(price_list_currency))

	def validate_dates(self):
		if self.is_cumulative and not (self.valid_from and self.valid_upto):
			frappe.throw(_("Valid from and valid upto fields are mandatory for the cumulative"))

		if self.valid_from and self.valid_upto and getdate(self.valid_from) > getdate(self.valid_upto):
			frappe.throw(_("Valid from date must be less than valid upto date"))

#--------------------------------------------------------------------------------

@frappe.whitelist()
def apply_pricing_rule(args, doc=None):
	"""
		args = {
			"items": [{"doctype": "", "name": "", "item_code": "", "brand": "", "item_group": ""}, ...],
			"customer": "something",
			"customer_group": "something",
			"territory": "something",
			"supplier": "something",
			"supplier_group": "something",
			"currency": "something",
			"conversion_rate": "something",
			"price_list": "something",
			"plc_conversion_rate": "something",
			"company": "something",
			"transaction_date": "something",
			"campaign": "something",
			"sales_partner": "something",
			"ignore_pricing_rule": "something"
		}
	"""

	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)

	if not args.transaction_type:
		set_transaction_type(args)

	# list of dictionaries
	out = []

	if args.get("doctype") == "Material Request": return out

	item_list = args.get("items")
	args.pop("items")

	set_serial_nos_based_on_fifo = frappe.db.get_single_value("Stock Settings",
		"automatically_set_serial_nos_based_on_fifo")

	for item in item_list:
		args_copy = copy.deepcopy(args)
		args_copy.update(item)
		data = get_pricing_rule_for_item(args_copy, item.get('price_list_rate'), doc=doc)
		out.append(data)
		if not item.get("serial_no") and set_serial_nos_based_on_fifo and not args.get('is_return'):
			out[0].update(get_serial_no_for_item(args_copy))

	return out

@frappe.whitelist()
def apply_transaction_pricing_rule(doc):
	from erpnext.accounts.doctype.pricing_rule.utils import apply_pricing_rule_on_transaction

	# converting dict into doc
	if isinstance(doc, string_types):
		doc = json.loads(doc)
	if doc:
		doc = frappe.get_doc(doc)

	apply_pricing_rule_on_transaction(doc)

	discount = {}

	if (
		doc.apply_discount_on and (
			doc.additional_discount_percentage or
			doc.discount_amount
		)
	):
		discount['price'] = {
			'apply_discount_on': doc.apply_discount_on,
			'additional_discount_percentage': doc.additional_discount_percentage,
			'discount_amount': doc.discount_amount,
		}

	for item in doc.items:
		if item.is_free_item:
			discount['product'] = {
				'item_code': item.item_code,
				'qty': item.qty,
				'rate': item.rate,
				'price_list_rate': item.price_list_rate,
				'is_free_item': item.is_free_item,
				'item_name': item.item_name,
				'description': item.description,
				'stock_uom': item.stock_uom,
				'uom': item.uom,
				'conversion_factor': item.conversion_factor,
				'amount': item.amount,
				'income_account': item.income_account,
			}

	return discount

def get_serial_no_for_item(args):
	from erpnext.stock.get_item_details import get_serial_no

	item_details = frappe._dict({
		"doctype": args.doctype,
		"name": args.name,
		"serial_no": args.serial_no
	})
	if args.get("parenttype") in ("Sales Invoice", "Delivery Note") and flt(args.stock_qty) > 0:
		item_details.serial_no = get_serial_no(args)
	return item_details

def get_pricing_rule_for_item(args, price_list_rate=0, doc=None, for_validate=False):
	from erpnext.accounts.doctype.pricing_rule.utils import (get_pricing_rules,
		get_applied_pricing_rules, get_pricing_rule_items, get_product_discount_rule)

	if isinstance(doc, string_types):
		doc = json.loads(doc)

	if doc:
		doc = frappe.get_doc(doc)

	if (args.get('is_free_item') or
		args.get("parenttype") == "Material Request"): return {}

	item_details = frappe._dict({
		"doctype": args.doctype,
		"name": args.name,
		"parent": args.parent,
		"parenttype": args.parenttype,
		"child_docname": args.get('child_docname'),
		"discount_percentage_on_rate": [],
		"discount_amount_on_rate": []
	})

	if args.ignore_pricing_rule or not args.item_code:
		if frappe.db.exists(args.doctype, args.name) and args.get("pricing_rules"):
			item_details = remove_pricing_rule_for_item(args.get("pricing_rules"),
				item_details, args.get('item_code'))
		return item_details

	update_args_for_pricing_rule(args)

	pricing_rules = (get_applied_pricing_rules(args)
		if for_validate and args.get("pricing_rules") else get_pricing_rules(args, doc))

	if pricing_rules:
		rules = []

		for pricing_rule in pricing_rules:
			if not pricing_rule: continue

			if isinstance(pricing_rule, string_types):
				pricing_rule = frappe.get_cached_doc("Pricing Rule", pricing_rule)
				pricing_rule.apply_rule_on_other_items = get_pricing_rule_items(pricing_rule)

			if pricing_rule.get('suggestion'): continue

			item_details.validate_applied_rule = pricing_rule.get("validate_applied_rule", 0)
			item_details.price_or_product_discount = pricing_rule.get("price_or_product_discount")

			rules.append(get_pricing_rule_details(args, pricing_rule))

			if pricing_rule.mixed_conditions or pricing_rule.apply_rule_on_other:
				item_details.update({
					'apply_rule_on_other_items': json.dumps(pricing_rule.apply_rule_on_other_items),
					'price_or_product_discount': pricing_rule.price_or_product_discount,
					'apply_rule_on': (frappe.scrub(pricing_rule.apply_rule_on_other)
						if pricing_rule.apply_rule_on_other else frappe.scrub(pricing_rule.get('apply_on')))
				})

			if pricing_rule.coupon_code_based==1 and args.coupon_code==None:
				return item_details
				
			if not pricing_rule.validate_applied_rule:
				if pricing_rule.price_or_product_discount == "Price":
					apply_price_discount_rule(pricing_rule, item_details, args)
				else:
					get_product_discount_rule(pricing_rule, item_details, args, doc)

		item_details.has_pricing_rule = 1

		item_details.pricing_rules = ','.join([d.pricing_rule for d in rules])

		if not doc: return item_details

	elif args.get("pricing_rules"):
		item_details = remove_pricing_rule_for_item(args.get("pricing_rules"),
			item_details, args.get('item_code'))

	return item_details

def update_args_for_pricing_rule(args):
	if not (args.item_group and args.brand):
		try:
			args.item_group, args.brand = frappe.get_cached_value("Item", args.item_code, ["item_group", "brand"])
		except TypeError:
			# invalid item_code
			return item_details
		if not args.item_group:
			frappe.throw(_("Item Group not mentioned in item master for item {0}").format(args.item_code))

	if args.transaction_type=="selling":
		if args.customer and not (args.customer_group and args.territory):

			if args.quotation_to and args.quotation_to != 'Customer':
				customer = frappe._dict()
			else:
				customer = frappe.get_cached_value("Customer", args.customer, ["customer_group", "territory"])

			if customer:
				args.customer_group, args.territory = customer

		args.supplier = args.supplier_group = None

	elif args.supplier and not args.supplier_group:
		args.supplier_group = frappe.get_cached_value("Supplier", args.supplier, "supplier_group")
		args.customer = args.customer_group = args.territory = None

def get_pricing_rule_details(args, pricing_rule):
	return frappe._dict({
		'pricing_rule': pricing_rule.name,
		'rate_or_discount': pricing_rule.rate_or_discount,
		'margin_type': pricing_rule.margin_type,
		'item_code': args.get("item_code"),
		'child_docname': args.get('child_docname')
	})

def apply_price_discount_rule(pricing_rule, item_details, args):
	item_details.pricing_rule_for = pricing_rule.rate_or_discount

	if ((pricing_rule.margin_type == 'Amount' and pricing_rule.currency == args.currency)
			or (pricing_rule.margin_type == 'Percentage')):
		item_details.margin_type = pricing_rule.margin_type
		item_details.margin_rate_or_amount = pricing_rule.margin_rate_or_amount
	else:
		item_details.margin_type = None
		item_details.margin_rate_or_amount = 0.0

	if pricing_rule.rate_or_discount == 'Rate':
		pricing_rule_rate = 0.0
		if pricing_rule.currency == args.currency:
			pricing_rule_rate = pricing_rule.rate
		item_details.update({
			"price_list_rate": pricing_rule_rate * args.get("conversion_factor", 1),
			"discount_percentage": 0.0
		})

	for apply_on in ['Discount Amount', 'Discount Percentage']:
		if pricing_rule.rate_or_discount != apply_on: continue

		field = frappe.scrub(apply_on)
		if pricing_rule.apply_discount_on_rate:
			discount_field = "{0}_on_rate".format(field)
			item_details[discount_field].append(pricing_rule.get(field, 0))
		else:
			if field not in item_details:
				item_details.setdefault(field, 0)

			item_details[field] += (pricing_rule.get(field, 0)
				if pricing_rule else args.get(field, 0))

def set_discount_amount(rate, item_details):
	for field in ['discount_percentage_on_rate', 'discount_amount_on_rate']:
		for d in item_details.get(field):
			dis_amount = (rate * d / 100
				if field == 'discount_percentage_on_rate' else d)
			rate -= dis_amount
			item_details.rate = rate

def remove_pricing_rule_for_item(pricing_rules, item_details, item_code=None):
	from erpnext.accounts.doctype.pricing_rule.utils import get_pricing_rule_items
	for d in pricing_rules.split(','):
		if not d or not frappe.db.exists("Pricing Rule", d): continue
		pricing_rule = frappe.get_cached_doc('Pricing Rule', d)

		if pricing_rule.price_or_product_discount == 'Price':
			if pricing_rule.rate_or_discount == 'Discount Percentage':
				item_details.discount_percentage = 0.0
				item_details.discount_amount = 0.0

			if pricing_rule.rate_or_discount == 'Discount Amount':
				item_details.discount_amount = 0.0

			if pricing_rule.margin_type in ['Percentage', 'Amount']:
				item_details.margin_rate_or_amount = 0.0
				item_details.margin_type = None
		elif pricing_rule.get('free_item'):
			item_details.remove_free_item = (item_code if pricing_rule.get('same_item')
				else pricing_rule.get('free_item'))

		if pricing_rule.get("mixed_conditions") or pricing_rule.get("apply_rule_on_other"):
			items = get_pricing_rule_items(pricing_rule)
			item_details.apply_on = (frappe.scrub(pricing_rule.apply_rule_on_other)
				if pricing_rule.apply_rule_on_other else frappe.scrub(pricing_rule.get('apply_on')))
			item_details.applied_on_items = ','.join(items)

	item_details.pricing_rules = ''

	return item_details

@frappe.whitelist()
def remove_pricing_rules(item_list):
	if isinstance(item_list, string_types):
		item_list = json.loads(item_list)

	out = []
	for item in item_list:
		item = frappe._dict(item)
		if item.get('pricing_rules'):
			out.append(remove_pricing_rule_for_item(item.get("pricing_rules"),
				item, item.item_code))

	return out

def set_transaction_type(args):
	if args.transaction_type:
		return
	if args.doctype in ("Opportunity", "Quotation", "Sales Order", "Delivery Note", "Sales Invoice"):
		args.transaction_type = "selling"
	elif args.doctype in ("Material Request", "Supplier Quotation", "Purchase Order",
		"Purchase Receipt", "Purchase Invoice"):
			args.transaction_type = "buying"
	elif args.customer:
		args.transaction_type = "selling"
	else:
		args.transaction_type = "buying"

@frappe.whitelist()
def make_pricing_rule(doctype, docname):
	doc = frappe.new_doc("Pricing Rule")
	doc.applicable_for = doctype
	doc.set(frappe.scrub(doctype), docname)
	doc.selling = 1 if doctype == "Customer" else 0
	doc.buying = 1 if doctype == "Supplier" else 0

	return doc

def get_item_uoms(doctype, txt, searchfield, start, page_len, filters):
	items = [filters.get('value')]
	if filters.get('apply_on') != 'Item Code':
		field = frappe.scrub(filters.get('apply_on'))

		items = frappe.db.sql_list("""select name
			from `tabItem` where {0} = %s""".format(field), filters.get('value'))

	return frappe.get_all('UOM Conversion Detail',
		filters = {'parent': ('in', items), 'uom': ("like", "{0}%".format(txt))},
		fields = ["distinct uom"], as_list=1)
