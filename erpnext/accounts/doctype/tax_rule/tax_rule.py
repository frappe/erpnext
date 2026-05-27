# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import functools

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_default_address
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.query_builder.functions import IfNull
from frappe.utils import cstr
from frappe.utils.nestedset import get_root_of

from erpnext.setup.doctype.customer_group.customer_group import get_parent_customer_groups
from erpnext.setup.doctype.supplier_group.supplier_group import get_parent_supplier_groups


class IncorrectCustomerGroup(frappe.ValidationError):
	pass


class IncorrectSupplierType(frappe.ValidationError):
	pass


class ConflictingTaxRule(frappe.ValidationError):
	pass


class TaxRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		billing_city: DF.Data | None
		billing_country: DF.Link | None
		billing_county: DF.Data | None
		billing_state: DF.Data | None
		billing_zipcode: DF.Data | None
		company: DF.Link | None
		customer: DF.Link | None
		customer_group: DF.Link | None
		from_date: DF.Date | None
		item: DF.Link | None
		item_group: DF.Link | None
		priority: DF.Int
		purchase_tax_template: DF.Link | None
		sales_tax_template: DF.Link | None
		shipping_city: DF.Data | None
		shipping_country: DF.Link | None
		shipping_county: DF.Data | None
		shipping_state: DF.Data | None
		shipping_zipcode: DF.Data | None
		supplier: DF.Link | None
		supplier_group: DF.Link | None
		tax_category: DF.Link | None
		tax_type: DF.Literal["Sales", "Purchase"]
		to_date: DF.Date | None
		use_for_shopping_cart: DF.Check
	# end: auto-generated types

	def validate(self):
		self.validate_tax_template()
		self.validate_from_to_dates("from_date", "to_date")
		self.validate_filters()

	def validate_tax_template(self):
		if self.tax_type == "Sales":
			self.purchase_tax_template = self.supplier = self.supplier_group = None
			if self.customer:
				self.customer_group = None

		else:
			self.sales_tax_template = self.customer = self.customer_group = None

			if self.supplier:
				self.supplier_group = None

		if not (self.sales_tax_template or self.purchase_tax_template):
			frappe.throw(_("Tax Template is mandatory."))

	def validate_filters(self):
		TaxRule = DocType("Tax Rule")

		filters = {
			"tax_type": self.tax_type,
			"customer": self.customer,
			"customer_group": self.customer_group,
			"supplier": self.supplier,
			"supplier_group": self.supplier_group,
			"item": self.item,
			"item_group": self.item_group,
			"billing_city": self.billing_city,
			"billing_county": self.billing_county,
			"billing_state": self.billing_state,
			"billing_zipcode": self.billing_zipcode,
			"billing_country": self.billing_country,
			"shipping_city": self.shipping_city,
			"shipping_county": self.shipping_county,
			"shipping_state": self.shipping_state,
			"shipping_zipcode": self.shipping_zipcode,
			"shipping_country": self.shipping_country,
			"tax_category": self.tax_category,
			"company": self.company,
		}

		query = (
			frappe.qb.from_(TaxRule).select(TaxRule.name, TaxRule.priority).where(TaxRule.name != self.name)
		)

		for field, value in filters.items():
			query = query.where(IfNull(TaxRule[field], "") == cstr(value))

		if self.from_date and self.to_date:
			query = query.where(
				((TaxRule.from_date > self.from_date) & (TaxRule.from_date < self.to_date))
				| ((TaxRule.to_date > self.from_date) & (TaxRule.to_date < self.to_date))
				| ((self.from_date > TaxRule.from_date) & (self.from_date < TaxRule.to_date))
				| ((TaxRule.from_date == self.from_date) & (TaxRule.to_date == self.to_date))
			)

		elif self.from_date:
			query = query.where(TaxRule.to_date > self.from_date)

		elif self.to_date:
			query = query.where(TaxRule.from_date < self.to_date)

		tax_rule = query.run(as_dict=True)

		if tax_rule and tax_rule[0].priority == self.priority:
			frappe.throw(
				_("Tax Rule Conflicts with {0}").format(tax_rule[0].name),
				ConflictingTaxRule,
			)


@frappe.whitelist()
def get_party_details(party, party_type, args=None):
	out = {}
	billing_address, shipping_address = None, None
	if args:
		if args.get("billing_address"):
			billing_address = frappe.get_doc("Address", args.get("billing_address"))
		if args.get("shipping_address"):
			shipping_address = frappe.get_doc("Address", args.get("shipping_address"))
	else:
		billing_address_name = get_default_address(party_type, party)
		shipping_address_name = get_default_address(party_type, party, "is_shipping_address")
		if billing_address_name:
			billing_address = frappe.get_doc("Address", billing_address_name)
		if shipping_address_name:
			shipping_address = frappe.get_doc("Address", shipping_address_name)

	if billing_address:
		out["billing_city"] = billing_address.city
		out["billing_county"] = billing_address.county
		out["billing_state"] = billing_address.state
		out["billing_zipcode"] = billing_address.pincode
		out["billing_country"] = billing_address.country

	if shipping_address:
		out["shipping_city"] = shipping_address.city
		out["shipping_county"] = shipping_address.county
		out["shipping_state"] = shipping_address.state
		out["shipping_zipcode"] = shipping_address.pincode
		out["shipping_country"] = shipping_address.country

	return out


def get_tax_template(posting_date, args):
	"""Get matching tax rule"""
	args = frappe._dict(args)

	TaxRule = DocType("Tax Rule")
	query = frappe.qb.from_(TaxRule).select("*")

	if posting_date:
		query = query.where(
			(TaxRule.from_date.isnull() | (TaxRule.from_date <= posting_date))
			& (TaxRule.to_date.isnull() | (TaxRule.to_date >= posting_date))
		)
	else:
		query = query.where(TaxRule.from_date.isnull() & TaxRule.to_date.isnull())

	def get_group_ancestors(doctype, get_parents, value):
		if not value:
			value = get_root_of(doctype)
		return [""] + [d.name for d in get_parents(value)]

	group_fields = {
		"customer_group": ("Customer Group", get_parent_customer_groups),
		"supplier_group": ("Supplier Group", get_parent_supplier_groups),
	}

	args.setdefault("tax_category", "")

	for key, value in args.items():
		if key == "use_for_shopping_cart":
			query = query.where(TaxRule.use_for_shopping_cart == value)
		elif key == "tax_category":
			query = query.where(IfNull(TaxRule.tax_category, "") == (value or ""))
		elif key in group_fields:
			doctype, get_parents = group_fields[key]
			query = query.where(
				IfNull(TaxRule[key], "").isin(get_group_ancestors(doctype, get_parents, value))
			)
		else:
			query = query.where(IfNull(TaxRule[key], "").isin(["", value or ""]))

	tax_rule = query.run(as_dict=True)

	if not tax_rule:
		return None

	for rule in tax_rule:
		rule.no_of_keys_matched = 0
		for key in args:
			if rule.get(key):
				rule.no_of_keys_matched += 1

	def cmp(a, b):
		# refernce: https://docs.python.org/3.0/whatsnew/3.0.html#ordering-comparisons
		return int(a > b) - int(a < b)

	rule = sorted(
		tax_rule,
		key=functools.cmp_to_key(
			lambda b, a: cmp(a.no_of_keys_matched, b.no_of_keys_matched) or cmp(a.priority, b.priority)
		),
	)[0]

	tax_template = rule.sales_tax_template or rule.purchase_tax_template
	doctype = f"{rule.tax_type} Taxes and Charges Template"

	if frappe.db.get_value(doctype, tax_template, "disabled") == 1:
		return None

	return tax_template
