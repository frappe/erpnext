# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import functools

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_default_address
from frappe.model.document import Document
from frappe.utils import cstr
from frappe.utils.nestedset import get_root_of

from erpnext.setup.doctype.customer_group.customer_group import get_parent_customer_groups


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

	def __setup__(self):
		self.flags.ignore_these_exceptions_in_test = [ConflictingTaxRule]

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

		conds = ""
		for d in filters:
			if conds:
				conds += " and "
			conds += f"""ifnull({d}, '') = {frappe.db.escape(cstr(filters[d]))}"""

		if self.from_date and self.to_date:
			conds += f""" and ((from_date > '{self.from_date}' and from_date < '{self.to_date}') or
					(to_date > '{self.from_date}' and to_date < '{self.to_date}') or
					('{self.from_date}' > from_date and '{self.from_date}' < to_date) or
					('{self.from_date}' = from_date and '{self.to_date}' = to_date))"""

		elif self.from_date and not self.to_date:
			conds += f""" and to_date > '{self.from_date}'"""

		elif self.to_date and not self.from_date:
			conds += f""" and from_date < '{self.to_date}'"""

		tax_rule = frappe.db.sql(
			f"select name, priority \
			from `tabTax Rule` where {conds} and name != '{self.name}'",
			as_dict=1,
		)

		if tax_rule:
			if tax_rule[0].priority == self.priority:
				frappe.throw(_("Tax Rule Conflicts with {0}").format(tax_rule[0].name), ConflictingTaxRule)


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
	conditions = []

	if posting_date:
		conditions.append(
			f"""(from_date is null or from_date <= '{posting_date}')
			and (to_date is null or to_date >= '{posting_date}')"""
		)
	else:
		conditions.append("(from_date is null) and (to_date is null)")

	conditions.append(
		"ifnull(tax_category, '') = {}".format(frappe.db.escape(cstr(args.get("tax_category"))))
	)
	if "tax_category" in args.keys():
		del args["tax_category"]

	for key, value in args.items():
		if key == "use_for_shopping_cart":
			conditions.append(f"use_for_shopping_cart = {1 if value else 0}")
		elif key == "customer_group":
			if not value:
				value = get_root_of("Customer Group")
			customer_group_condition = get_customer_group_condition(value)
			conditions.append(f"ifnull({key}, '') in ('', {customer_group_condition})")
		else:
			conditions.append(f"ifnull({key}, '') in ('', {frappe.db.escape(cstr(value))})")

	tax_rule = frappe.db.sql(
		"""select * from `tabTax Rule`
		where {}""".format(" and ".join(conditions)),
		as_dict=True,
	)

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


def get_customer_group_condition(customer_group):
	condition = ""
	customer_groups = ["%s" % (frappe.db.escape(d.name)) for d in get_parent_customer_groups(customer_group)]
	if customer_groups:
		condition = ",".join(["%s"] * len(customer_groups)) % (tuple(customer_groups))
	return condition
