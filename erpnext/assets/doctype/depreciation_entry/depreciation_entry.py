# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.controllers.base_asset import validate_serial_no
from erpnext.controllers.accounts_controller import AccountsController

class DepreciationEntry(AccountsController):
	def validate(self):
		validate_serial_no(self)
		self.validate_depreciation_amount()
		self.set_credit_and_debit_accounts()
		self.validate_reference_doctype()
		self.validate_reference_docname()
		self.validate_depr_schedule_row()
		self.validate_finance_book()

	def on_submit(self):
		self.make_gl_entries()

	def on_cancel(self):
		self.make_gl_entries(cancel=1)

	def validate_depreciation_amount(self):
		if self.depreciation_amount <= 0:
			frappe.throw(_("Depreciation Amount must be greater than zero."), title = _("Invalid Amount"))

	def set_credit_and_debit_accounts(self):
		from erpnext.assets.doctype.depreciation_schedule.depreciation_posting import get_depreciation_accounts

		asset_category = frappe.get_value("Asset", self.asset, "asset_category")

		if (not self.credit_account or not self.debit_account) and asset_category and self.company:
			credit_account, debit_account = get_depreciation_accounts(asset_category, self.company)

			if not self.credit_account:
				self.credit_account = credit_account

			if not self.debit_account:
				self.debit_account = debit_account

	def validate_reference_doctype(self):
		if self.reference_doctype not in ["Asset", "Asset Serial No", "Depreciation Schedule"]:
			frappe.throw(_("Reference Document can only be an Asset, Asset Serial No or Depreciation Schedule."),
				title = _("Invalid Reference"))

		if self.reference_doctype == "Asset Serial No" and not self.serial_no:
			frappe.throw(_("Reference Document Type cannot be {0} when Serial No has not been entered.").
				format(self.reference_doctype), title = _("Invalid Reference"))

	def validate_reference_docname(self):
		if self.reference_doctype in ["Asset", "Asset Serial No"]:
			ideal_reference_docname = self.get_asset_or_serial_no()

			if self.reference_docname != ideal_reference_docname:
				frappe.throw(_("Reference Document Name cannot be {0} when the {1} entered is {2}.").
					format(self.reference_docname, self.reference_doctype, ideal_reference_docname),
					title = _("Invalid Reference"))

		elif self.reference_doctype == "Depreciation Schedule":
			fieldname = "serial_no" if self.serial_no else "asset"

			asset_linked_with_depr_schedule = frappe.get_value("Depreciation Schedule", self.reference_docname, fieldname)
			asset_linked_with_depr_entry = self.get_asset_or_serial_no()

			if asset_linked_with_depr_schedule != asset_linked_with_depr_entry:
				frappe.throw(_("Depreciation Schedule {0} cannot be used here as it is linked with {1}, not {2}.").
					format(self.reference_docname, asset_linked_with_depr_schedule, asset_linked_with_depr_entry),
					title = _("Invalid Reference"))

	def validate_depr_schedule_row(self):
		if self.reference_doctype == "Depreciation Schedule" and not self.depr_schedule_row:
			frappe.throw(_("Depreciation Schedule Row needs to be fetched."), title = _("Missing Value"))

	def validate_finance_book(self):
		is_depreciable_asset = frappe.get_value("Asset", self.asset, "calculate_depreciation")

		if is_depreciable_asset:
			asset_or_serial_no = self.get_asset_or_serial_no()
			finance_books = self.get_finance_books_linked_with_asset(asset_or_serial_no)

			if len(finance_books) == 1:
				if not self.finance_book:
					self.finance_book = finance_books[0]
			elif len(finance_books) > 1:
				if not self.finance_book:
					frappe.throw(_("Enter Finance Book as {0} is linked with multiple Finance Books.").
						format(asset_or_serial_no), title = _("Missing Finance Book"))
			else:
				frappe.throw(_("{0} is not linked with any Finance Books").format(asset_or_serial_no),
					title = _("Invalid Asset"))

			if self.finance_book:
				if self.finance_book not in finance_books:
					finance_books = ', '.join([str(fb) for fb in finance_books])

					frappe.throw(_("{0} is not used in {1}. Please use one of the following instead: {2}").
						format(self.finance_book, asset_or_serial_no, finance_books))

	def get_asset_or_serial_no(self):
		if self.serial_no:
			return self.serial_no
		else:
			return self.asset

	def get_finance_books_linked_with_asset(self, asset_or_serial_no):
		return frappe.get_all(
			"Asset Finance Book",
			filters = {
				"parent": asset_or_serial_no
			},
			pluck = "finance_book"
		)

	def make_gl_entries(self, cancel=0, adv_adj=0):
		from erpnext.accounts.general_ledger import make_gl_entries

		gl_map = []
		for account in [self.credit_account, self.debit_account]:
			dr_or_cr = "credit" if account == self.credit_account else "debit"

			gl_map.append(
				self.get_gl_dict({
					"account": account,
					dr_or_cr: flt(self.depreciation_amount, self.precision("depreciation_amount")),
					dr_or_cr + "_in_account_currency": flt(self.depreciation_amount, self.precision("depreciation_amount")),
					"cost_center": self.cost_center,
					"finance_book": self.finance_book,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"company": self.company
				}, item = self)
			)

		if gl_map:
			make_gl_entries(gl_map, cancel = cancel, adv_adj = adv_adj, update_outstanding = "Yes")
