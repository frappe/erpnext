# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors

# For license information, please see license.txt


import copy
import json
import re

import frappe
from frappe import _, throw
from frappe.model.document import Document
from frappe.utils import cint, flt

apply_on_dict = {"Item Code": "items", "Item Group": "item_groups", "Brand": "brands"}

other_fields = ["other_item_code", "other_item_group", "other_brand"]


class PricingRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.pricing_rule_brand.pricing_rule_brand import PricingRuleBrand
		from erpnext.accounts.doctype.pricing_rule_item_code.pricing_rule_item_code import PricingRuleItemCode
		from erpnext.accounts.doctype.pricing_rule_item_group.pricing_rule_item_group import (
			PricingRuleItemGroup,
		)

		applicable_for: DF.Literal[
			"",
			"Customer",
			"Customer Group",
			"Territory",
			"Sales Partner",
			"Campaign",
			"Supplier",
			"Supplier Group",
		]
		apply_discount_on: DF.Literal["Grand Total", "Net Total"]
		apply_discount_on_rate: DF.Check
		apply_multiple_pricing_rules: DF.Check
		apply_on: DF.Literal["", "Item Code", "Item Group", "Brand", "Transaction"]
		apply_recursion_over: DF.Float
		apply_rule_on_other: DF.Literal["", "Item Code", "Item Group", "Brand"]
		brands: DF.Table[PricingRuleBrand]
		buying: DF.Check
		campaign: DF.Link | None
		company: DF.Link | None
		condition: DF.Code | None
		coupon_code_based: DF.Check
		currency: DF.Link
		customer: DF.Link | None
		customer_group: DF.Link | None
		disable: DF.Check
		discount_amount: DF.Currency
		discount_percentage: DF.Float
		for_price_list: DF.Link | None
		free_item: DF.Link | None
		free_item_rate: DF.Currency
		free_item_uom: DF.Link | None
		free_qty: DF.Float
		has_priority: DF.Check
		is_cumulative: DF.Check
		is_recursive: DF.Check
		item_groups: DF.Table[PricingRuleItemGroup]
		items: DF.Table[PricingRuleItemCode]
		margin_rate_or_amount: DF.Float
		margin_type: DF.Literal["", "Percentage", "Amount"]
		max_amt: DF.Currency
		max_qty: DF.Float
		min_amt: DF.Currency
		min_qty: DF.Float
		mixed_conditions: DF.Check
		naming_series: DF.Literal["PRLE-.####"]
		other_brand: DF.Link | None
		other_item_code: DF.Link | None
		other_item_group: DF.Link | None
		price_or_product_discount: DF.Literal["Price", "Product"]
		priority: DF.Literal[
			"",
			"1",
			"2",
			"3",
			"4",
			"5",
			"6",
			"7",
			"8",
			"9",
			"10",
			"11",
			"12",
			"13",
			"14",
			"15",
			"16",
			"17",
			"18",
			"19",
			"20",
		]
		promotional_scheme: DF.Link | None
		promotional_scheme_id: DF.Data | None
		rate: DF.Currency
		rate_or_discount: DF.Literal["", "Rate", "Discount Percentage", "Discount Amount"]
		recurse_for: DF.Float
		round_free_qty: DF.Check
		rule_description: DF.SmallText | None
		sales_partner: DF.Link | None
		same_item: DF.Check
		selling: DF.Check
		supplier: DF.Link | None
		supplier_group: DF.Link | None
		territory: DF.Link | None
		threshold_percentage: DF.Percent
		title: DF.Data
		valid_from: DF.Date | None
		valid_upto: DF.Date | None
		validate_applied_rule: DF.Check
		warehouse: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_mandatory()
		self.validate_duplicate_apply_on()
		self.validate_applicable_for_selling_or_buying()
		self.validate_min_max_amt()
		self.validate_min_max_qty()
		self.validate_recursion()
		self.cleanup_fields_value()
		self.validate_rate_or_discount()
		self.validate_max_discount()
		self.validate_price_list_with_currency()
		self.validate_dates()
		self.validate_condition()
		self.validate_mixed_with_recursion()

		if not self.margin_type:
			self.margin_rate_or_amount = 0.0

	def validate_duplicate_apply_on(self):
		if self.apply_on != "Transaction":
			apply_on_table = apply_on_dict.get(self.apply_on)
			if not apply_on_table:
				return

			apply_on_field = frappe.scrub(self.apply_on)
			values = [d.get(apply_on_field) for d in self.get(apply_on_table) if d.get(apply_on_field)]
			if len(values) != len(set(values)):
				frappe.throw(_("Duplicate {0} found in the table").format(self.apply_on))

	def validate_mandatory(self):
		if self.has_priority and not self.priority:
			throw(_("Priority is mandatory"), frappe.MandatoryError, _("Please Set Priority"))

		if self.priority and not self.has_priority:
			self.has_priority = 1

		for apply_on, field in apply_on_dict.items():
			if self.apply_on == apply_on and len(self.get(field) or []) < 1:
				throw(_("{0} is not added in the table").format(apply_on), frappe.MandatoryError)

		tocheck = frappe.scrub(self.get("applicable_for", ""))
		if tocheck and not self.get(tocheck):
			throw(_("{0} is required").format(self.meta.get_label(tocheck)), frappe.MandatoryError)

		if self.apply_rule_on_other:
			o_field = "other_" + frappe.scrub(self.apply_rule_on_other)
			if not self.get(o_field) and o_field in other_fields:
				frappe.throw(
					_("For the 'Apply Rule On Other' condition the field {0} is mandatory").format(
						frappe.bold(self.apply_rule_on_other)
					)
				)

		if self.price_or_product_discount == "Price" and not self.rate_or_discount:
			throw(_("Rate or Discount is required for the price discount."), frappe.MandatoryError)

		if self.apply_discount_on_rate:
			if not self.priority:
				throw(
					_("As the field {0} is enabled, the field {1} is mandatory.").format(
						frappe.bold("Apply Discount on Discounted Rate"), frappe.bold("Priority")
					)
				)

			if self.priority and cint(self.priority) == 1:
				throw(
					_(
						"As the field {0} is enabled, the value of the field {1} should be more than 1."
					).format(frappe.bold("Apply Discount on Discounted Rate"), frappe.bold("Priority"))
				)

	def validate_applicable_for_selling_or_buying(self):
		if not self.selling and not self.buying:
			throw(_("Atleast one of the Selling or Buying must be selected"))

		if not self.selling and self.applicable_for in [
			"Customer",
			"Customer Group",
			"Territory",
			"Sales Partner",
			"Campaign",
		]:
			throw(
				_("Selling must be checked, if Applicable For is selected as {0}").format(self.applicable_for)
			)

		if not self.buying and self.applicable_for in ["Supplier", "Supplier Group"]:
			throw(
				_("Buying must be checked, if Applicable For is selected as {0}").format(self.applicable_for)
			)

	def validate_min_max_qty(self):
		if self.min_qty and self.max_qty and flt(self.min_qty) > flt(self.max_qty):
			throw(_("Min Qty can not be greater than Max Qty"))

	def validate_min_max_amt(self):
		if self.min_amt and self.max_amt and flt(self.min_amt) > flt(self.max_amt):
			throw(_("Min Amt can not be greater than Max Amt"))

	def validate_recursion(self):
		if self.price_or_product_discount != "Product":
			return
		if self.free_item or self.same_item:
			if flt(self.recurse_for) <= 0:
				self.recurse_for = 1
		if self.is_recursive:
			if flt(self.apply_recursion_over) > flt(self.min_qty):
				throw(_("Min Qty should be greater than Recurse Over Qty"))
			if flt(self.apply_recursion_over) < 0:
				throw(_("Recurse Over Qty cannot be less than 0"))

	def cleanup_fields_value(self):
		for logic_field in ["apply_on", "applicable_for", "rate_or_discount"]:
			fieldname = frappe.scrub(self.get(logic_field) or "")

			# reset all values except for the logic field
			options = (self.meta.get_options(logic_field) or "").split("\n")
			for f in options:
				if not f:
					continue

				scrubbed_f = frappe.scrub(f)

				if logic_field == "apply_on":
					apply_on_f = apply_on_dict.get(f, f)
				else:
					apply_on_f = scrubbed_f

				if scrubbed_f != fieldname:
					self.set(apply_on_f, None)

		if self.mixed_conditions and self.get("same_item"):
			self.same_item = 0

		apply_rule_on_other = frappe.scrub(self.apply_rule_on_other or "")

		cleanup_other_fields = (
			other_fields
			if not apply_rule_on_other
			else [o_field for o_field in other_fields if o_field != "other_" + apply_rule_on_other]
		)

		for other_field in cleanup_other_fields:
			self.set(other_field, None)

	def validate_rate_or_discount(self):
		for field in ["Rate"]:
			if flt(self.get(frappe.scrub(field))) < 0:
				throw(_("{0} can not be negative").format(field))

		if self.price_or_product_discount == "Product" and not self.free_item:
			if self.mixed_conditions:
				frappe.throw(_("Free item code is not selected"))
			else:
				self.same_item = 1

	def validate_max_discount(self):
		if self.rate_or_discount == "Discount Percentage" and self.get("items"):
			for d in self.items:
				max_discount = frappe.get_cached_value("Item", d.item_code, "max_discount")
				if max_discount and flt(self.discount_percentage) > flt(max_discount):
					throw(_("Max discount allowed for item: {0} is {1}%").format(d.item_code, max_discount))

	def validate_price_list_with_currency(self):
		if self.currency and self.for_price_list:
			price_list_currency = frappe.db.get_value("Price List", self.for_price_list, "currency", True)
			if not self.currency == price_list_currency:
				throw(_("Currency should be same as Price List Currency: {0}").format(price_list_currency))

	def validate_dates(self):
		if self.is_cumulative and not (self.valid_from and self.valid_upto):
			frappe.throw(_("Valid from and valid upto fields are mandatory for the cumulative"))

		self.validate_from_to_dates("valid_from", "valid_upto")

	def validate_condition(self):
		if (
			self.condition
			and ("=" in self.condition)
			and re.match(r'[\w\.:_]+\s*={1}\s*[\w\.@\'"]+', self.condition)
		):
			frappe.throw(_("Invalid condition expression"))

	def validate_mixed_with_recursion(self):
		if self.mixed_conditions and self.is_recursive:
			frappe.throw(_("Recursive Discounts with Mixed condition is not supported by the system"))


# --------------------------------------------------------------------------------


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

	if isinstance(args, str):
		args = json.loads(args)

	args = frappe._dict(args)

	if not args.transaction_type:
		set_transaction_type(args)

	# list of dictionaries
	out = []

	if args.get("doctype") == "Material Request":
		return out

	item_list = args.get("items")
	args.pop("items")

	item_code_list = tuple(item.get("item_code") for item in item_list)
	query_items = frappe.get_all(
		"Item",
		fields=["item_code", "has_serial_no"],
		filters=[["item_code", "in", item_code_list]],
		as_list=1,
	)
	serialized_items = dict()
	for item_code, val in query_items:
		serialized_items.setdefault(item_code, val)

	for item in item_list:
		args_copy = copy.deepcopy(args)
		args_copy.update(item)
		data = get_pricing_rule_for_item(args_copy, doc=doc)
		out.append(data)

	return out


def update_pricing_rule_uom(pricing_rule, args):
	child_doc = {"Item Code": "items", "Item Group": "item_groups", "Brand": "brands"}.get(
		pricing_rule.apply_on
	)

	apply_on_field = frappe.scrub(pricing_rule.apply_on)

	for row in pricing_rule.get(child_doc):
		if row.get(apply_on_field) == args.get(apply_on_field):
			pricing_rule.uom = row.uom


def get_pricing_rule_for_item(args, doc=None, for_validate=False):
	from erpnext.accounts.doctype.pricing_rule.utils import (
		get_applied_pricing_rules,
		get_pricing_rule_items,
		get_pricing_rules,
		get_product_discount_rule,
	)

	if isinstance(doc, str):
		doc = json.loads(doc)

	if doc:
		doc = frappe.get_doc(doc)

	if args.get("is_free_item") or args.get("parenttype") == "Material Request":
		return {}

	item_details = frappe._dict(
		{
			"doctype": args.doctype,
			"has_margin": False,
			"name": args.name,
			"free_item_data": [],
			"parent": args.parent,
			"parenttype": args.parenttype,
			"child_docname": args.get("child_docname"),
		}
	)

	if args.ignore_pricing_rule or not args.item_code:
		if frappe.db.exists(args.doctype, args.name) and args.get("pricing_rules"):
			item_details = remove_pricing_rule_for_item(
				args.get("pricing_rules"),
				item_details,
				item_code=args.get("item_code"),
				rate=args.get("price_list_rate"),
			)
		return item_details

	update_args_for_pricing_rule(args)

	pricing_rules = (
		get_applied_pricing_rules(args.get("pricing_rules"))
		if for_validate and args.get("pricing_rules")
		else get_pricing_rules(args, doc)
	)

	if pricing_rules:
		rules = []

		for pricing_rule in pricing_rules:
			if not pricing_rule:
				continue

			if isinstance(pricing_rule, str):
				pricing_rule = frappe.get_cached_doc("Pricing Rule", pricing_rule)
				update_pricing_rule_uom(pricing_rule, args)
				pricing_rule.apply_rule_on_other_items = get_pricing_rule_items(pricing_rule) or []

			if pricing_rule.get("suggestion"):
				continue

			item_details.validate_applied_rule = pricing_rule.get("validate_applied_rule", 0)
			item_details.price_or_product_discount = pricing_rule.get("price_or_product_discount")

			rules.append(get_pricing_rule_details(args, pricing_rule))

			if pricing_rule.mixed_conditions or pricing_rule.apply_rule_on_other:
				item_details.update(
					{
						"price_or_product_discount": pricing_rule.price_or_product_discount,
						"apply_rule_on": (
							frappe.scrub(pricing_rule.apply_rule_on_other)
							if pricing_rule.apply_rule_on_other
							else frappe.scrub(pricing_rule.get("apply_on"))
						),
					}
				)

				if pricing_rule.apply_rule_on_other_items:
					item_details["apply_rule_on_other_items"] = json.dumps(
						pricing_rule.apply_rule_on_other_items
					)

			if pricing_rule.coupon_code_based == 1 and args.coupon_code is None:
				return item_details

			if not pricing_rule.validate_applied_rule:
				if pricing_rule.price_or_product_discount == "Price":
					apply_price_discount_rule(pricing_rule, item_details, args)
				else:
					get_product_discount_rule(pricing_rule, item_details, args, doc)

		if not item_details.get("has_margin"):
			item_details.margin_type = None
			item_details.margin_rate_or_amount = 0.0

		item_details.has_pricing_rule = 1

		item_details.pricing_rules = frappe.as_json([d.pricing_rule for d in rules])

		if not doc:
			return item_details

	elif args.get("pricing_rules"):
		item_details = remove_pricing_rule_for_item(
			args.get("pricing_rules"),
			item_details,
			item_code=args.get("item_code"),
			rate=args.get("price_list_rate"),
		)

	return item_details


def update_args_for_pricing_rule(args):
	if not (args.item_group and args.brand):
		item = frappe.get_cached_value("Item", args.item_code, ("item_group", "brand"))
		if not item:
			return

		args.item_group, args.brand = item

		if not args.item_group:
			frappe.throw(_("Item Group not mentioned in item master for item {0}").format(args.item_code))

	if args.transaction_type == "selling":
		if args.customer and not (args.customer_group and args.territory):
			if args.quotation_to and args.quotation_to != "Customer":
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
	return frappe._dict(
		{
			"pricing_rule": pricing_rule.name,
			"rate_or_discount": pricing_rule.rate_or_discount,
			"margin_type": pricing_rule.margin_type,
			"item_code": args.get("item_code"),
			"child_docname": args.get("child_docname"),
		}
	)


def apply_price_discount_rule(pricing_rule, item_details, args):
	item_details.pricing_rule_for = pricing_rule.rate_or_discount

	if (pricing_rule.margin_type in ["Amount", "Percentage"] and pricing_rule.currency == args.currency) or (
		pricing_rule.margin_type == "Percentage"
	):
		item_details.margin_type = pricing_rule.margin_type
		item_details.has_margin = True

		if pricing_rule.apply_multiple_pricing_rules and item_details.margin_rate_or_amount is not None:
			item_details.margin_rate_or_amount += pricing_rule.margin_rate_or_amount
		else:
			item_details.margin_rate_or_amount = pricing_rule.margin_rate_or_amount

	if pricing_rule.rate_or_discount == "Rate":
		pricing_rule_rate = 0.0
		if pricing_rule.currency == args.currency:
			pricing_rule_rate = pricing_rule.rate

		# TODO https://github.com/frappe/erpnext/pull/23636 solve this in some other way.
		if pricing_rule_rate:
			is_blank_uom = pricing_rule.get("uom") != args.get("uom")
			# Override already set price list rate (from item price)
			# if pricing_rule_rate > 0
			item_details.update(
				{
					"price_list_rate": pricing_rule_rate
					* (args.get("conversion_factor", 1) if is_blank_uom else 1),
				}
			)
		item_details.update({"discount_percentage": 0.0})

	for apply_on in ["Discount Amount", "Discount Percentage"]:
		if pricing_rule.rate_or_discount != apply_on:
			continue

		field = frappe.scrub(apply_on)
		if pricing_rule.apply_discount_on_rate and item_details.get("discount_percentage"):
			# Apply discount on discounted rate
			item_details[field] += (100 - item_details[field]) * (pricing_rule.get(field, 0) / 100)
		elif args.price_list_rate:
			value = pricing_rule.get(field, 0)
			calculate_discount_percentage = False
			if field == "discount_percentage":
				field = "discount_amount"
				value = args.price_list_rate * (value / 100)
				calculate_discount_percentage = True

			if field not in item_details:
				item_details.setdefault(field, 0)

			item_details[field] += value if pricing_rule else args.get(field, 0)
			if calculate_discount_percentage and args.price_list_rate and item_details.discount_amount:
				item_details.discount_percentage = flt(
					(flt(item_details.discount_amount) / flt(args.price_list_rate)) * 100
				)
		else:
			if field not in item_details:
				item_details.setdefault(field, 0)

			item_details[field] += pricing_rule.get(field, 0) if pricing_rule else args.get(field, 0)


@frappe.whitelist()
def remove_pricing_rule_for_item(pricing_rules, item_details, item_code=None, rate=None):
	from erpnext.accounts.doctype.pricing_rule.utils import (
		get_applied_pricing_rules,
		get_pricing_rule_items,
	)

	if isinstance(item_details, str):
		item_details = json.loads(item_details)
		item_details = frappe._dict(item_details)

	for d in get_applied_pricing_rules(pricing_rules):
		if not d or not frappe.db.exists("Pricing Rule", d):
			continue
		pricing_rule = frappe.get_cached_doc("Pricing Rule", d)

		if pricing_rule.price_or_product_discount == "Price":
			if pricing_rule.rate_or_discount == "Discount Percentage":
				item_details.discount_percentage = 0.0
				item_details.discount_amount = 0.0
				item_details.rate = rate or 0.0

			if pricing_rule.rate_or_discount == "Discount Amount":
				item_details.discount_amount = 0.0

			if pricing_rule.margin_type in ["Percentage", "Amount"]:
				item_details.margin_rate_or_amount = 0.0
				item_details.margin_type = None
		elif pricing_rule.get("free_item"):
			item_details.remove_free_item = (
				item_code if pricing_rule.get("same_item") else pricing_rule.get("free_item")
			)

		if pricing_rule.get("mixed_conditions") or pricing_rule.get("apply_rule_on_other"):
			items = get_pricing_rule_items(pricing_rule, other_items=True)
			item_details.apply_on = (
				frappe.scrub(pricing_rule.apply_rule_on_other)
				if pricing_rule.apply_rule_on_other
				else frappe.scrub(pricing_rule.get("apply_on"))
			)
			item_details.applied_on_items = ",".join(items)

	item_details.pricing_rules = ""
	item_details.pricing_rule_removed = True

	return item_details


@frappe.whitelist()
def remove_pricing_rules(item_list):
	if isinstance(item_list, str):
		item_list = json.loads(item_list)

	out = []
	for item in item_list:
		item = frappe._dict(item)
		if item.get("pricing_rules"):
			out.append(
				remove_pricing_rule_for_item(
					item.get("pricing_rules"), item, item.item_code, item.get("price_list_rate")
				)
			)

	return out


def set_transaction_type(args):
	if args.transaction_type:
		return
	if args.doctype in ("Opportunity", "Quotation", "Sales Order", "Delivery Note", "Sales Invoice"):
		args.transaction_type = "selling"
	elif args.doctype in (
		"Material Request",
		"Supplier Quotation",
		"Purchase Order",
		"Purchase Receipt",
		"Purchase Invoice",
	):
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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_item_uoms(doctype, txt, searchfield, start, page_len, filters):
	items = [filters.get("value")]
	if filters.get("apply_on") != "Item Code":
		field = frappe.scrub(filters.get("apply_on"))
		items = [d.name for d in frappe.db.get_all("Item", filters={field: filters.get("value")})]

	return frappe.get_all(
		"UOM Conversion Detail",
		filters={"parent": ("in", items), "uom": ("like", f"{txt}%")},
		fields=["distinct uom"],
		as_list=1,
	)
