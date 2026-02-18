# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_link_to_form


class AssetCategory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.assets.doctype.asset_category_account.asset_category_account import AssetCategoryAccount
		from erpnext.assets.doctype.asset_finance_book.asset_finance_book import AssetFinanceBook

		accounts: DF.Table[AssetCategoryAccount]
		asset_category_name: DF.Data
		enable_cwip_accounting: DF.Check
		finance_books: DF.Table[AssetFinanceBook]
		non_depreciable_category: DF.Check
	# end: auto-generated types

	def validate(self):
		self.validate_finance_books()
		self.validate_account_types()
		self.validate_account_currency()
		self.validate_accounts()

	def validate_finance_books(self):
		for d in self.finance_books:
			for field in ("Total Number of Depreciations", "Frequency of Depreciation"):
				if cint(d.get(frappe.scrub(field))) < 1:
					frappe.throw(
						_("Row {0}: {1} must be greater than 0").format(d.idx, field), frappe.MandatoryError
					)

	def validate_account_currency(self):
		account_types = [
			"fixed_asset_account",
			"accumulated_depreciation_account",
			"depreciation_expense_account",
			"capital_work_in_progress_account",
		]
		invalid_accounts = []
		for d in self.accounts:
			company_currency = frappe.get_value("Company", d.get("company_name"), "default_currency")
			for type_of_account in account_types:
				if d.get(type_of_account):
					account_currency = frappe.get_value("Account", d.get(type_of_account), "account_currency")
					if account_currency != company_currency:
						invalid_accounts.append(
							frappe._dict(
								{"type": type_of_account, "idx": d.idx, "account": d.get(type_of_account)}
							)
						)

		for d in invalid_accounts:
			frappe.throw(
				_("Row #{}: Currency of {} - {} doesn't matches company currency.").format(
					d.idx, frappe.bold(frappe.unscrub(d.type)), frappe.bold(d.account)
				),
				title=_("Invalid Account"),
			)

	def validate_account_types(self):
		account_type_map = {
			"fixed_asset_account": {"account_type": ["Fixed Asset"]},
			"accumulated_depreciation_account": {"account_type": ["Accumulated Depreciation"]},
			"depreciation_expense_account": {"account_type": ["Depreciation"]},
			"capital_work_in_progress_account": {"account_type": ["Capital Work in Progress"]},
		}
		for d in self.accounts:
			for fieldname in account_type_map.keys():
				if d.get(fieldname):
					selected_account = d.get(fieldname)
					key_to_match = next(iter(account_type_map.get(fieldname)))  # acount_type or root_type
					selected_key_type = frappe.db.get_value("Account", selected_account, key_to_match)
					expected_key_types = account_type_map[fieldname][key_to_match]

					if selected_key_type not in expected_key_types:
						frappe.throw(
							_(
								"Row #{0}: {1} of {2} should be {3}. Please update the {1} or select a different account."
							).format(
								d.idx,
								frappe.unscrub(key_to_match),
								frappe.bold(selected_account),
								frappe.bold(" or ".join(expected_key_types)),
							),
							title=_("Invalid Account"),
						)

	def validate_accounts(self):
		self.validate_duplicate_rows()
		self.validate_cwip_accounts()
		self.validate_depreciation_accounts()

	def validate_duplicate_rows(self):
		companies = {row.company_name for row in self.accounts}
		if len(companies) != len(self.accounts):
			frappe.throw(_("Cannot set multiple account rows for the same company"))

	def validate_cwip_accounts(self):
		if self.enable_cwip_accounting:
			missing_cwip_accounts_for_company = []
			for d in self.accounts:
				if not d.capital_work_in_progress_account and not frappe.get_cached_value(
					"Company", d.company_name, "capital_work_in_progress_account"
				):
					missing_cwip_accounts_for_company.append(get_link_to_form("Company", d.company_name))

			if missing_cwip_accounts_for_company:
				msg = _("""To enable Capital Work in Progress Accounting,""") + " "
				msg += _("""you must select Capital Work in Progress Account in accounts table""")
				msg += "<br><br>"
				msg += _("You can also set default CWIP account in Company {}").format(
					", ".join(missing_cwip_accounts_for_company)
				)
				frappe.throw(msg, title=_("Missing Account"))

	def validate_depreciation_accounts(self):
		depreciation_account_map = {
			"accumulated_depreciation_account": "Accumulated Depreciation Account",
			"depreciation_expense_account": "Depreciation Expense Account",
		}

		error_msg = []
		companies_with_accounts = set()

		def validate_company_accounts(company, acc_row=None):
			default_accounts = frappe.get_cached_value(
				"Company",
				company,
				["accumulated_depreciation_account", "depreciation_expense_account"],
				as_dict=True,
			)
			for fieldname, label in depreciation_account_map.items():
				row_value = acc_row.get(fieldname) if acc_row else None
				if not row_value and not default_accounts.get(fieldname):
					if acc_row:
						error_msg.append(
							_("Row #{0}: Missing <b>{1}</b> for company <b>{2}</b>.").format(
								acc_row.idx,
								label,
								get_link_to_form("Company", company),
							)
						)
					else:
						msg = _("Missing account configuration for company <b>{0}</b>.").format(
							get_link_to_form("Company", company),
						)
						if msg not in error_msg:
							error_msg.append(msg)

		companies_with_assets = frappe.db.get_all(
			"Asset",
			{
				"calculate_depreciation": 1,
				"asset_category": self.name,
				"status": ["in", ("Submitted", "Partially Depreciated")],
			},
			pluck="company",
			distinct=True,
		)

		for acc_row in self.accounts:
			companies_with_accounts.add(acc_row.company_name)
			if acc_row.company_name in companies_with_assets:
				validate_company_accounts(acc_row.company_name, acc_row)

		for company in companies_with_assets:
			if company not in companies_with_accounts:
				validate_company_accounts(company)

		if error_msg:
			msg = _(
				"Since there are active depreciable assets under this category, the following accounts are required. <br><br>"
			)
			msg += _(
				"You can either configure default depreciation accounts in the Company or set the required accounts in the following rows: <br><br>"
			)
			msg += "<br>".join(error_msg)

			frappe.throw(msg, title=_("Missing Accounts"))


def get_asset_category_account(
	fieldname, item=None, asset=None, account=None, asset_category=None, company=None
):
	if item and frappe.db.get_value("Item", item, "is_fixed_asset"):
		asset_category = frappe.db.get_value("Item", item, ["asset_category"])

	elif not asset_category or not company:
		if account:
			if frappe.db.get_value("Account", account, "account_type") != "Fixed Asset":
				account = None

		if not account:
			asset_details = frappe.db.get_value("Asset", asset, ["asset_category", "company"])
			asset_category, company = asset_details or [None, None]

	account = frappe.db.get_value(
		"Asset Category Account",
		filters={"parent": asset_category, "company_name": company},
		fieldname=fieldname,
	)

	return account
