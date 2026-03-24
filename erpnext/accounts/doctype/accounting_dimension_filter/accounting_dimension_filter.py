# Copyright, (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class AccountingDimensionFilter(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.allowed_dimension.allowed_dimension import AllowedDimension
		from erpnext.accounts.doctype.applicable_on_account.applicable_on_account import ApplicableOnAccount

		accounting_dimension: DF.Literal[None]
		accounts: DF.Table[ApplicableOnAccount]
		allow_or_restrict: DF.Literal["Allow", "Restrict"]
		apply_restriction_on_values: DF.Check
		company: DF.Link
		dimensions: DF.Table[AllowedDimension]
		disabled: DF.Check
		fieldname: DF.Data | None
	# end: auto-generated types

	def before_save(self):
		# If restriction is not applied on values, then remove all the dimensions and set allow_or_restrict to Restrict
		if not self.apply_restriction_on_values:
			self.allow_or_restrict = "Restrict"
			self.set("dimensions", [])

	def validate(self):
		self.fieldname = frappe.db.get_value(
			"Accounting Dimension", {"document_type": self.accounting_dimension}, "fieldname"
		) or frappe.scrub(self.accounting_dimension)  # scrub to handle default accounting dimension

		self.validate_applicable_accounts()

	def validate_applicable_accounts(self):
		dimension_filters = frappe.get_all(
			"Accounting Dimension Filter",
			filters={"name": ["!=", self.name], "accounting_dimension": self.accounting_dimension},
			pluck="name",
		)

		account_list = []
		if dimension_filters:
			account_list = frappe.get_all(
				"Applicable On Account",
				filters={"parent": ["in", dimension_filters]},
				pluck="applicable_on_account",
			)

		for account in self.get("accounts"):
			if account.applicable_on_account in account_list:
				frappe.throw(
					_("Row {0}: {1} account already applied for Accounting Dimension {2}").format(
						account.idx,
						frappe.bold(account.applicable_on_account),
						frappe.bold(self.accounting_dimension),
					)
				)


def get_dimension_filter_map():
	dimension_filters = frappe.get_all(
		"Accounting Dimension Filter",
		filters={"disabled": 0},
		fields=["name", "accounting_dimension", "allow_or_restrict", "fieldname"],
	)

	dimension_filter_map = {}
	if not dimension_filters:
		return dimension_filter_map

	filter_names = [dimension_filter.name for dimension_filter in dimension_filters]
	account_rows = frappe.get_all(
		"Applicable On Account",
		filters={"parent": ["in", filter_names]},
		fields=["parent", "applicable_on_account", "is_mandatory"],
	)
	dimension_rows = frappe.get_all(
		"Allowed Dimension",
		filters={"parent": ["in", filter_names]},
		fields=["parent", "dimension_value"],
	)
	dimensions_by_parent = {}
	for row in dimension_rows:
		dimensions_by_parent.setdefault(row.parent, []).append(row.dimension_value)
	accounts_by_parent = {}
	for row in account_rows:
		accounts_by_parent.setdefault(row.parent, []).append(row)

	for dimension_filter in dimension_filters:
		filter_values = dimensions_by_parent.get(dimension_filter.name) or [None]
		for account in accounts_by_parent.get(dimension_filter.name, []):
			for filter_value in filter_values:
				build_map(
					dimension_filter_map,
					dimension_filter.fieldname,
					account.applicable_on_account,
					filter_value,
					dimension_filter.allow_or_restrict,
					account.is_mandatory,
				)
	return dimension_filter_map


def build_map(map_object, dimension, account, filter_value, allow_or_restrict, is_mandatory):
	map_object.setdefault(
		(dimension, account),
		{"allowed_dimensions": [], "is_mandatory": is_mandatory, "allow_or_restrict": allow_or_restrict},
	)
	if filter_value:
		map_object[(dimension, account)]["allowed_dimensions"].append(filter_value)
