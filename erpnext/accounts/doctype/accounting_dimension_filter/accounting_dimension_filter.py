# Copyright, (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Any

import frappe
from frappe import _, scrub
from frappe.model.document import Document
from frappe.query_builder import DocType
from frappe.utils.nestedset import get_descendants_of


class AccountingDimensionFilter(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.allowed_dimension.allowed_dimension import AllowedDimension
		from erpnext.accounts.doctype.applicable_on_account.applicable_on_account import (
			ApplicableOnAccount,
		)

		accounting_dimension: DF.Literal
		accounts: DF.Table[ApplicableOnAccount]
		allow_or_restrict: DF.Literal["Allow", "Restrict"]
		apply_restriction_on_values: DF.Check
		company: DF.Link
		dimensions: DF.Table[AllowedDimension]
		disabled: DF.Check
	# end: auto-generated types

	def before_save(self):
		# If restriction is not applied on values, then remove all the dimensions and set allow_or_restrict to Restrict
		if not self.apply_restriction_on_values:
			self.allow_or_restrict = "Restrict"
			self.set("dimensions", [])

	def validate(self):
		self.validate_applicable_accounts()

	def validate_applicable_accounts(self):
		ApplicableOnAccount = DocType("Applicable On Account")
		AccountingDimensionFilter = DocType("Accounting Dimension Filter")

		account_list = (
			frappe.qb.from_(ApplicableOnAccount)
			.inner_join(AccountingDimensionFilter)
			.on(AccountingDimensionFilter.name == ApplicableOnAccount.parent)
			.select(
				(ApplicableOnAccount.applicable_on_account).as_("account"),
			)
			.where(AccountingDimensionFilter.name != self.name)
			.where(AccountingDimensionFilter.accounting_dimension == self.accounting_dimension)
			.run(as_list=True, pluck="account")
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


def get_dimension_filter_map() -> dict[tuple[str, str], dict[str, Any]]:
	if frappe.flags.get("dimension_filter_map"):
		return frappe.flags.dimension_filter_map

	ApplicableOnAccount = DocType("Applicable On Account")
	AllowedDimension = DocType("Allowed Dimension")
	AccountingDimensionFilter = DocType("Accounting Dimension Filter")

	filters = (
		frappe.qb.from_(ApplicableOnAccount)
		.inner_join(AccountingDimensionFilter)
		.on(AccountingDimensionFilter.name == ApplicableOnAccount.parent)
		.inner_join(AllowedDimension)
		.on(AccountingDimensionFilter.name == AllowedDimension.parent)
		.select(
			ApplicableOnAccount.applicable_on_account,
			ApplicableOnAccount.is_mandatory,
			AllowedDimension.dimension_value,
			AccountingDimensionFilter.accounting_dimension,
			AccountingDimensionFilter.allow_or_restrict,
		)
		.run(as_dict=True)
	)

	dimension_filter_map = {}

	for f in filters:
		f.fieldname = scrub(f.accounting_dimension)
		if frappe.get_cached_value("Account", f.applicable_on_account, "is_group"):
			accounts = get_descendants_of("Account", f.applicable_on_account)
		else:
			accounts = [f.applicable_on_account]
		for account in accounts:
			build_map(
				dimension_filter_map,
				f.fieldname,
				account,
				f.dimension_value,
				f.allow_or_restrict,
				f.is_mandatory,
			)

	frappe.flags.dimension_filter_map = dimension_filter_map
	return frappe.flags.dimension_filter_map


def build_map(
	map_object: dict[tuple[str, str], dict[str, Any]],
	dimension: str,
	account: str,
	filter_value: str,
	allow_or_restrict: str,
	is_mandatory: bool,
):
	map_object.setdefault(
		(dimension, account),
		{
			"allowed_dimensions": [],
			"is_mandatory": is_mandatory,
			"allow_or_restrict": allow_or_restrict,
		},
	)
	map_object[(dimension, account)]["allowed_dimensions"].append(filter_value)
