# Copyright, (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, scrub
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
		accounts = frappe.db.sql(
			"""
				SELECT a.applicable_on_account as account
				FROM `tabApplicable On Account` a, `tabAccounting Dimension Filter` d
				WHERE d.name = a.parent
				and d.name != %s
				and d.accounting_dimension = %s
			""",
			(self.name, self.accounting_dimension),
			as_dict=1,
		)

		account_list = [d.account for d in accounts]

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
	if not frappe.flags.get("dimension_filter_map"):
		filters = frappe.db.sql(
			"""
			SELECT
				a.applicable_on_account, d.dimension_value, p.accounting_dimension,
				p.allow_or_restrict, p.fieldname, a.is_mandatory
			FROM
				`tabApplicable On Account` a,
				`tabAccounting Dimension Filter` p
			LEFT JOIN `tabAllowed Dimension` d ON d.parent = p.name
			WHERE
				p.name = a.parent
				AND p.disabled = 0
		""",
			as_dict=1,
		)

		dimension_filter_map = {}

		for f in filters:
			build_map(
				dimension_filter_map,
				f.fieldname,
				f.applicable_on_account,
				f.dimension_value,
				f.allow_or_restrict,
				f.is_mandatory,
			)
		frappe.flags.dimension_filter_map = dimension_filter_map

	return frappe.flags.dimension_filter_map


def build_map(map_object, dimension, account, filter_value, allow_or_restrict, is_mandatory):
	map_object.setdefault(
		(dimension, account),
		{"allowed_dimensions": [], "is_mandatory": is_mandatory, "allow_or_restrict": allow_or_restrict},
	)
	if filter_value:
		map_object[(dimension, account)]["allowed_dimensions"].append(filter_value)
