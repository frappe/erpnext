# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import copy
from frappe import throw, _
from frappe.utils import flt, cint
from frappe.model.document import Document

from six import string_types

class MultiplePricingRuleConflict(frappe.ValidationError): pass

class PricingRule(Document):
	def validate(self):
		self.validate_mandatory()
		self.validate_applicable_for_selling_or_buying()
		self.validate_min_max_qty()
		self.cleanup_fields_value()
		self.validate_rate_or_discount()
		self.validate_max_discount()
		self.validate_price_list_with_currency()

		if not self.margin_type: self.margin_rate_or_amount = 0.0

	def validate_mandatory(self):
		for field in ["apply_on", "applicable_for"]:
			tocheck = frappe.scrub(self.get(field) or "")
			if tocheck and not self.get(tocheck):
				throw(_("{0} is required").format(self.meta.get_label(tocheck)), frappe.MandatoryError)

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

	def validate_rate_or_discount(self):
		for field in ["Rate"]:
			if flt(self.get(frappe.scrub(field))) < 0:
				throw(_("{0} can not be negative").format(field))

	def validate_max_discount(self):
		if self.rate_or_discount == "Discount Percentage" and self.item_code:
			max_discount = frappe.get_cached_value("Item", self.item_code, "max_discount")
			if max_discount and flt(self.discount_percentage) > flt(max_discount):
				throw(_("Max discount allowed for item: {0} is {1}%").format(self.item_code, max_discount))

	def validate_price_list_with_currency(self):
		if self.currency and self.for_price_list:
			price_list_currency = frappe.db.get_value("Price List", self.for_price_list, "currency", True)
			if not self.currency == price_list_currency:
				throw(_("Currency should be same as Price List Currency: {0}").format(price_list_currency))

#--------------------------------------------------------------------------------

@frappe.whitelist()
def apply_pricing_rule(args):
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
		out.append(get_pricing_rule_for_item(args_copy))
		if set_serial_nos_based_on_fifo and not args.get('is_return'):
			out.append(get_serial_no_for_item(args_copy))
	return out

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

def get_pricing_rule_for_item(args):
	if args.get("parenttype") == "Material Request": return {}

	item_details = frappe._dict({
		"doctype": args.doctype,
		"name": args.name,
		"pricing_rule": None
	})

	if args.ignore_pricing_rule or not args.item_code:
		if frappe.db.exists(args.doctype, args.name) and args.get("pricing_rule"):
			item_details = remove_pricing_rule_for_item(args.get("pricing_rule"), item_details)
		return item_details

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
			customer = frappe.get_cached_value("Customer", args.customer, ["customer_group", "territory"])
			if customer:
				args.customer_group, args.territory = customer

		args.supplier = args.supplier_group = None

	elif args.supplier and not args.supplier_group:
		args.supplier_group = frappe.get_cached_value("Supplier", args.supplier, "supplier_group")
		args.customer = args.customer_group = args.territory = None

	pricing_rules = get_pricing_rules(args)
	pricing_rule = filter_pricing_rules(args, pricing_rules)

	if pricing_rule:
		item_details.pricing_rule = pricing_rule.name
		item_details.pricing_rule_for = pricing_rule.rate_or_discount

		if (pricing_rule.margin_type == 'Amount' and pricing_rule.currency == args.currency)\
				or (pricing_rule.margin_type == 'Percentage'):
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
				"price_list_rate": pricing_rule_rate,
				"discount_percentage": 0.0
			})
		else:
			item_details.discount_percentage = (pricing_rule.get('discount_percentage', 0)
				if pricing_rule else args.discount_percentage)
	elif args.get('pricing_rule'):
		item_details = remove_pricing_rule_for_item(args.get("pricing_rule"), item_details)

	return item_details

def remove_pricing_rule_for_item(pricing_rule, item_details):
	pricing_rule = frappe.get_cached_value('Pricing Rule', pricing_rule,
		['price_or_discount', 'margin_type'], as_dict=1)
	if pricing_rule and pricing_rule.price_or_discount == 'Discount Percentage':
		item_details.discount_percentage = 0.0

	if pricing_rule and pricing_rule.margin_type in ['Percentage', 'Amount']:
		item_details.margin_rate_or_amount = 0.0
		item_details.margin_type = None

	if item_details.pricing_rule:
		item_details.pricing_rule = None
	return item_details

@frappe.whitelist()
def remove_pricing_rules(item_list):
	if isinstance(item_list, string_types):
		item_list = json.loads(item_list)

	out = []
	for item in item_list:
		item = frappe._dict(item)
		out.append(remove_pricing_rule_for_item(item.get("pricing_rule"), item))

	return out

def get_pricing_rules(args):
	def _get_tree_conditions(parenttype, allow_blank=True):
		field = frappe.scrub(parenttype)
		condition = ""
		if args.get(field):
			if not frappe.flags.tree_conditions:
				frappe.flags.tree_conditions = {}
			key = (parenttype, args[field], )
			if key in frappe.flags.tree_conditions:
				return frappe.flags.tree_conditions[key]

			try:
				lft, rgt = frappe.db.get_value(parenttype, args[field], ["lft", "rgt"])
			except TypeError:
				frappe.throw(_("Invalid {0}").format(args[field]))

			parent_groups = frappe.db.sql_list("""select name from `tab%s`
				where lft<=%s and rgt>=%s""" % (parenttype, '%s', '%s'), (lft, rgt))

			if parent_groups:
				if allow_blank: parent_groups.append('')
				condition = " ifnull("+field+", '') in ('" + \
					"', '".join([frappe.db.escape(d) for d in parent_groups])+"')"
			frappe.flags.tree_conditions[key] = condition

		return condition


	conditions = item_variant_condition = ""
	values =  {"item_code": args.get("item_code"), "brand": args.get("brand")}

	for field in ["company", "customer", "supplier", "supplier_group", "campaign", "sales_partner"]:
		if args.get(field):
			conditions += " and ifnull("+field+", '') in (%("+field+")s, '')"
			values[field] = args.get(field)
		else:
			conditions += " and ifnull("+field+", '') = ''"

	for parenttype in ["Customer Group", "Territory"]:
		group_condition = _get_tree_conditions(parenttype)
		if group_condition:
			conditions += " and " + group_condition

	if not args.price_list: args.price_list = None
	conditions += " and ifnull(for_price_list, '') in (%(price_list)s, '')"
	values["price_list"] = args.get("price_list")

	if args.get("transaction_date"):
		conditions += """ and %(transaction_date)s between ifnull(valid_from, '2000-01-01')
			and ifnull(valid_upto, '2500-12-31')"""
		values['transaction_date'] = args.get('transaction_date')

	item_group_condition = _get_tree_conditions("Item Group", False)
	if item_group_condition:
		item_group_condition = " or " + item_group_condition

	# load variant of if not defined
	if "variant_of" not in args:
		args.variant_of = frappe.get_cached_value("Item", args.item_code, "variant_of")

	if args.variant_of:
		item_variant_condition = ' or item_code=%(variant_of)s '
		values['variant_of'] = args.variant_of

	return frappe.db.sql("""select * from `tabPricing Rule`
		where (item_code=%(item_code)s {item_variant_condition} {item_group_condition} or brand=%(brand)s)
			and docstatus < 2 and disable = 0
			and {transaction_type} = 1 {conditions}
		order by priority desc, name desc""".format(
			item_group_condition = item_group_condition,
			item_variant_condition = item_variant_condition,
			transaction_type = args.transaction_type,
			conditions = conditions), values, as_dict=1)

def filter_pricing_rules(args, pricing_rules):
	# filter for qty
	if pricing_rules:
		stock_qty = flt(args.get('qty')) * args.get('conversion_factor', 1)

		pricing_rules = list(filter(lambda x: (flt(stock_qty)>=flt(x.min_qty)
			and (flt(stock_qty)<=x.max_qty if x.max_qty else True)), pricing_rules))

		# add variant_of property in pricing rule
		for p in pricing_rules:
			if p.item_code and args.variant_of:
				p.variant_of = args.variant_of
			else:
				p.variant_of = None

	# find pricing rule with highest priority
	if pricing_rules:
		max_priority = max([cint(p.priority) for p in pricing_rules])
		if max_priority:
			pricing_rules = list(filter(lambda x: cint(x.priority)==max_priority, pricing_rules))

	# apply internal priority
	all_fields = ["item_code", "item_group", "brand", "customer", "customer_group", "territory",
		"supplier", "supplier_group", "campaign", "sales_partner", "variant_of"]

	if len(pricing_rules) > 1:
		for field_set in [["item_code", "variant_of", "item_group", "brand"],
			["customer", "customer_group", "territory"], ["supplier", "supplier_group"]]:
				remaining_fields = list(set(all_fields) - set(field_set))
				if if_all_rules_same(pricing_rules, remaining_fields):
					pricing_rules = apply_internal_priority(pricing_rules, field_set, args)
					break

	if len(pricing_rules) > 1:
		rate_or_discount = list(set([d.rate_or_discount for d in pricing_rules]))
		if len(rate_or_discount) == 1 and rate_or_discount[0] == "Discount Percentage":
			pricing_rules = filter(lambda x: x.for_price_list==args.price_list, pricing_rules) \
				or pricing_rules

	if len(pricing_rules) > 1 and not args.for_shopping_cart:
		frappe.throw(_("Multiple Price Rules exists with same criteria, please resolve conflict by assigning priority. Price Rules: {0}")
			.format("\n".join([d.name for d in pricing_rules])), MultiplePricingRuleConflict)
	elif pricing_rules:
		return pricing_rules[0]

def if_all_rules_same(pricing_rules, fields):
	all_rules_same = True
	val = [pricing_rules[0][k] for k in fields]
	for p in pricing_rules[1:]:
		if val != [p[k] for k in fields]:
			all_rules_same = False
			break

	return all_rules_same

def apply_internal_priority(pricing_rules, field_set, args):
	filtered_rules = []
	for field in field_set:
		if args.get(field):
			filtered_rules = filter(lambda x: x[field]==args[field], pricing_rules)
			if filtered_rules: break

	return filtered_rules or pricing_rules

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
