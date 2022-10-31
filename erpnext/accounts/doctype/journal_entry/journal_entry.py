# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
from frappe import _, msgprint, scrub
from frappe.utils import cint, cstr, flt, fmt_money, formatdate, get_link_to_form, nowdate

import erpnext
from erpnext.accounts.deferred_revenue import get_deferred_booking_accounts
from erpnext.accounts.doctype.invoice_discounting.invoice_discounting import (
	get_party_account_based_on_invoice_discounting,
)
from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import (
	get_party_tax_withholding_details,
)
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import (
	get_account_currency,
	get_balance_on,
	get_stock_accounts,
	get_stock_and_account_balance,
)
from erpnext.controllers.accounts_controller import AccountsController


class StockAccountInvalidTransaction(frappe.ValidationError):
	pass


class JournalEntry(AccountsController):
	def __init__(self, *args, **kwargs):
		super(JournalEntry, self).__init__(*args, **kwargs)

	def get_feed(self):
		return self.voucher_type

	def validate(self):
		if self.voucher_type == "Opening Entry":
			self.is_opening = "Yes"

		if not self.is_opening:
			self.is_opening = "No"

		self.clearance_date = None

		self.validate_party()
		self.validate_entries_for_advance()
		self.validate_multi_currency()
		self.set_amounts_in_company_currency()
		self.validate_debit_credit_amount()

		# Do not validate while importing via data import
		if not frappe.flags.in_import:
			self.validate_total_debit_and_credit()

		if not frappe.flags.is_reverse_depr_entry:
			self.validate_against_jv()
			self.validate_stock_accounts()

		self.validate_reference_doc()
		if self.docstatus == 0:
			self.set_against_account()
		self.create_remarks()
		self.set_print_format_fields()
		self.validate_credit_debit_note()
		self.validate_empty_accounts_table()
		self.set_account_and_party_balance()
		self.validate_inter_company_accounts()

		if self.docstatus == 0:
			self.apply_tax_withholding()

		if not self.title:
			self.title = self.get_title()

	def on_submit(self):
		self.validate_cheque_info()
		self.check_credit_limit()
		self.make_gl_entries()
		self.update_advance_paid()
		self.update_inter_company_jv()
		self.update_invoice_discounting()

	def on_cancel(self):
		from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries

		unlink_ref_doc_from_payment_entries(self)
		self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")
		self.make_gl_entries(1)
		self.update_advance_paid()
		self.unlink_advance_entry_reference()
		self.unlink_asset_reference()
		self.unlink_inter_company_jv()
		self.unlink_asset_adjustment_entry()
		self.update_invoice_discounting()

	def get_title(self):
		return self.pay_to_recd_from or self.accounts[0].account

	def update_advance_paid(self):
		advance_paid = frappe._dict()
		for d in self.get("accounts"):
			if d.is_advance:
				if d.reference_type in frappe.get_hooks("advance_payment_doctypes"):
					advance_paid.setdefault(d.reference_type, []).append(d.reference_name)

		for voucher_type, order_list in advance_paid.items():
			for voucher_no in list(set(order_list)):
				frappe.get_doc(voucher_type, voucher_no).set_total_advance_paid()

	def validate_inter_company_accounts(self):
		if (
			self.voucher_type == "Inter Company Journal Entry"
			and self.inter_company_journal_entry_reference
		):
			doc = frappe.get_doc("Journal Entry", self.inter_company_journal_entry_reference)
			account_currency = frappe.get_cached_value("Company", self.company, "default_currency")
			previous_account_currency = frappe.get_cached_value("Company", doc.company, "default_currency")
			if account_currency == previous_account_currency:
				if self.total_credit != doc.total_debit or self.total_debit != doc.total_credit:
					frappe.throw(_("Total Credit/ Debit Amount should be same as linked Journal Entry"))

	def validate_stock_accounts(self):
		stock_accounts = get_stock_accounts(self.company, self.doctype, self.name)
		for account in stock_accounts:
			account_bal, stock_bal, warehouse_list = get_stock_and_account_balance(
				account, self.posting_date, self.company
			)

			if account_bal == stock_bal:
				frappe.throw(
					_("Account: {0} can only be updated via Stock Transactions").format(account),
					StockAccountInvalidTransaction,
				)

	def apply_tax_withholding(self):
		from erpnext.accounts.report.general_ledger.general_ledger import get_account_type_map

		if not self.apply_tds or self.voucher_type not in ("Debit Note", "Credit Note"):
			return

		parties = [d.party for d in self.get("accounts") if d.party]
		parties = list(set(parties))

		if len(parties) > 1:
			frappe.throw(_("Cannot apply TDS against multiple parties in one entry"))

		account_type_map = get_account_type_map(self.company)
		party_type = "supplier" if self.voucher_type == "Credit Note" else "customer"
		doctype = "Purchase Invoice" if self.voucher_type == "Credit Note" else "Sales Invoice"
		debit_or_credit = (
			"debit_in_account_currency"
			if self.voucher_type == "Credit Note"
			else "credit_in_account_currency"
		)
		rev_debit_or_credit = (
			"credit_in_account_currency"
			if debit_or_credit == "debit_in_account_currency"
			else "debit_in_account_currency"
		)

		party_account = get_party_account(party_type.title(), parties[0], self.company)

		net_total = sum(
			d.get(debit_or_credit)
			for d in self.get("accounts")
			if account_type_map.get(d.account) not in ("Tax", "Chargeable")
		)

		party_amount = sum(
			d.get(rev_debit_or_credit) for d in self.get("accounts") if d.account == party_account
		)

		inv = frappe._dict(
			{
				party_type: parties[0],
				"doctype": doctype,
				"company": self.company,
				"posting_date": self.posting_date,
				"net_total": net_total,
			}
		)

		tax_withholding_details, advance_taxes, voucher_wise_amount = get_party_tax_withholding_details(
			inv, self.tax_withholding_category
		)

		if not tax_withholding_details:
			return

		accounts = []
		for d in self.get("accounts"):
			if d.get("account") == tax_withholding_details.get("account_head"):
				d.update(
					{
						"account": tax_withholding_details.get("account_head"),
						debit_or_credit: tax_withholding_details.get("tax_amount"),
					}
				)

			accounts.append(d.get("account"))

			if d.get("account") == party_account:
				d.update({rev_debit_or_credit: party_amount - tax_withholding_details.get("tax_amount")})

		if not accounts or tax_withholding_details.get("account_head") not in accounts:
			self.append(
				"accounts",
				{
					"account": tax_withholding_details.get("account_head"),
					rev_debit_or_credit: tax_withholding_details.get("tax_amount"),
					"against_account": parties[0],
				},
			)

		to_remove = [
			d
			for d in self.get("accounts")
			if not d.get(rev_debit_or_credit) and d.account == tax_withholding_details.get("account_head")
		]

		for d in to_remove:
			self.remove(d)

	def update_inter_company_jv(self):
		if (
			self.voucher_type == "Inter Company Journal Entry"
			and self.inter_company_journal_entry_reference
		):
			frappe.db.set_value(
				"Journal Entry",
				self.inter_company_journal_entry_reference,
				"inter_company_journal_entry_reference",
				self.name,
			)

	def update_invoice_discounting(self):
		def _validate_invoice_discounting_status(inv_disc, id_status, expected_status, row_id):
			id_link = get_link_to_form("Invoice Discounting", inv_disc)
			if id_status != expected_status:
				frappe.throw(
					_("Row #{0}: Status must be {1} for Invoice Discounting {2}").format(
						d.idx, expected_status, id_link
					)
				)

		invoice_discounting_list = list(
			set([d.reference_name for d in self.accounts if d.reference_type == "Invoice Discounting"])
		)
		for inv_disc in invoice_discounting_list:
			inv_disc_doc = frappe.get_doc("Invoice Discounting", inv_disc)
			status = None
			for d in self.accounts:
				if d.account == inv_disc_doc.short_term_loan and d.reference_name == inv_disc:
					if self.docstatus == 1:
						if d.credit > 0:
							_validate_invoice_discounting_status(inv_disc, inv_disc_doc.status, "Sanctioned", d.idx)
							status = "Disbursed"
						elif d.debit > 0:
							_validate_invoice_discounting_status(inv_disc, inv_disc_doc.status, "Disbursed", d.idx)
							status = "Settled"
					else:
						if d.credit > 0:
							_validate_invoice_discounting_status(inv_disc, inv_disc_doc.status, "Disbursed", d.idx)
							status = "Sanctioned"
						elif d.debit > 0:
							_validate_invoice_discounting_status(inv_disc, inv_disc_doc.status, "Settled", d.idx)
							status = "Disbursed"
					break
			if status:
				inv_disc_doc.set_status(status=status)

	def unlink_advance_entry_reference(self):
		for d in self.get("accounts"):
			if d.is_advance == "Yes" and d.reference_type in ("Sales Invoice", "Purchase Invoice"):
				doc = frappe.get_doc(d.reference_type, d.reference_name)
				doc.delink_advance_entries(self.name)
				d.reference_type = ""
				d.reference_name = ""
				d.db_update()

	def unlink_asset_reference(self):
		for d in self.get("accounts"):
			if d.reference_type == "Asset" and d.reference_name:
				asset = frappe.get_doc("Asset", d.reference_name)
				for s in asset.get("schedules"):
					if s.journal_entry == self.name:
						s.db_set("journal_entry", None)

						idx = cint(s.finance_book_id) or 1
						finance_books = asset.get("finance_books")[idx - 1]
						finance_books.value_after_depreciation += s.depreciation_amount
						finance_books.db_update()

						asset.set_status()

	def unlink_inter_company_jv(self):
		if (
			self.voucher_type == "Inter Company Journal Entry"
			and self.inter_company_journal_entry_reference
		):
			frappe.db.set_value(
				"Journal Entry",
				self.inter_company_journal_entry_reference,
				"inter_company_journal_entry_reference",
				"",
			)
			frappe.db.set_value("Journal Entry", self.name, "inter_company_journal_entry_reference", "")

	def unlink_asset_adjustment_entry(self):
		frappe.db.sql(
			""" update `tabAsset Value Adjustment`
			set journal_entry = null where journal_entry = %s""",
			self.name,
		)

	def validate_party(self):
		for d in self.get("accounts"):
			account_type = frappe.db.get_value("Account", d.account, "account_type")
			if account_type in ["Receivable", "Payable"]:
				if not (d.party_type and d.party):
					frappe.throw(
						_("Row {0}: Party Type and Party is required for Receivable / Payable account {1}").format(
							d.idx, d.account
						)
					)

	def check_credit_limit(self):
		customers = list(
			set(
				d.party
				for d in self.get("accounts")
				if d.party_type == "Customer" and d.party and flt(d.debit) > 0
			)
		)
		if customers:
			from erpnext.selling.doctype.customer.customer import check_credit_limit

			for customer in customers:
				check_credit_limit(customer, self.company)

	def validate_cheque_info(self):
		if self.voucher_type in ["Bank Entry"]:
			if not self.cheque_no or not self.cheque_date:
				msgprint(
					_("Reference No & Reference Date is required for {0}").format(self.voucher_type),
					raise_exception=1,
				)

		if self.cheque_date and not self.cheque_no:
			msgprint(_("Reference No is mandatory if you entered Reference Date"), raise_exception=1)

	def validate_entries_for_advance(self):
		for d in self.get("accounts"):
			if d.reference_type not in ("Sales Invoice", "Purchase Invoice", "Journal Entry"):
				if (d.party_type == "Customer" and flt(d.credit) > 0) or (
					d.party_type == "Supplier" and flt(d.debit) > 0
				):
					if d.is_advance == "No":
						msgprint(
							_(
								"Row {0}: Please check 'Is Advance' against Account {1} if this is an advance entry."
							).format(d.idx, d.account),
							alert=True,
						)
					elif d.reference_type in ("Sales Order", "Purchase Order") and d.is_advance != "Yes":
						frappe.throw(
							_(
								"Row {0}: Payment against Sales/Purchase Order should always be marked as advance"
							).format(d.idx)
						)

				if d.is_advance == "Yes":
					if d.party_type == "Customer" and flt(d.debit) > 0:
						frappe.throw(_("Row {0}: Advance against Customer must be credit").format(d.idx))
					elif d.party_type == "Supplier" and flt(d.credit) > 0:
						frappe.throw(_("Row {0}: Advance against Supplier must be debit").format(d.idx))

	def validate_against_jv(self):
		for d in self.get("accounts"):
			if d.reference_type == "Journal Entry":
				account_root_type = frappe.db.get_value("Account", d.account, "root_type")
				if account_root_type == "Asset" and flt(d.debit) > 0:
					frappe.throw(
						_(
							"Row #{0}: For {1}, you can select reference document only if account gets credited"
						).format(d.idx, d.account)
					)
				elif account_root_type == "Liability" and flt(d.credit) > 0:
					frappe.throw(
						_(
							"Row #{0}: For {1}, you can select reference document only if account gets debited"
						).format(d.idx, d.account)
					)

				if d.reference_name == self.name:
					frappe.throw(_("You can not enter current voucher in 'Against Journal Entry' column"))

				against_entries = frappe.db.sql(
					"""select * from `tabJournal Entry Account`
					where account = %s and docstatus = 1 and parent = %s
					and (reference_type is null or reference_type in ('', 'Sales Order', 'Purchase Order'))
					""",
					(d.account, d.reference_name),
					as_dict=True,
				)

				if not against_entries:
					frappe.throw(
						_(
							"Journal Entry {0} does not have account {1} or already matched against other voucher"
						).format(d.reference_name, d.account)
					)
				else:
					dr_or_cr = "debit" if d.credit > 0 else "credit"
					valid = False
					for jvd in against_entries:
						if flt(jvd[dr_or_cr]) > 0:
							valid = True
					if not valid:
						frappe.throw(
							_("Against Journal Entry {0} does not have any unmatched {1} entry").format(
								d.reference_name, dr_or_cr
							)
						)

	def validate_reference_doc(self):
		"""Validates reference document"""
		field_dict = {
			"Sales Invoice": ["Customer", "Debit To"],
			"Purchase Invoice": ["Supplier", "Credit To"],
			"Sales Order": ["Customer"],
			"Purchase Order": ["Supplier"],
		}

		self.reference_totals = {}
		self.reference_types = {}
		self.reference_accounts = {}

		for d in self.get("accounts"):
			if not d.reference_type:
				d.reference_name = None
			if not d.reference_name:
				d.reference_type = None
			if d.reference_type and d.reference_name and (d.reference_type in list(field_dict)):
				dr_or_cr = (
					"credit_in_account_currency"
					if d.reference_type in ("Sales Order", "Sales Invoice")
					else "debit_in_account_currency"
				)

				# check debit or credit type Sales / Purchase Order
				if d.reference_type == "Sales Order" and flt(d.debit) > 0:
					frappe.throw(
						_("Row {0}: Debit entry can not be linked with a {1}").format(d.idx, d.reference_type)
					)

				if d.reference_type == "Purchase Order" and flt(d.credit) > 0:
					frappe.throw(
						_("Row {0}: Credit entry can not be linked with a {1}").format(d.idx, d.reference_type)
					)

				# set totals
				if not d.reference_name in self.reference_totals:
					self.reference_totals[d.reference_name] = 0.0

				if self.voucher_type not in ("Deferred Revenue", "Deferred Expense"):
					self.reference_totals[d.reference_name] += flt(d.get(dr_or_cr))

				self.reference_types[d.reference_name] = d.reference_type
				self.reference_accounts[d.reference_name] = d.account

				against_voucher = frappe.db.get_value(
					d.reference_type, d.reference_name, [scrub(dt) for dt in field_dict.get(d.reference_type)]
				)

				if not against_voucher:
					frappe.throw(_("Row {0}: Invalid reference {1}").format(d.idx, d.reference_name))

				# check if party and account match
				if d.reference_type in ("Sales Invoice", "Purchase Invoice"):
					if self.voucher_type in ("Deferred Revenue", "Deferred Expense") and d.reference_detail_no:
						debit_or_credit = "Debit" if d.debit else "Credit"
						party_account = get_deferred_booking_accounts(
							d.reference_type, d.reference_detail_no, debit_or_credit
						)
						against_voucher = ["", against_voucher[1]]
					else:
						if d.reference_type == "Sales Invoice":
							party_account = (
								get_party_account_based_on_invoice_discounting(d.reference_name) or against_voucher[1]
							)
						else:
							party_account = against_voucher[1]

					if against_voucher[0] != cstr(d.party) or party_account != d.account:
						frappe.throw(
							_("Row {0}: Party / Account does not match with {1} / {2} in {3} {4}").format(
								d.idx,
								field_dict.get(d.reference_type)[0],
								field_dict.get(d.reference_type)[1],
								d.reference_type,
								d.reference_name,
							)
						)

				# check if party matches for Sales / Purchase Order
				if d.reference_type in ("Sales Order", "Purchase Order"):
					# set totals
					if against_voucher != d.party:
						frappe.throw(
							_("Row {0}: {1} {2} does not match with {3}").format(
								d.idx, d.party_type, d.party, d.reference_type
							)
						)

		self.validate_orders()
		self.validate_invoices()

	def validate_orders(self):
		"""Validate totals, closed and docstatus for orders"""
		for reference_name, total in self.reference_totals.items():
			reference_type = self.reference_types[reference_name]
			account = self.reference_accounts[reference_name]

			if reference_type in ("Sales Order", "Purchase Order"):
				order = frappe.get_doc(reference_type, reference_name)

				if order.docstatus != 1:
					frappe.throw(_("{0} {1} is not submitted").format(reference_type, reference_name))

				if flt(order.per_billed) >= 100:
					frappe.throw(_("{0} {1} is fully billed").format(reference_type, reference_name))

				if cstr(order.status) == "Closed":
					frappe.throw(_("{0} {1} is closed").format(reference_type, reference_name))

				account_currency = get_account_currency(account)
				if account_currency == self.company_currency:
					voucher_total = order.base_grand_total
					formatted_voucher_total = fmt_money(
						voucher_total, order.precision("base_grand_total"), currency=account_currency
					)
				else:
					voucher_total = order.grand_total
					formatted_voucher_total = fmt_money(
						voucher_total, order.precision("grand_total"), currency=account_currency
					)

				if flt(voucher_total) < (flt(order.advance_paid) + total):
					frappe.throw(
						_("Advance paid against {0} {1} cannot be greater than Grand Total {2}").format(
							reference_type, reference_name, formatted_voucher_total
						)
					)

	def validate_invoices(self):
		"""Validate totals and docstatus for invoices"""
		for reference_name, total in self.reference_totals.items():
			reference_type = self.reference_types[reference_name]

			if reference_type in ("Sales Invoice", "Purchase Invoice") and self.voucher_type not in [
				"Debit Note",
				"Credit Note",
			]:
				invoice = frappe.db.get_value(
					reference_type, reference_name, ["docstatus", "outstanding_amount"], as_dict=1
				)

				if invoice.docstatus != 1:
					frappe.throw(_("{0} {1} is not submitted").format(reference_type, reference_name))

				if total and flt(invoice.outstanding_amount) < total:
					frappe.throw(
						_("Payment against {0} {1} cannot be greater than Outstanding Amount {2}").format(
							reference_type, reference_name, invoice.outstanding_amount
						)
					)

	def set_against_account(self):
		accounts_debited, accounts_credited = [], []
		if self.voucher_type in ("Deferred Revenue", "Deferred Expense"):
			for d in self.get("accounts"):
				if d.reference_type == "Sales Invoice":
					field = "customer"
				else:
					field = "supplier"

				d.against_account = frappe.db.get_value(d.reference_type, d.reference_name, field)
		else:
			for d in self.get("accounts"):
				if flt(d.debit > 0):
					accounts_debited.append(d.party or d.account)
				if flt(d.credit) > 0:
					accounts_credited.append(d.party or d.account)

			for d in self.get("accounts"):
				if flt(d.debit > 0):
					d.against_account = ", ".join(list(set(accounts_credited)))
				if flt(d.credit > 0):
					d.against_account = ", ".join(list(set(accounts_debited)))

	def validate_debit_credit_amount(self):
		for d in self.get("accounts"):
			if not flt(d.debit) and not flt(d.credit):
				frappe.throw(_("Row {0}: Both Debit and Credit values cannot be zero").format(d.idx))

	def validate_total_debit_and_credit(self):
		self.set_total_debit_credit()
		if self.difference:
			frappe.throw(
				_("Total Debit must be equal to Total Credit. The difference is {0}").format(self.difference)
			)

	def set_total_debit_credit(self):
		self.total_debit, self.total_credit, self.difference = 0, 0, 0
		for d in self.get("accounts"):
			if d.debit and d.credit:
				frappe.throw(_("You cannot credit and debit same account at the same time"))

			self.total_debit = flt(self.total_debit) + flt(d.debit, d.precision("debit"))
			self.total_credit = flt(self.total_credit) + flt(d.credit, d.precision("credit"))

		self.difference = flt(self.total_debit, self.precision("total_debit")) - flt(
			self.total_credit, self.precision("total_credit")
		)

	def validate_multi_currency(self):
		alternate_currency = []
		for d in self.get("accounts"):
			account = frappe.db.get_value(
				"Account", d.account, ["account_currency", "account_type"], as_dict=1
			)
			if account:
				d.account_currency = account.account_currency
				d.account_type = account.account_type

			if not d.account_currency:
				d.account_currency = self.company_currency

			if d.account_currency != self.company_currency and d.account_currency not in alternate_currency:
				alternate_currency.append(d.account_currency)

		if alternate_currency:
			if not self.multi_currency:
				frappe.throw(_("Please check Multi Currency option to allow accounts with other currency"))

		self.set_exchange_rate()

	def set_amounts_in_company_currency(self):
		for d in self.get("accounts"):
			d.debit_in_account_currency = flt(
				d.debit_in_account_currency, d.precision("debit_in_account_currency")
			)
			d.credit_in_account_currency = flt(
				d.credit_in_account_currency, d.precision("credit_in_account_currency")
			)

			d.debit = flt(d.debit_in_account_currency * flt(d.exchange_rate), d.precision("debit"))
			d.credit = flt(d.credit_in_account_currency * flt(d.exchange_rate), d.precision("credit"))

	def set_exchange_rate(self):
		for d in self.get("accounts"):
			if d.account_currency == self.company_currency:
				d.exchange_rate = 1
			elif (
				not d.exchange_rate
				or d.exchange_rate == 1
				or (
					d.reference_type in ("Sales Invoice", "Purchase Invoice")
					and d.reference_name
					and self.posting_date
				)
			):

				# Modified to include the posting date for which to retreive the exchange rate
				d.exchange_rate = get_exchange_rate(
					self.posting_date,
					d.account,
					d.account_currency,
					self.company,
					d.reference_type,
					d.reference_name,
					d.debit,
					d.credit,
					d.exchange_rate,
				)

			if not d.exchange_rate:
				frappe.throw(_("Row {0}: Exchange Rate is mandatory").format(d.idx))

	def create_remarks(self):
		r = []

		if self.user_remark:
			r.append(_("Note: {0}").format(self.user_remark))

		if self.cheque_no:
			if self.cheque_date:
				r.append(_("Reference #{0} dated {1}").format(self.cheque_no, formatdate(self.cheque_date)))
			else:
				msgprint(_("Please enter Reference date"), raise_exception=frappe.MandatoryError)

		for d in self.get("accounts"):
			if d.reference_type == "Sales Invoice" and d.credit:
				r.append(
					_("{0} against Sales Invoice {1}").format(
						fmt_money(flt(d.credit), currency=self.company_currency), d.reference_name
					)
				)

			if d.reference_type == "Sales Order" and d.credit:
				r.append(
					_("{0} against Sales Order {1}").format(
						fmt_money(flt(d.credit), currency=self.company_currency), d.reference_name
					)
				)

			if d.reference_type == "Purchase Invoice" and d.debit:
				bill_no = frappe.db.sql(
					"""select bill_no, bill_date
					from `tabPurchase Invoice` where name=%s""",
					d.reference_name,
				)
				if (
					bill_no
					and bill_no[0][0]
					and bill_no[0][0].lower().strip() not in ["na", "not applicable", "none"]
				):
					r.append(
						_("{0} against Bill {1} dated {2}").format(
							fmt_money(flt(d.debit), currency=self.company_currency),
							bill_no[0][0],
							bill_no[0][1] and formatdate(bill_no[0][1].strftime("%Y-%m-%d")),
						)
					)

			if d.reference_type == "Purchase Order" and d.debit:
				r.append(
					_("{0} against Purchase Order {1}").format(
						fmt_money(flt(d.credit), currency=self.company_currency), d.reference_name
					)
				)

		if r:
			self.remark = ("\n").join(r)  # User Remarks is not mandatory

	def set_print_format_fields(self):
		bank_amount = party_amount = total_amount = 0.0
		currency = bank_account_currency = party_account_currency = pay_to_recd_from = None
		party_type = None
		for d in self.get("accounts"):
			if d.party_type in ["Customer", "Supplier"] and d.party:
				party_type = d.party_type
				if not pay_to_recd_from:
					pay_to_recd_from = d.party

				if pay_to_recd_from and pay_to_recd_from == d.party:
					party_amount += d.debit_in_account_currency or d.credit_in_account_currency
					party_account_currency = d.account_currency

			elif frappe.db.get_value("Account", d.account, "account_type") in ["Bank", "Cash"]:
				bank_amount += d.debit_in_account_currency or d.credit_in_account_currency
				bank_account_currency = d.account_currency

		if party_type and pay_to_recd_from:
			self.pay_to_recd_from = frappe.db.get_value(
				party_type, pay_to_recd_from, "customer_name" if party_type == "Customer" else "supplier_name"
			)
			if bank_amount:
				total_amount = bank_amount
				currency = bank_account_currency
			else:
				total_amount = party_amount
				currency = party_account_currency

		self.set_total_amount(total_amount, currency)

	def set_total_amount(self, amt, currency):
		self.total_amount = amt
		self.total_amount_currency = currency
		from frappe.utils import money_in_words

		self.total_amount_in_words = money_in_words(amt, currency)

	def build_gl_map(self):
		gl_map = []
		for d in self.get("accounts"):
			if d.debit or d.credit:
				r = [d.user_remark, self.remark]
				r = [x for x in r if x]
				remarks = "\n".join(r)

				gl_map.append(
					self.get_gl_dict(
						{
							"account": d.account,
							"party_type": d.party_type,
							"due_date": self.due_date,
							"party": d.party,
							"against": d.against_account,
							"debit": flt(d.debit, d.precision("debit")),
							"credit": flt(d.credit, d.precision("credit")),
							"account_currency": d.account_currency,
							"debit_in_account_currency": flt(
								d.debit_in_account_currency, d.precision("debit_in_account_currency")
							),
							"credit_in_account_currency": flt(
								d.credit_in_account_currency, d.precision("credit_in_account_currency")
							),
							"against_voucher_type": d.reference_type,
							"against_voucher": d.reference_name,
							"remarks": remarks,
							"voucher_detail_no": d.reference_detail_no,
							"cost_center": d.cost_center,
							"project": d.project,
							"finance_book": self.finance_book,
						},
						item=d,
					)
				)
		return gl_map

	def make_gl_entries(self, cancel=0, adv_adj=0):
		from erpnext.accounts.general_ledger import make_gl_entries

		gl_map = self.build_gl_map()
		if self.voucher_type in ("Deferred Revenue", "Deferred Expense"):
			update_outstanding = "No"
		else:
			update_outstanding = "Yes"

		if gl_map:
			make_gl_entries(gl_map, cancel=cancel, adv_adj=adv_adj, update_outstanding=update_outstanding)

	@frappe.whitelist()
	def get_balance(self):
		if not self.get("accounts"):
			msgprint(_("'Entries' cannot be empty"), raise_exception=True)
		else:
			self.total_debit, self.total_credit = 0, 0
			diff = flt(self.difference, self.precision("difference"))

			# If any row without amount, set the diff on that row
			if diff:
				blank_row = None
				for d in self.get("accounts"):
					if not d.credit_in_account_currency and not d.debit_in_account_currency and diff != 0:
						blank_row = d

				if not blank_row:
					blank_row = self.append("accounts", {})

				blank_row.exchange_rate = 1
				if diff > 0:
					blank_row.credit_in_account_currency = diff
					blank_row.credit = diff
				elif diff < 0:
					blank_row.debit_in_account_currency = abs(diff)
					blank_row.debit = abs(diff)

			self.validate_total_debit_and_credit()

	@frappe.whitelist()
	def get_outstanding_invoices(self):
		self.set("accounts", [])
		total = 0
		for d in self.get_values():
			total += flt(d.outstanding_amount, self.precision("credit", "accounts"))
			jd1 = self.append("accounts", {})
			jd1.account = d.account
			jd1.party = d.party

			if self.write_off_based_on == "Accounts Receivable":
				jd1.party_type = "Customer"
				jd1.credit_in_account_currency = flt(
					d.outstanding_amount, self.precision("credit", "accounts")
				)
				jd1.reference_type = "Sales Invoice"
				jd1.reference_name = cstr(d.name)
			elif self.write_off_based_on == "Accounts Payable":
				jd1.party_type = "Supplier"
				jd1.debit_in_account_currency = flt(d.outstanding_amount, self.precision("debit", "accounts"))
				jd1.reference_type = "Purchase Invoice"
				jd1.reference_name = cstr(d.name)

		jd2 = self.append("accounts", {})
		if self.write_off_based_on == "Accounts Receivable":
			jd2.debit_in_account_currency = total
		elif self.write_off_based_on == "Accounts Payable":
			jd2.credit_in_account_currency = total

		self.validate_total_debit_and_credit()

	def get_values(self):
		cond = (
			" and outstanding_amount <= {0}".format(self.write_off_amount)
			if flt(self.write_off_amount) > 0
			else ""
		)

		if self.write_off_based_on == "Accounts Receivable":
			return frappe.db.sql(
				"""select name, debit_to as account, customer as party, outstanding_amount
				from `tabSales Invoice` where docstatus = 1 and company = %s
				and outstanding_amount > 0 %s"""
				% ("%s", cond),
				self.company,
				as_dict=True,
			)
		elif self.write_off_based_on == "Accounts Payable":
			return frappe.db.sql(
				"""select name, credit_to as account, supplier as party, outstanding_amount
				from `tabPurchase Invoice` where docstatus = 1 and company = %s
				and outstanding_amount > 0 %s"""
				% ("%s", cond),
				self.company,
				as_dict=True,
			)

	def validate_credit_debit_note(self):
		if self.stock_entry:
			if frappe.db.get_value("Stock Entry", self.stock_entry, "docstatus") != 1:
				frappe.throw(_("Stock Entry {0} is not submitted").format(self.stock_entry))

			if frappe.db.exists(
				{"doctype": "Journal Entry", "stock_entry": self.stock_entry, "docstatus": 1}
			):
				frappe.msgprint(
					_("Warning: Another {0} # {1} exists against stock entry {2}").format(
						self.voucher_type, self.name, self.stock_entry
					)
				)

	def validate_empty_accounts_table(self):
		if not self.get("accounts"):
			frappe.throw(_("Accounts table cannot be blank."))

	def set_account_and_party_balance(self):
		account_balance = {}
		party_balance = {}
		for d in self.get("accounts"):
			if d.account not in account_balance:
				account_balance[d.account] = get_balance_on(account=d.account, date=self.posting_date)

			if (d.party_type, d.party) not in party_balance:
				party_balance[(d.party_type, d.party)] = get_balance_on(
					party_type=d.party_type, party=d.party, date=self.posting_date, company=self.company
				)

			d.account_balance = account_balance[d.account]
			d.party_balance = party_balance[(d.party_type, d.party)]


@frappe.whitelist()
def get_default_bank_cash_account(company, account_type=None, mode_of_payment=None, account=None):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account

	if mode_of_payment:
		account = get_bank_cash_account(mode_of_payment, company).get("account")

	if not account:
		"""
		Set the default account first. If the user hasn't set any default account then, he doesn't
		want us to set any random account. In this case set the account only if there is single
		account (of that type), otherwise return empty dict.
		"""
		if account_type == "Bank":
			account = frappe.get_cached_value("Company", company, "default_bank_account")
			if not account:
				account_list = frappe.get_all(
					"Account", filters={"company": company, "account_type": "Bank", "is_group": 0}
				)
				if len(account_list) == 1:
					account = account_list[0].name

		elif account_type == "Cash":
			account = frappe.get_cached_value("Company", company, "default_cash_account")
			if not account:
				account_list = frappe.get_all(
					"Account", filters={"company": company, "account_type": "Cash", "is_group": 0}
				)
				if len(account_list) == 1:
					account = account_list[0].name

	if account:
		account_details = frappe.db.get_value(
			"Account", account, ["account_currency", "account_type"], as_dict=1
		)

		return frappe._dict(
			{
				"account": account,
				"balance": get_balance_on(account),
				"account_currency": account_details.account_currency,
				"account_type": account_details.account_type,
			}
		)
	else:
		return frappe._dict()


@frappe.whitelist()
def get_payment_entry_against_order(
	dt, dn, amount=None, debit_in_account_currency=None, journal_entry=False, bank_account=None
):
	ref_doc = frappe.get_doc(dt, dn)

	if flt(ref_doc.per_billed, 2) > 0:
		frappe.throw(_("Can only make payment against unbilled {0}").format(dt))

	if dt == "Sales Order":
		party_type = "Customer"
		amount_field_party = "credit_in_account_currency"
		amount_field_bank = "debit_in_account_currency"
	else:
		party_type = "Supplier"
		amount_field_party = "debit_in_account_currency"
		amount_field_bank = "credit_in_account_currency"

	party_account = get_party_account(party_type, ref_doc.get(party_type.lower()), ref_doc.company)
	party_account_currency = get_account_currency(party_account)

	if not amount:
		if party_account_currency == ref_doc.company_currency:
			amount = flt(ref_doc.base_grand_total) - flt(ref_doc.advance_paid)
		else:
			amount = flt(ref_doc.grand_total) - flt(ref_doc.advance_paid)

	return get_payment_entry(
		ref_doc,
		{
			"party_type": party_type,
			"party_account": party_account,
			"party_account_currency": party_account_currency,
			"amount_field_party": amount_field_party,
			"amount_field_bank": amount_field_bank,
			"amount": amount,
			"debit_in_account_currency": debit_in_account_currency,
			"remarks": "Advance Payment received against {0} {1}".format(dt, dn),
			"is_advance": "Yes",
			"bank_account": bank_account,
			"journal_entry": journal_entry,
		},
	)


@frappe.whitelist()
def get_payment_entry_against_invoice(
	dt, dn, amount=None, debit_in_account_currency=None, journal_entry=False, bank_account=None
):
	ref_doc = frappe.get_doc(dt, dn)
	if dt == "Sales Invoice":
		party_type = "Customer"
		party_account = get_party_account_based_on_invoice_discounting(dn) or ref_doc.debit_to
	else:
		party_type = "Supplier"
		party_account = ref_doc.credit_to

	if (dt == "Sales Invoice" and ref_doc.outstanding_amount > 0) or (
		dt == "Purchase Invoice" and ref_doc.outstanding_amount < 0
	):
		amount_field_party = "credit_in_account_currency"
		amount_field_bank = "debit_in_account_currency"
	else:
		amount_field_party = "debit_in_account_currency"
		amount_field_bank = "credit_in_account_currency"

	return get_payment_entry(
		ref_doc,
		{
			"party_type": party_type,
			"party_account": party_account,
			"party_account_currency": ref_doc.party_account_currency,
			"amount_field_party": amount_field_party,
			"amount_field_bank": amount_field_bank,
			"amount": amount if amount else abs(ref_doc.outstanding_amount),
			"debit_in_account_currency": debit_in_account_currency,
			"remarks": "Payment received against {0} {1}. {2}".format(dt, dn, ref_doc.remarks),
			"is_advance": "No",
			"bank_account": bank_account,
			"journal_entry": journal_entry,
		},
	)


def get_payment_entry(ref_doc, args):
	cost_center = ref_doc.get("cost_center") or frappe.get_cached_value(
		"Company", ref_doc.company, "cost_center"
	)
	exchange_rate = 1
	if args.get("party_account"):
		# Modified to include the posting date for which the exchange rate is required.
		# Assumed to be the posting date in the reference document
		exchange_rate = get_exchange_rate(
			ref_doc.get("posting_date") or ref_doc.get("transaction_date"),
			args.get("party_account"),
			args.get("party_account_currency"),
			ref_doc.company,
			ref_doc.doctype,
			ref_doc.name,
		)

	je = frappe.new_doc("Journal Entry")
	je.update(
		{"voucher_type": "Bank Entry", "company": ref_doc.company, "remark": args.get("remarks")}
	)

	party_row = je.append(
		"accounts",
		{
			"account": args.get("party_account"),
			"party_type": args.get("party_type"),
			"party": ref_doc.get(args.get("party_type").lower()),
			"cost_center": cost_center,
			"account_type": frappe.db.get_value("Account", args.get("party_account"), "account_type"),
			"account_currency": args.get("party_account_currency")
			or get_account_currency(args.get("party_account")),
			"balance": get_balance_on(args.get("party_account")),
			"party_balance": get_balance_on(party=args.get("party"), party_type=args.get("party_type")),
			"exchange_rate": exchange_rate,
			args.get("amount_field_party"): args.get("amount"),
			"is_advance": args.get("is_advance"),
			"reference_type": ref_doc.doctype,
			"reference_name": ref_doc.name,
		},
	)

	bank_row = je.append("accounts")

	# Make it bank_details
	bank_account = get_default_bank_cash_account(
		ref_doc.company, "Bank", account=args.get("bank_account")
	)
	if bank_account:
		bank_row.update(bank_account)
		# Modified to include the posting date for which the exchange rate is required.
		# Assumed to be the posting date of the reference date
		bank_row.exchange_rate = get_exchange_rate(
			ref_doc.get("posting_date") or ref_doc.get("transaction_date"),
			bank_account["account"],
			bank_account["account_currency"],
			ref_doc.company,
		)

	bank_row.cost_center = cost_center

	amount = args.get("debit_in_account_currency") or args.get("amount")

	if bank_row.account_currency == args.get("party_account_currency"):
		bank_row.set(args.get("amount_field_bank"), amount)
	else:
		bank_row.set(args.get("amount_field_bank"), amount * exchange_rate)

	# Multi currency check again
	if party_row.account_currency != ref_doc.company_currency or (
		bank_row.account_currency and bank_row.account_currency != ref_doc.company_currency
	):
		je.multi_currency = 1

	je.set_amounts_in_company_currency()
	je.set_total_debit_credit()

	return je if args.get("journal_entry") else je.as_dict()


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_against_jv(doctype, txt, searchfield, start, page_len, filters):
	if not frappe.db.has_column("Journal Entry", searchfield):
		return []

	return frappe.db.sql(
		"""
		SELECT jv.name, jv.posting_date, jv.user_remark
		FROM `tabJournal Entry` jv, `tabJournal Entry Account` jv_detail
		WHERE jv_detail.parent = jv.name
			AND jv_detail.account = %(account)s
			AND IFNULL(jv_detail.party, '') = %(party)s
			AND (
				jv_detail.reference_type IS NULL
				OR jv_detail.reference_type = ''
			)
			AND jv.docstatus = 1
			AND jv.`{0}` LIKE %(txt)s
		ORDER BY jv.name DESC
		LIMIT %(limit)s offset %(offset)s
		""".format(
			searchfield
		),
		dict(
			account=filters.get("account"),
			party=cstr(filters.get("party")),
			txt="%{0}%".format(txt),
			offset=start,
			limit=page_len,
		),
	)


@frappe.whitelist()
def get_outstanding(args):
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	if isinstance(args, str):
		args = json.loads(args)

	company_currency = erpnext.get_company_currency(args.get("company"))
	due_date = None

	if args.get("doctype") == "Journal Entry":
		condition = " and party=%(party)s" if args.get("party") else ""

		against_jv_amount = frappe.db.sql(
			"""
			select sum(debit_in_account_currency) - sum(credit_in_account_currency)
			from `tabJournal Entry Account` where parent=%(docname)s and account=%(account)s {0}
			and (reference_type is null or reference_type = '')""".format(
				condition
			),
			args,
		)

		against_jv_amount = flt(against_jv_amount[0][0]) if against_jv_amount else 0
		amount_field = (
			"credit_in_account_currency" if against_jv_amount > 0 else "debit_in_account_currency"
		)
		return {amount_field: abs(against_jv_amount)}
	elif args.get("doctype") in ("Sales Invoice", "Purchase Invoice"):
		party_type = "Customer" if args.get("doctype") == "Sales Invoice" else "Supplier"
		invoice = frappe.db.get_value(
			args["doctype"],
			args["docname"],
			["outstanding_amount", "conversion_rate", scrub(party_type), "due_date"],
			as_dict=1,
		)

		due_date = invoice.get("due_date")

		exchange_rate = (
			invoice.conversion_rate if (args.get("account_currency") != company_currency) else 1
		)

		if args["doctype"] == "Sales Invoice":
			amount_field = (
				"credit_in_account_currency"
				if flt(invoice.outstanding_amount) > 0
				else "debit_in_account_currency"
			)
		else:
			amount_field = (
				"debit_in_account_currency"
				if flt(invoice.outstanding_amount) > 0
				else "credit_in_account_currency"
			)

		return {
			amount_field: abs(flt(invoice.outstanding_amount)),
			"exchange_rate": exchange_rate,
			"party_type": party_type,
			"party": invoice.get(scrub(party_type)),
			"reference_due_date": due_date,
		}


@frappe.whitelist()
def get_party_account_and_balance(company, party_type, party, cost_center=None):
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	account = get_party_account(party_type, party, company)

	account_balance = get_balance_on(account=account, cost_center=cost_center)
	party_balance = get_balance_on(
		party_type=party_type, party=party, company=company, cost_center=cost_center
	)

	return {
		"account": account,
		"balance": account_balance,
		"party_balance": party_balance,
		"account_currency": frappe.db.get_value("Account", account, "account_currency"),
	}


@frappe.whitelist()
def get_account_balance_and_party_type(
	account, date, company, debit=None, credit=None, exchange_rate=None, cost_center=None
):
	"""Returns dict of account balance and party type to be set in Journal Entry on selection of account."""
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	company_currency = erpnext.get_company_currency(company)
	account_details = frappe.db.get_value(
		"Account", account, ["account_type", "account_currency"], as_dict=1
	)

	if not account_details:
		return

	if account_details.account_type == "Receivable":
		party_type = "Customer"
	elif account_details.account_type == "Payable":
		party_type = "Supplier"
	else:
		party_type = ""

	grid_values = {
		"balance": get_balance_on(account, date, cost_center=cost_center),
		"party_type": party_type,
		"account_type": account_details.account_type,
		"account_currency": account_details.account_currency or company_currency,
		# The date used to retreive the exchange rate here is the date passed in
		# as an argument to this function. It is assumed to be the date on which the balance is sought
		"exchange_rate": get_exchange_rate(
			date,
			account,
			account_details.account_currency,
			company,
			debit=debit,
			credit=credit,
			exchange_rate=exchange_rate,
		),
	}

	# un-set party if not party type
	if not party_type:
		grid_values["party"] = ""

	return grid_values


@frappe.whitelist()
def get_exchange_rate(
	posting_date,
	account=None,
	account_currency=None,
	company=None,
	reference_type=None,
	reference_name=None,
	debit=None,
	credit=None,
	exchange_rate=None,
):
	from erpnext.setup.utils import get_exchange_rate

	account_details = frappe.db.get_value(
		"Account", account, ["account_type", "root_type", "account_currency", "company"], as_dict=1
	)

	if not account_details:
		frappe.throw(_("Please select correct account"))

	if not company:
		company = account_details.company

	if not account_currency:
		account_currency = account_details.account_currency

	company_currency = erpnext.get_company_currency(company)

	if account_currency != company_currency:
		if reference_type in ("Sales Invoice", "Purchase Invoice") and reference_name:
			exchange_rate = frappe.db.get_value(reference_type, reference_name, "conversion_rate")

		# The date used to retreive the exchange rate here is the date passed
		# in as an argument to this function.
		elif (not exchange_rate or flt(exchange_rate) == 1) and account_currency and posting_date:
			exchange_rate = get_exchange_rate(account_currency, company_currency, posting_date)
	else:
		exchange_rate = 1

	# don't return None or 0 as it is multipled with a value and that value could be lost
	return exchange_rate or 1


@frappe.whitelist()
def get_average_exchange_rate(account):
	exchange_rate = 0
	bank_balance_in_account_currency = get_balance_on(account)
	if bank_balance_in_account_currency:
		bank_balance_in_company_currency = get_balance_on(account, in_account_currency=False)
		exchange_rate = bank_balance_in_company_currency / bank_balance_in_account_currency

	return exchange_rate


@frappe.whitelist()
def make_inter_company_journal_entry(name, voucher_type, company):
	journal_entry = frappe.new_doc("Journal Entry")
	journal_entry.voucher_type = voucher_type
	journal_entry.company = company
	journal_entry.posting_date = nowdate()
	journal_entry.inter_company_journal_entry_reference = name
	return journal_entry.as_dict()


@frappe.whitelist()
def make_reverse_journal_entry(source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc

	def post_process(source, target):
		target.reversal_of = source.name

	doclist = get_mapped_doc(
		"Journal Entry",
		source_name,
		{
			"Journal Entry": {"doctype": "Journal Entry", "validation": {"docstatus": ["=", 1]}},
			"Journal Entry Account": {
				"doctype": "Journal Entry Account",
				"field_map": {
					"account_currency": "account_currency",
					"exchange_rate": "exchange_rate",
					"debit_in_account_currency": "credit_in_account_currency",
					"debit": "credit",
					"credit_in_account_currency": "debit_in_account_currency",
					"credit": "debit",
				},
			},
		},
		target_doc,
		post_process,
	)

	return doclist
