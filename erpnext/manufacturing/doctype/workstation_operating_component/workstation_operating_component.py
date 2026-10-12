# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, bold
from frappe.model.document import Document


class WorkstationOperatingComponent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.workstation_operating_component_account.workstation_operating_component_account import (
			WorkstationOperatingComponentAccount,
		)

		accounts: DF.Table[WorkstationOperatingComponentAccount]
		component_name: DF.Data
	# end: auto-generated types

	def validate(self):
		self.validate_duplicate_company()
		self.validate_accounts()

	def validate_duplicate_company(self):
		companies = set()
		for row in self.accounts:
			if row.company in companies:
				frappe.throw(
					_("Row #{0}: Company {1} already has an expense account").format(
						row.idx, bold(row.company)
					)
				)
			companies.add(row.company)

	def validate_accounts(self):
		names = [row.expense_account for row in self.accounts if row.expense_account]
		if not names:
			return

		accounts = {
			account.name: account
			for account in frappe.get_all(
				"Account",
				filters={"name": ["in", names]},
				fields=["name", "company", "is_group", "root_type"],
			)
		}

		for row in self.accounts:
			account = accounts.get(row.expense_account)
			if not account:
				continue

			if account.is_group or account.root_type != "Expense" or account.company != row.company:
				frappe.throw(
					_("Row #{0}: Account {1} must be an Expense ledger account of company {2}").format(
						row.idx, bold(row.expense_account), bold(row.company)
					)
				)
