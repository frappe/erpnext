# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext, json
from frappe.utils import cstr, flt, fmt_money, formatdate, getdate, nowdate, cint
from frappe import msgprint, _, scrub
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.utils import get_balance_on, get_balance_on_voucher, get_account_currency
from erpnext.accounts.party import get_party_account
from erpnext.hr.doctype.expense_claim.expense_claim import update_reimbursed_amount
from erpnext.hr.doctype.loan.loan import update_disbursement_status, update_total_amount_paid

from six import string_types, iteritems

class JournalEntry(AccountsController):
	def __init__(self, *args, **kwargs):
		super(JournalEntry, self).__init__(*args, **kwargs)

	def get_feed(self):
		return self.voucher_type

	def validate(self):
		if not self.is_opening:
			self.is_opening='No'

		for d in self.accounts:
			d.clearance_date = None

		self.validate_party()
		self.validate_order_entries()
		self.validate_multi_currency()
		self.set_amounts_in_company_currency()
		self.validate_total_debit_and_credit()
		self.validate_reference_doc()
		self.set_against_account()
		self.set_print_format_fields()
		self.validate_expense_claim()
		self.validate_credit_debit_note()
		self.validate_empty_accounts_table()
		self.set_account_and_party_balance()
		self.validate_inter_company_accounts()

		if not self.title:
			self.title = self.get_title()

	def before_submit(self):
		self.validate_cheque_info()
		self.create_remarks()

	def on_submit(self):
		self.check_credit_limit()
		self.make_gl_entries()
		self.update_advance_paid()
		self.update_expense_claim()
		self.update_loan()
		self.update_inter_company_jv()

	def get_title(self):
		return self.pay_to_recd_from or self.accounts[0].account

	def update_advance_paid(self):
		advance_paid = frappe._dict()
		for d in self.get("accounts"):
			if d.reference_type in ("Sales Order", "Purchase Order", "Employee Advance"):
				advance_paid.setdefault(d.reference_type, []).append(d.reference_name)

		for voucher_type, order_list in iteritems(advance_paid):
			for voucher_no in list(set(order_list)):
				frappe.get_doc(voucher_type, voucher_no).set_total_advance_paid()

	def validate_inter_company_accounts(self):
		if self.voucher_type == "Inter Company Journal Entry" and self.inter_company_journal_entry_reference:
			doc = frappe.get_doc("Journal Entry", self.inter_company_journal_entry_reference)
			account_currency = frappe.get_cached_value('Company',  self.company,  "default_currency")
			previous_account_currency = frappe.get_cached_value('Company',  doc.company,  "default_currency")
			if account_currency == previous_account_currency:
				if self.total_credit != doc.total_debit or self.total_debit != doc.total_credit:
					frappe.throw(_("Total Credit/ Debit Amount should be same as linked Journal Entry"))

	def update_inter_company_jv(self):
		if self.voucher_type == "Inter Company Journal Entry" and self.inter_company_journal_entry_reference:
			frappe.db.set_value("Journal Entry", self.inter_company_journal_entry_reference,\
				"inter_company_journal_entry_reference", self.name)

	def on_cancel(self):
		from erpnext.accounts.utils import unlink_ref_doc_from_payment_entries
		from erpnext.hr.doctype.salary_slip.salary_slip import unlink_ref_doc_from_salary_slip
		unlink_ref_doc_from_payment_entries(self)
		unlink_ref_doc_from_salary_slip(self.name)
		self.make_gl_entries(1)
		self.update_advance_paid()
		self.update_expense_claim()
		self.update_loan()
		self.unlink_advance_entry_reference()
		self.unlink_asset_reference()
		self.unlink_inter_company_jv()
		self.unlink_asset_adjustment_entry()

	def unlink_advance_entry_reference(self):
		for d in self.get("accounts"):
			if d.reference_type in ("Sales Invoice", "Purchase Invoice", "Landed Cost Voucher"):
				doc = frappe.get_doc(d.reference_type, d.reference_name)
				doc.delink_advance_entries(self.name)

	def unlink_asset_reference(self):
		for d in self.get("accounts"):
			if d.reference_type=="Asset" and d.reference_name:
				asset = frappe.get_doc("Asset", d.reference_name)
				for s in asset.get("schedules"):
					if s.journal_entry == self.name:
						s.db_set("journal_entry", None)

						idx = cint(s.finance_book_id) or 1
						finance_books = asset.get('finance_books')[idx - 1]
						finance_books.value_after_depreciation += s.depreciation_amount
						finance_books.db_update()

						asset.set_status()

	def unlink_inter_company_jv(self):
		if self.voucher_type == "Inter Company Journal Entry" and self.inter_company_journal_entry_reference:
			frappe.db.set_value("Journal Entry", self.inter_company_journal_entry_reference,\
				"inter_company_journal_entry_reference", "")
			frappe.db.set_value("Journal Entry", self.name,\
				"inter_company_journal_entry_reference", "")

	def unlink_asset_adjustment_entry(self):
		frappe.db.sql(""" update `tabAsset Value Adjustment`
			set journal_entry = null where journal_entry = %s""", self.name)

	def validate_party(self):
		for d in self.get("accounts"):
			account_type = frappe.db.get_value("Account", d.account, "account_type")
			if account_type in ["Receivable", "Payable"]:
				if not (d.party_type and d.party):
					frappe.throw(_("Row {0}: Party Type and Party is required for Receivable / Payable account {1}").format(d.idx, d.account))

	def check_credit_limit(self):
		customers = list(set([d.party for d in self.get("accounts")
			if d.party_type=="Customer" and d.party and flt(d.debit) > 0]))
		if customers:
			from erpnext.selling.doctype.customer.customer import check_credit_limit
			for customer in customers:
				check_credit_limit(customer, self.company)

	def validate_cheque_info(self):
		for row in self.accounts:
			if not row.cheque_no:
				row.cheque_no = self.cheque_no
			if not row.cheque_date:
				row.cheque_date = self.cheque_date

			account_type = frappe.get_cached_value("Account", row.account, "account_type")
			if account_type == "Bank" and self.voucher_type in ['Bank Entry'] and (not row.cheque_no or not row.cheque_date):
				frappe.throw(_("Row #{0}: Reference No & Reference Date is required for {1}").format(row.idx, self.voucher_type))

			if row.cheque_date and not row.cheque_no:
				frappe.throw(_("Row #{0}: Reference No is mandatory if you entered Reference Date").format(row.idx))

	def validate_order_entries(self):
		for d in self.get('accounts'):
			if d.reference_type == "Sales Order" and flt(d.debit) > 0:
				frappe.throw(_("Row {0}: Advance against Sales Order must be credit").format(d.idx))
			if d.reference_type == "Purchase Order" and flt(d.credit) > 0:
				frappe.throw(_("Row {0}: Advance against Purchase Order must be debit").format(d.idx))

	def validate_against_jv(self, d):
		if d.reference_name == self.name:
			frappe.throw(_("You can not enter current voucher in 'Against Journal Entry' column"))

		against_entries = frappe.db.sql("""select debit, credit from `tabJournal Entry Account`
			where account = %s and docstatus = 1 and parent = %s and (reference_type is null or reference_type = '')
			""", (d.account, d.reference_name), as_dict=True)

		if not against_entries:
			frappe.throw(_("Row {0}: Journal Entry {1} does not have account {2} or is already matched against a voucher")
				.format(d.idx, d.reference_name, d.account))
		else:
			dr_or_cr = "debit" if d.credit > 0 else "credit"
			valid = False
			for jvd in against_entries:
				if flt(jvd[dr_or_cr]) > 0:
					valid = True
			if not valid:
				frappe.throw(_("Row {0}: Against Journal Entry {1} does not have any unmatched {2} entry")
					.format(d.idx, d.reference_name, dr_or_cr))

		if d.party and d.party_type:
			acc_tuple = (d.account, d.party_type, d.party)
			if d.reference_name not in self.jv_party_references:
				self.jv_party_references[d.reference_name] = {}
			if acc_tuple not in self.jv_party_references[d.reference_name]:
				self.jv_party_references[d.reference_name][acc_tuple] = 0.0

			self.jv_party_references[d.reference_name][acc_tuple] += d.debit_in_account_currency - d.credit_in_account_currency

	def validate_reference_doc(self):
		"""Validates reference document"""
		field_dict = {
			'Sales Invoice': ["Customer", "Debit To"],
			'Purchase Invoice': ["Supplier", "Credit To", "Letter of Credit"],
			'Sales Order': ["Customer"],
			'Purchase Order': ["Supplier"]
		}

		self.reference_totals = {}
		self.reference_types = {}
		self.reference_accounts = {}
		self.jv_party_references = {}

		for d in self.get("accounts"):
			if not d.reference_type:
				d.reference_name = None
			if not d.reference_name:
				d.reference_type = None
			if d.reference_type and d.reference_name:
				if d.reference_type in list(field_dict):
					dr_or_cr = "credit_in_account_currency" \
						if d.reference_type in ("Sales Order", "Sales Invoice") else "debit_in_account_currency"

					# check debit or credit type Sales / Purchase Order
					if d.reference_type=="Sales Order" and flt(d.debit) > 0:
						frappe.throw(_("Row {0}: Debit entry can not be linked with a {1}").format(d.idx, d.reference_type))

					if d.reference_type == "Purchase Order" and flt(d.credit) > 0:
						frappe.throw(_("Row {0}: Credit entry can not be linked with a {1}").format(d.idx, d.reference_type))

					# set totals
					if not d.reference_name in self.reference_totals:
						self.reference_totals[d.reference_name] = 0.0
					self.reference_totals[d.reference_name] += flt(d.get(dr_or_cr))
					self.reference_types[d.reference_name] = d.reference_type
					self.reference_accounts[d.reference_name] = d.account

					against_voucher = frappe.db.get_value(d.reference_type, d.reference_name,
						[scrub(dt) for dt in field_dict.get(d.reference_type)])

					if not against_voucher:
						frappe.throw(_("Row {0}: Invalid reference {1}").format(d.idx, d.reference_name))

					# check if party and account match
					if d.reference_type in ("Sales Invoice", "Purchase Invoice"):
						if d.reference_type == "Sales Invoice":
							billing_party, account = against_voucher
							billing_party_type, account_field = field_dict.get(d.reference_type)
						else:
							billing_party = against_voucher[2] if against_voucher[2] else against_voucher[0]
							account = against_voucher[1]
							billing_party_type = field_dict.get(d.reference_type)[2] if against_voucher[2] else field_dict.get(d.reference_type)[0]
							account_field = field_dict.get(d.reference_type)[1]

						if billing_party != d.party or billing_party_type != d.party_type or account != d.account:
							frappe.throw(_("Row {0}: Party / Account does not match with {1} / {2} in {3} {4}")
								.format(d.idx, billing_party_type, account_field, d.reference_type, d.reference_name))

					# check if party matches for Sales / Purchase Order
					elif d.reference_type in ("Sales Order", "Purchase Order"):
						# set totals
						if against_voucher != d.party:
							frappe.throw(_("Row {0}: {1} {2} does not match with {3}") \
								.format(d.idx, d.party_type, d.party, d.reference_type))

				elif d.reference_type == "Journal Entry":
					self.validate_against_jv(d)

		self.validate_orders()
		self.validate_invoices()
		self.validate_jv_party_references()

	def validate_orders(self):
		"""Validate totals, closed and docstatus for orders"""
		for reference_name, total in iteritems(self.reference_totals):
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
					formatted_voucher_total = fmt_money(voucher_total, order.precision("base_grand_total"),
						currency=account_currency)
				else:
					voucher_total = order.grand_total
					formatted_voucher_total = fmt_money(voucher_total, order.precision("grand_total"),
						currency=account_currency)

				if flt(voucher_total) < (flt(order.advance_paid) + total):
					frappe.throw(_("Advance paid against {0} {1} cannot be greater \
						than Grand Total {2}").format(reference_type, reference_name, formatted_voucher_total))

	def validate_invoices(self):
		"""Validate totals and docstatus for invoices"""
		for reference_name, total in iteritems(self.reference_totals):
			reference_type = self.reference_types[reference_name]

			if reference_type in ("Sales Invoice", "Purchase Invoice"):
				invoice = frappe.db.get_value(reference_type, reference_name,
					["docstatus", "outstanding_amount"], as_dict=1)

				if invoice.docstatus != 1:
					frappe.throw(_("{0} {1} is not submitted").format(reference_type, reference_name))

				if total and flt(invoice.outstanding_amount) < total:
					frappe.throw(_("Payment against {0} {1} cannot be greater than Outstanding Amount {2}")
						.format(reference_type, reference_name, invoice.outstanding_amount))

	def validate_jv_party_references(self):
		for reference_name, acc_amounts in iteritems(self.jv_party_references):
			for (account, party_type, party), amount in iteritems(acc_amounts):
				if amount == 0:
					continue

				if amount > 0:
					bal_dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
					dr_or_cr = "credit"
				else:
					bal_dr_or_cr = "debit_in_account_currency - credit_in_account_currency"
					dr_or_cr = "debit"

				jv_balance = get_balance_on_voucher("Journal Entry", reference_name, party_type, party, account, bal_dr_or_cr)
				if jv_balance <= 0:
					frappe.throw(_("Journal Entry {0} does not have any {1} outstanding balance for party {2}")
						.format(reference_name, dr_or_cr, party))
				else:
					amount = abs(amount)
					if amount > jv_balance:
						frappe.throw(_("Referenced amount {0} to Journal Entry {1} for party {2} is greater than the outstanding balance {3}")
							.format(amount, reference_name, party, jv_balance))


	def set_against_account(self):
		accounts_debited, accounts_credited = [], []
		for d in self.get("accounts"):
			if flt(d.debit > 0): accounts_debited.append(d.party or d.account)
			if flt(d.credit) > 0: accounts_credited.append(d.party or d.account)

		for d in self.get("accounts"):
			if flt(d.debit > 0): d.against_account = ", ".join(list(set(accounts_credited)))
			if flt(d.credit > 0): d.against_account = ", ".join(list(set(accounts_debited)))

	def validate_total_debit_and_credit(self):
		self.set_total_debit_credit()
		if self.difference:
			frappe.throw(_("Total Debit must be equal to Total Credit. The difference is {0}")
				.format(self.difference))

	def set_total_debit_credit(self):
		self.total_debit, self.total_credit, self.difference = 0, 0, 0
		for d in self.get("accounts"):
			if d.debit and d.credit:
				frappe.throw(_("You cannot credit and debit same account at the same time"))

			self.total_debit = flt(self.total_debit) + flt(d.debit, d.precision("debit"))
			self.total_credit = flt(self.total_credit) + flt(d.credit, d.precision("credit"))

		self.difference = flt(self.total_debit, self.precision("total_debit")) - \
			flt(self.total_credit, self.precision("total_credit"))

	def validate_multi_currency(self):
		alternate_currency = []
		for d in self.get("accounts"):
			account = frappe.db.get_value("Account", d.account, ["account_currency", "account_type"], as_dict=1)
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
			d.debit_in_account_currency = flt(d.debit_in_account_currency, d.precision("debit_in_account_currency"))
			d.credit_in_account_currency = flt(d.credit_in_account_currency, d.precision("credit_in_account_currency"))

			d.debit = flt(d.debit_in_account_currency * flt(d.exchange_rate), d.precision("debit"))
			d.credit = flt(d.credit_in_account_currency * flt(d.exchange_rate), d.precision("credit"))

	def set_exchange_rate(self):
		for d in self.get("accounts"):
			if d.account_currency == self.company_currency:
				d.exchange_rate = 1
			elif not d.exchange_rate or d.exchange_rate == 1 \
				or (d.reference_type in ("Sales Invoice", "Purchase Invoice") and d.reference_name and self.posting_date) \
				or (d.reference_type == "Journal Entry" and d.reference_name and d.party_type and d.party and d.account):

					# Modified to include the posting date for which to retreive the exchange rate
					d.exchange_rate = get_exchange_rate(self.posting_date, d.account, d.account_currency,
						self.company, d.reference_type, d.reference_name, d.debit, d.credit, d.exchange_rate,
						d.party_type, d.party)

			if not d.exchange_rate:
				frappe.throw(_("Row {0}: Exchange Rate is mandatory").format(d.idx))

	def create_remarks(self):
		r = []

		if self.user_remark:
			r.append(_("Note: {0}").format(self.user_remark))

		if self.reference_account:
			r.append(_('Reference Account: {0}').format(self.reference_account))

		# Reference numbers string
		refs = set([d.cheque_no for d in self.accounts if d.cheque_no])
		self.reference_numbers = ", ".join(refs)

		# Reference number and dates string
		refs = set([(d.cheque_no, d.cheque_date) for d in self.accounts if d.cheque_no])
		ref_strs = []
		for ref in refs:
			if ref[0] and ref[1]:
				ref_strs.append(_("{0} dated {1}").format(ref[0], formatdate(ref[1])))
			else:
				ref_strs.append(ref[0])
		if ref_strs:
			r.append(_("Reference #: {0}").format(", ".join(ref_strs)))

		# Reference documents
		for d in self.get('accounts'):
			if d.reference_type=="Sales Invoice" and d.credit:
				r.append(_("{0} against Sales Invoice {1}").format(fmt_money(flt(d.credit), currency = self.company_currency), \
					d.reference_name))

			if d.reference_type=="Sales Order" and d.credit:
				r.append(_("{0} against Sales Order {1}").format(fmt_money(flt(d.credit), currency = self.company_currency), \
					d.reference_name))

			if d.reference_type == "Purchase Invoice" and d.debit:
				r.append(_("{0} against Purchase Invoice {1}").format(fmt_money(flt(d.debit), currency = self.company_currency), \
					d.reference_name))

				bill_no = frappe.db.sql("""select bill_no, bill_date from `tabPurchase Invoice` where name=%s""", d.reference_name)
				if bill_no and bill_no[0][0] and bill_no[0][0].lower().strip() not in ['na', 'not applicable', 'none']:
					r.append(_('{0} against Bill {1} dated {2}').format(fmt_money(flt(d.debit), currency=self.company_currency), \
						bill_no[0][0], bill_no[0][1] and formatdate(bill_no[0][1])))

			if d.reference_type == "Purchase Order" and d.debit:
				r.append(_("{0} against Purchase Order {1}").format(fmt_money(flt(d.debit), currency = self.company_currency), \
					d.reference_name))

		self.remark = "\n".join(r) if r else "" # User Remarks is not mandatory

	def set_print_format_fields(self):
		bank_amount = party_amount = total_amount = 0.0
		currency = bank_account_currency = party_account_currency = pay_to_recd_from= None
		for d in self.get('accounts'):
			if d.party_type in ['Customer', 'Supplier', 'Letter of Credit', 'Employee'] and d.party:
				if not pay_to_recd_from:
					if d.party_type == "Letter of Credit":
						name_field = "name"
					elif d.party_type == "Employee":
						name_field = "employee_name"
					else:
						name_field = "customer_name" if d.party_type=="Customer" else "supplier_name"
					pay_to_recd_from = frappe.db.get_value(d.party_type, d.party, name_field)

				party_amount += (d.debit_in_account_currency or d.credit_in_account_currency)
				party_account_currency = d.account_currency

			elif frappe.db.get_value("Account", d.account, "account_type") in ["Bank", "Cash"]:
				bank_amount += (d.debit_in_account_currency or d.credit_in_account_currency)
				bank_account_currency = d.account_currency

		if pay_to_recd_from:
			self.pay_to_recd_from = pay_to_recd_from
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

	def make_gl_entries(self, cancel=0, adv_adj=0):
		from erpnext.accounts.general_ledger import make_gl_entries

		gl_map = []
		for d in self.get("accounts"):
			if d.debit or d.credit:
				r = []
				if d.user_remark:
					r.append(d.user_remark)
				if self.user_remark:
					r.append(_("Note: {0}").format(self.user_remark))
				if self.reference_account:
					r.append(_('Reference Account: {0}').format(self.reference_account))
				remarks = "\n".join(r)

				gl_map.append(
					self.get_gl_dict({
						"account": d.account,
						"party_type": d.party_type,
						"party": d.party,
						"against": d.against_account,
						"debit": flt(d.debit, d.precision("debit")),
						"credit": flt(d.credit, d.precision("credit")),
						"account_currency": d.account_currency,
						"debit_in_account_currency": flt(d.debit_in_account_currency, d.precision("debit_in_account_currency")),
						"credit_in_account_currency": flt(d.credit_in_account_currency, d.precision("credit_in_account_currency")),
						"against_voucher_type": d.reference_type,
						"against_voucher": d.reference_name,
						"remarks": remarks,
						"reference_no": d.cheque_no,
						"reference_date": d.cheque_date,
						"cost_center": d.cost_center,
						"project": d.project,
						"finance_book": self.finance_book
					})
				)

		if gl_map:
			make_gl_entries(gl_map, cancel=cancel, adv_adj=adv_adj)

	def get_balance(self):
		if not self.get('accounts'):
			msgprint(_("'Entries' cannot be empty"), raise_exception=True)
		else:
			self.total_debit, self.total_credit = 0, 0
			diff = flt(self.difference, self.precision("difference"))

			# If any row without amount, set the diff on that row
			if diff:
				blank_row = None
				for d in self.get('accounts'):
					if not d.credit_in_account_currency and not d.debit_in_account_currency and diff != 0:
						blank_row = d

				if not blank_row:
					blank_row = self.append('accounts', {})

				blank_row.exchange_rate = 1
				if diff>0:
					blank_row.credit_in_account_currency = diff
					blank_row.credit = diff
				elif diff<0:
					blank_row.debit_in_account_currency = abs(diff)
					blank_row.debit = abs(diff)

			self.validate_total_debit_and_credit()

	def get_outstanding_invoices(self):
		self.set('accounts', [])
		total = 0
		for d in self.get_values():
			total += flt(d.outstanding_amount, self.precision("credit", "accounts"))
			jd1 = self.append('accounts', {})
			jd1.account = d.account
			jd1.party = d.party

			if self.write_off_based_on == 'Accounts Receivable':
				jd1.party_type = "Customer"
				jd1.credit = flt(d.outstanding_amount, self.precision("credit", "accounts"))
				jd1.reference_type = "Sales Invoice"
				jd1.reference_name = cstr(d.name)
			elif self.write_off_based_on == 'Accounts Payable':
				jd1.party_type = "Supplier"
				jd1.debit = flt(d.outstanding_amount, self.precision("debit", "accounts"))
				jd1.reference_type = "Purchase Invoice"
				jd1.reference_name = cstr(d.name)

		jd2 = self.append('accounts', {})
		if self.write_off_based_on == 'Accounts Receivable':
			jd2.debit = total
		elif self.write_off_based_on == 'Accounts Payable':
			jd2.credit = total

		self.validate_total_debit_and_credit()


	def get_values(self):
		cond = " and outstanding_amount <= {0}".format(self.write_off_amount) \
			if flt(self.write_off_amount) > 0 else ""

		if self.write_off_based_on == 'Accounts Receivable':
			return frappe.db.sql("""select name, debit_to as account, customer as party, outstanding_amount
				from `tabSales Invoice` where docstatus = 1 and company = %s
				and outstanding_amount > 0 %s""" % ('%s', cond), self.company, as_dict=True)
		elif self.write_off_based_on == 'Accounts Payable':
			return frappe.db.sql("""select name, credit_to as account, supplier as party, outstanding_amount
				from `tabPurchase Invoice` where docstatus = 1 and company = %s
				and outstanding_amount > 0 %s""" % ('%s', cond), self.company, as_dict=True)

	def update_expense_claim(self):
		for d in self.accounts:
			if d.reference_type=="Expense Claim" and d.reference_name:
				doc = frappe.get_doc("Expense Claim", d.reference_name)
				update_reimbursed_amount(doc)

	def update_loan(self):
		if self.paid_loan:
			paid_loan = json.loads(self.paid_loan)
			value = 1 if self.docstatus < 2 else 0
			for name in paid_loan:
				frappe.db.set_value("Repayment Schedule", name, "paid", value)
		for d in self.accounts:
			if d.reference_type=="Loan" and flt(d.debit) > 0:
				doc = frappe.get_doc("Loan", d.reference_name)
				update_disbursement_status(doc)
				update_total_amount_paid(doc)

	def validate_expense_claim(self):
		for d in self.accounts:
			if d.reference_type=="Expense Claim":
				sanctioned_amount, reimbursed_amount = frappe.db.get_value("Expense Claim",
					d.reference_name, ("total_sanctioned_amount", "total_amount_reimbursed"))
				pending_amount = flt(sanctioned_amount) - flt(reimbursed_amount)
				if d.debit > pending_amount:
					frappe.throw(_("Row No {0}: Amount cannot be greater than Pending Amount against Expense Claim {1}. Pending Amount is {2}".format(d.idx, d.reference_name, pending_amount)))

	def validate_credit_debit_note(self):
		if self.stock_entry:
			if frappe.db.get_value("Stock Entry", self.stock_entry, "docstatus") != 1:
				frappe.throw(_("Stock Entry {0} is not submitted").format(self.stock_entry))

			if frappe.db.exists({"doctype": "Journal Entry", "stock_entry": self.stock_entry, "docstatus":1}):
				frappe.msgprint(_("Warning: Another {0} # {1} exists against stock entry {2}".format(self.voucher_type, self.name, self.stock_entry)))

	def validate_empty_accounts_table(self):
		if not self.get('accounts'):
			frappe.throw(_("Accounts table cannot be blank."))

	def set_account_and_party_balance(self):
		account_balance = {}
		party_balance = {}
		for d in self.get("accounts"):
			if d.account not in account_balance:
				account_balance[d.account] = get_balance_on(account=d.account, date=self.posting_date)

			if (d.party_type, d.party) not in party_balance:
				party_balance[(d.party_type, d.party)] = get_balance_on(party_type=d.party_type,
					party=d.party, date=self.posting_date, company=self.company)

			d.account_balance = account_balance[d.account]
			d.party_balance = flt(party_balance[(d.party_type, d.party)])


@frappe.whitelist()
def get_default_bank_cash_account(company, account_type=None, mode_of_payment=None, account=None):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
	if mode_of_payment:
		account = get_bank_cash_account(mode_of_payment, company).get("account")

	if not account:
		'''
			Set the default account first. If the user hasn't set any default account then, he doesn't
			want us to set any random account. In this case set the account only if there is single
			account (of that type), otherwise return empty dict.
		'''
		if account_type=="Bank":
			account = frappe.get_cached_value('Company',  company,  "default_bank_account")
			if not account:
				account_list = frappe.get_all("Account", filters = {"company": company,
					"account_type": "Bank", "is_group": 0})
				if len(account_list) == 1:
					account = account_list[0].name

		elif account_type=="Cash":
			account = frappe.get_cached_value('Company',  company,  "default_cash_account")
			if not account:
				account_list = frappe.get_all("Account", filters = {"company": company,
					"account_type": "Cash", "is_group": 0})
				if len(account_list) == 1:
					account = account_list[0].name

	if account:
		account_details = frappe.db.get_value("Account", account,
			["account_currency", "account_type"], as_dict=1)

		return frappe._dict({
			"account": account,
			"balance": get_balance_on(account),
			"account_currency": account_details.account_currency,
			"account_type": account_details.account_type
		})
	else: return frappe._dict()

@frappe.whitelist()
def get_payment_entry_against_order(dt, dn, amount=None, debit_in_account_currency=None, journal_entry=False, bank_account=None):
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

	party_account = get_party_account(party_type, ref_doc.get(scrub(party_type)), ref_doc.company)
	party_account_currency = get_account_currency(party_account)

	if not amount:
		if party_account_currency == ref_doc.company_currency:
			amount = flt(ref_doc.base_grand_total) - flt(ref_doc.advance_paid)
		else:
			amount = flt(ref_doc.grand_total) - flt(ref_doc.advance_paid)

	return get_payment_entry(ref_doc, {
		"party_type": party_type,
		"party_account": party_account,
		"party_account_currency": party_account_currency,
		"amount_field_party": amount_field_party,
		"amount_field_bank": amount_field_bank,
		"amount": amount,
		"debit_in_account_currency": debit_in_account_currency,
		"remarks": 'Advance Payment received against {0} {1}'.format(dt, dn),
		"bank_account": bank_account,
		"journal_entry": journal_entry
	})

@frappe.whitelist()
def get_payment_entry_against_invoice(dt, dn, amount=None,  debit_in_account_currency=None, journal_entry=False, bank_account=None):
	ref_doc = frappe.get_doc(dt, dn)
	if dt == "Sales Invoice":
		party_type = "Customer"
		party_account = ref_doc.debit_to
	else:
		party_type = "Supplier" if not ref_doc.get("letter_of_credit") else "Letter of Credit"
		party_account = ref_doc.credit_to

	if (dt == "Sales Invoice" and ref_doc.outstanding_amount > 0) \
		or (dt == "Purchase Invoice" and ref_doc.outstanding_amount < 0):
			amount_field_party = "credit_in_account_currency"
			amount_field_bank = "debit_in_account_currency"
	else:
		amount_field_party = "debit_in_account_currency"
		amount_field_bank = "credit_in_account_currency"

	return get_payment_entry(ref_doc, {
		"party_type": party_type,
		"party_account": party_account,
		"party_account_currency": ref_doc.party_account_currency,
		"amount_field_party": amount_field_party,
		"amount_field_bank": amount_field_bank,
		"amount": amount if amount else abs(ref_doc.outstanding_amount),
		"debit_in_account_currency": debit_in_account_currency,
		"remarks": 'Payment received against {0} {1}. {2}'.format(dt, dn, ref_doc.remarks),
		"bank_account": bank_account,
		"journal_entry": journal_entry
	})


def get_payment_entry(ref_doc, args):
	cost_center = ref_doc.get("cost_center") or frappe.get_cached_value('Company',  ref_doc.company,  "cost_center")
	exchange_rate = 1
	if args.get("party_account"):
		# Modified to include the posting date for which the exchange rate is required.
		# Assumed to be the posting date in the reference document
		exchange_rate = get_exchange_rate(ref_doc.get("posting_date") or ref_doc.get("transaction_date"),
			args.get("party_account"), args.get("party_account_currency"),
			ref_doc.company, ref_doc.doctype, ref_doc.name)

	je = frappe.new_doc("Journal Entry")
	je.update({
		"voucher_type": "Bank Entry",
		"company": ref_doc.company,
		"remark": args.get("remarks")
	})

	party_row = je.append("accounts", {
		"account": args.get("party_account"),
		"party_type": args.get("party_type"),
		"party": ref_doc.get(scrub(args.get("party_type"))),
		"cost_center": cost_center,
		"account_type": frappe.db.get_value("Account", args.get("party_account"), "account_type"),
		"account_currency": args.get("party_account_currency") or \
							get_account_currency(args.get("party_account")),
		"balance": get_balance_on(args.get("party_account")),
		"party_balance": get_balance_on(party=args.get("party"), party_type=args.get("party_type")),
		"exchange_rate": exchange_rate,
		args.get("amount_field_party"): args.get("amount"),
		"reference_type": ref_doc.doctype,
		"reference_name": ref_doc.name
	})

	bank_row = je.append("accounts")

	# Make it bank_details
	bank_account = get_default_bank_cash_account(ref_doc.company, "Bank", account=args.get("bank_account"))
	if bank_account:
		bank_row.update(bank_account)
		# Modified to include the posting date for which the exchange rate is required.
		# Assumed to be the posting date of the reference date
		bank_row.exchange_rate = get_exchange_rate(ref_doc.get("posting_date")
			or ref_doc.get("transaction_date"), bank_account["account"],
			bank_account["account_currency"], ref_doc.company)

	bank_row.cost_center = cost_center

	amount = args.get("debit_in_account_currency") or args.get("amount")

	if bank_row.account_currency == args.get("party_account_currency"):
		bank_row.set(args.get("amount_field_bank"), amount)
	else:
		bank_row.set(args.get("amount_field_bank"), amount * exchange_rate)

	# Multi currency check again
	if party_row.account_currency != ref_doc.company_currency \
		or (bank_row.account_currency and bank_row.account_currency != ref_doc.company_currency):
			je.multi_currency = 1

	je.set_amounts_in_company_currency()
	je.set_total_debit_credit()

	return je if args.get("journal_entry") else je.as_dict()


@frappe.whitelist()
def get_opening_accounts(company):
	"""get all balance sheet accounts for opening entry"""
	accounts = frappe.db.sql_list("""select
			name from tabAccount
		where
			is_group=0 and report_type='Balance Sheet' and company=%s and
			name not in(select distinct account from tabWarehouse where
			account is not null and account != '')
		order by name asc""", frappe.db.escape(company))

	return [{"account": a, "balance": get_balance_on(a)} for a in accounts]

def get_outstanding_journal_entries(party_account, party_type, party):
	if erpnext.get_party_account_type(party_type) == "Receivable":
		bal_dr_or_cr = "gle_je.credit_in_account_currency - gle_je.debit_in_account_currency"
		payment_dr_or_cr = "gle_payment.debit_in_account_currency - gle_payment.credit_in_account_currency"
	else:
		bal_dr_or_cr = "gle_je.debit_in_account_currency - gle_je.credit_in_account_currency"
		payment_dr_or_cr = "gle_payment.credit_in_account_currency - gle_payment.debit_in_account_currency"

	return frappe.db.sql("""
		select je.name, je.posting_date, je.user_remark,
			ifnull(sum({bal_dr_or_cr}), 0) - (
				select ifnull(sum({payment_dr_or_cr}), 0)
				from `tabGL Entry` gle_payment
				where
					gle_payment.against_voucher_type = gle_je.voucher_type
					and gle_payment.against_voucher = gle_je.voucher_no
					and gle_payment.party_type = gle_je.party_type
					and gle_payment.party = gle_je.party
					and gle_payment.account = gle_je.account
					and abs({payment_dr_or_cr}) > 0
			) as balance
		from `tabGL Entry` gle_je
		inner join `tabJournal Entry` je on je.name = gle_je.voucher_no
		where
			gle_je.party_type = %(party_type)s and gle_je.party = %(party)s and gle_je.account = %(account)s
			and gle_je.voucher_type = 'Journal Entry' and (gle_je.against_voucher = '' or gle_je.against_voucher is null)
			and abs({bal_dr_or_cr}) > 0
		group by gle_je.voucher_no
		having abs(balance) > 0.005
		order by gle_je.posting_date""".format(
	bal_dr_or_cr=bal_dr_or_cr,
	payment_dr_or_cr=payment_dr_or_cr
	), {
		"party_type": party_type,
		"party": party,
		"account": party_account
	}, as_dict=1)

def get_against_jv(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("account") and filters.get("party_type") and filters.get("party"):
		res = get_outstanding_journal_entries(filters.get("account"), filters.get("party_type"), filters.get("party"))
		return [[jv.name, jv.posting_date, _("Balance: {0}").format(jv.balance), jv.user_remark] for jv in res]
	else:
		return frappe.db.sql("""select jv.name, jv.posting_date, jv.user_remark
			from `tabJournal Entry` jv, `tabJournal Entry Account` jv_detail
			where jv_detail.parent = jv.name and jv_detail.account = %s and ifnull(jv_detail.party, '') = %s
			and (jv_detail.reference_type is null or jv_detail.reference_type = '')
			and jv.docstatus = 1 and jv.`{0}` like %s order by jv.name desc limit %s, %s""".format(frappe.db.escape(searchfield)),
			(filters.get("account"), cstr(filters.get("party")), "%{0}%".format(txt), start, page_len))

@frappe.whitelist()
def get_outstanding(args):
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	if isinstance(args, string_types):
		args = json.loads(args)

	company_currency = erpnext.get_company_currency(args.get("company"))

	if args.get("doctype") == "Journal Entry":
		against_jv_amount = get_balance_on_voucher("Journal Entry", args.get("docname"), args.get("party_type"),
			args.get("party"), args.get("account"), dr_or_cr="debit_in_account_currency - credit_in_account_currency")

		amount_field = "credit_in_account_currency" if against_jv_amount >= 0 else "debit_in_account_currency"
		return {
			amount_field: abs(against_jv_amount)
		}
	elif args.get("doctype") in ("Sales Invoice", "Purchase Invoice"):
		party_type = "Customer" if args.get("doctype") == "Sales Invoice" else "Supplier"
		invoice = frappe.db.get_value(args["doctype"], args["docname"],
			["outstanding_amount", "conversion_rate", scrub(party_type)]
				+ (["letter_of_credit"] if args.get("doctype") == "Purchase Invoice" else []), as_dict=1)

		if invoice.get("letter_of_credit"):
			party_type = "Letter of Credit"

		exchange_rate = invoice.conversion_rate if (args.get("account_currency") != company_currency) else 1

		if args["doctype"] == "Sales Invoice":
			amount_field = "credit_in_account_currency" \
				if flt(invoice.outstanding_amount) > 0 else "debit_in_account_currency"
		else:
			amount_field = "debit_in_account_currency" \
				if flt(invoice.outstanding_amount) > 0 else "credit_in_account_currency"

		return {
			amount_field: abs(flt(invoice.outstanding_amount)),
			"exchange_rate": exchange_rate,
			"party_type": party_type,
			"party": invoice.get(scrub(party_type))
		}

@frappe.whitelist()
def get_party_account_and_balance(company, party_type, party, cost_center=None):
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	account = get_party_account(party_type, party, company)

	account_balance = get_balance_on(account=account, cost_center=cost_center)
	party_balance = get_balance_on(party_type=party_type, party=party, company=company, cost_center=cost_center)

	return {
		"account": account,
		"balance": account_balance,
		"party_balance": party_balance,
		"account_currency": frappe.db.get_value("Account", account, "account_currency")
	}


@frappe.whitelist()
def get_account_balance_and_party_type(account, date, company, debit=None, credit=None, exchange_rate=None, cost_center=None):
	"""Returns dict of account balance and party type to be set in Journal Entry on selection of account."""
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	company_currency = erpnext.get_company_currency(company)
	account_details = frappe.db.get_value("Account", account, ["account_type", "account_currency"], as_dict=1)

	if not account_details:
		return

	if account_details.account_type == "Receivable":
		if account == frappe.get_cached_value('Company', {"company_name": company}, "default_employee_loan_account"):
			party_type = "Employee"
		else:
			party_type = "Customer"
	elif account_details.account_type == "Payable":
		if account == frappe.get_cached_value('Company', {"company_name": company}, "default_letter_of_credit_account"):
			party_type = "Letter of Credit"
		elif account == frappe.get_cached_value('Company', {"company_name": company}, "default_employee_advance_account"):
			party_type = "Employee"
		else:
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
		"exchange_rate": get_exchange_rate(date, account, account_details.account_currency,
			company, debit=debit, credit=credit, exchange_rate=exchange_rate)
	}

	# un-set party if not party type
	if not party_type:
		grid_values["party"] = ""

	return grid_values


@frappe.whitelist()
def get_exchange_rate(posting_date, account=None, account_currency=None, company=None,
		reference_type=None, reference_name=None, debit=None, credit=None, exchange_rate=None,
		party_type=None, party=None):
	from erpnext.setup.utils import get_exchange_rate
	account_details = frappe.db.get_value("Account", account,
		["account_type", "root_type", "account_currency", "company"], as_dict=1)

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
		elif reference_type == "Journal Entry" and reference_name and party_type and party:
			exchange_rate = get_average_party_exchange_rate_on_journal_entry(reference_name, party_type, party, account)

		# The date used to retreive the exchange rate here is the date passed
		# in as an argument to this function.
		elif (not exchange_rate or exchange_rate==1) and account_currency and posting_date:
			exchange_rate = get_exchange_rate(account_currency, company_currency, posting_date)
	else:
		exchange_rate = 1

	# don't return None or 0 as it is multipled with a value and that value could be lost
	return exchange_rate or 1

def get_average_party_exchange_rate_on_journal_entry(jv_name, party_type, party, account):
	res = frappe.db.sql("""select avg(jv_detail.exchange_rate)
		from `tabJournal Entry` jv, `tabJournal Entry Account` jv_detail
		where jv.name = %s and jv_detail.parent = jv.name
		and jv_detail.account = %s and jv_detail.party_type = %s and jv_detail.party = %s
		and (jv_detail.reference_type is null or jv_detail.reference_type = '')
		""", [jv_name, account, party_type, party])
	return res[0][0] if res else 1.0

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
	journal_entry = frappe.new_doc('Journal Entry')
	journal_entry.voucher_type = voucher_type
	journal_entry.company = company
	journal_entry.posting_date = nowdate()
	journal_entry.inter_company_journal_entry_reference = name
	return journal_entry.as_dict()
