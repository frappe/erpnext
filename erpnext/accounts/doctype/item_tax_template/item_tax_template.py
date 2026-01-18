# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class ItemTaxTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.item_tax_template_detail.item_tax_template_detail import (
			ItemTaxTemplateDetail,
		)

		company: DF.Link
		disabled: DF.Check
		taxes: DF.Table[ItemTaxTemplateDetail]
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_tax_accounts()

	def autoname(self):
		if self.company and self.title:
			abbr = frappe.get_cached_value("Company", self.company, "abbr")
			self.name = f"{self.title} - {abbr}"

	def validate_tax_accounts(self):
		"""Check whether Tax Rate is not entered twice for same Tax Type"""
		check_list = []
		for d in self.get("taxes"):
			if d.tax_type:
				account_type, account_company = frappe.get_cached_value(
					"Account", d.tax_type, ["account_type", "company"]
				)

				if account_company != self.company:
					frappe.throw(
						_("Item Tax Row {0}: Account must belong to Company - {1}").format(
							d.idx, frappe.bold(self.company)
						)
					)

				if account_type not in [
					"Tax",
					"Chargeable",
					"Income Account",
					"Expense Account",
					"Expenses Included In Valuation",
				]:
					frappe.throw(
						_(
							"Item Tax Row {0} must have account of type Tax or Income or Expense or Chargeable"
						).format(d.idx)
					)
				else:
					if d.tax_type in check_list:
						frappe.throw(_("{0} entered twice in Item Tax").format(d.tax_type))
					else:
						check_list.append(d.tax_type)
