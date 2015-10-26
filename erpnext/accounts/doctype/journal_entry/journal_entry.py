# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, flt, fmt_money, formatdate
from frappe import msgprint, _, scrub
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.utils import get_balance_on, get_account_currency
from erpnext.setup.utils import get_company_currency


class JournalEntry(AccountsController):
	def __init__(self, arg1, arg2=None):
		super(JournalEntry, self).__init__(arg1, arg2)

	def get_feed(self):
		return self.voucher_type

	def validate(self):
		if not self.is_opening:
			self.is_opening='No'
		self.clearance_date = None

		super(JournalEntry, self).validate_date_with_fiscal_year()
		self.validate_party()
		self.validate_cheque_info()
		self.validate_entries_for_advance()
		self.validate_multi_currency()
		self.validate_debit_and_credit()
		self.validate_against_jv()
		self.validate_reference_doc()
		self.set_against_account()
		self.create_remarks()
		self.set_print_format_fields()
		self.validate_expense_claim()
		self.validate_credit_debit_note()
		self.validate_empty_accounts_table()
		self.set_account_and_party_balance()
		if not self.title:
			self.title = self.get_title()

	def on_submit(self):
		self.check_credit_limit()
		self.make_gl_entries()
		self.update_advance_paid()
		self.update_expense_claim()

	def get_title(self):
		return self.pay_to_recd_from or self.accounts[0].account

	def update_advance_paid(self):
		advance_paid = frappe._dict()
		for d in self.get("accounts"):
			if d.is_advance:
				if d.reference_type in ("Sales Order", "Purchase Order"):
					advance_paid.setdefault(d.reference_type, []).append(d.reference_name)

		for voucher_type, order_list in advance_paid.items():
			for voucher_no in list(set(order_list)):
				frappe.get_doc(voucher_type, voucher_no).set_total_advance_paid()

	def on_cancel(self):
		from erpnext.accounts.utils import remove_against_link_from_jv
		remove_against_link_from_jv(self.doctype, self.name)

		self.make_gl_entries(1)
		self.update_advance_paid()
		self.update_expense_claim()

	def validate_party(self):
		for d in self.get("accounts"):
			account_type = frappe.db.get_value("Account", d.account, "account_type")
			if account_type in ["Receivable", "Payable"]:
				if not (d.party_type and d.party):
					frappe.throw(_("Row {0}: Party Type and Party is required for Receivable / Payable account {1}").format(d.idx, d.account))
			elif d.party_type and d.party:
				frappe.throw(_("Row {0}: Party Type and Party is only applicable against Receivable / Payable account").format(d.idx))

	def check_credit_limit(self):
		customers = list(set([d.party for d in self.get("accounts")
			if d.party_type=="Customer" and d.party and flt(d.debit) > 0]))
		if customers:
			from erpnext.selling.doctype.customer.customer import check_credit_limit
			for customer in customers:
				check_credit_limit(customer, self.company)

	def validate_cheque_info(self):
		if self.voucher_type in ['Bank Entry']:
			if not self.cheque_no or not self.cheque_date:
				msgprint(_("Reference No & Reference Date is required for {0}").format(self.voucher_type),
					raise_exception=1)

		if self.cheque_date and not self.cheque_no:
			msgprint(_("Reference No is mandatory if you entered Reference Date"), raise_exception=1)

	def validate_entries_for_advance(self):
		for d in self.get('accounts'):
			if d.reference_type not in ("Sales Invoice", "Purchase Invoice", "Journal Entry"):
				if (d.party_type == 'Customer' and flt(d.credit) > 0) or \
						(d.party_type == 'Supplier' and flt(d.debit) > 0):
					if d.is_advance=="No":
						msgprint(_("Row {0}: Please check 'Is Advance' against Account {1} if this is an advance entry.").format(d.idx, d.account))
					elif d.reference_type in ("Sales Order", "Purchase Order") and d.is_advance != "Yes":
						frappe.throw(_("Row {0}: Payment against Sales/Purchase Order should always be marked as advance").format(d.idx))

	def validate_against_jv(self):
		for d in self.get('accounts'):
			if d.reference_type=="Journal Entry":
				account_root_type = frappe.db.get_value("Account", d.account, "root_type")
				if account_root_type == "Asset" and flt(d.debit) > 0:
					frappe.throw(_("For {0}, only credit accounts can be linked against another debit entry")
						.format(d.account))
				elif account_root_type == "Liability" and flt(d.credit) > 0:
					frappe.throw(_("For {0}, only debit accounts can be linked against another credit entry")
						.format(d.account))

				if d.reference_name == self.name:
					frappe.throw(_("You can not enter current voucher in 'Against Journal Entry' column"))

				against_entries = frappe.db.sql("""select * from `tabJournal Entry Account`
					where account = %s and docstatus = 1 and parent = %s
					and ifnull(reference_type, '') in ("", "Sales Order", "Purchase Order")
					""", (d.account, d.reference_name), as_dict=True)

				if not against_entries:
					frappe.throw(_("Journal Entry {0} does not have account {1} or already matched against other voucher")
						.format(d.reference_name, d.account))
				else:
					dr_or_cr = "debit" if d.credit > 0 else "credit"
					valid = False
					for jvd in against_entries:
						if flt(jvd[dr_or_cr]) > 0:
							valid = True
					if not valid:
						frappe.throw(_("Against Journal Entry {0} does not have any unmatched {1} entry")
							.format(d.reference_name, dr_or_cr))

	def validate_reference_doc(self):
		"""Validates reference document"""
		field_dict = {
			'Sales Invoice': ["Customer", "Debit To"],
			'Purchase Invoice': ["Supplier", "Credit To"],
			'Sales Order': ["Customer"],
			'Purchase Order': ["Supplier"]
		}

		self.reference_totals = {}
		self.reference_types = {}
		self.reference_accounts = {}

		for d in self.get("accounts"):
			if not d.reference_type:
				d.reference_name = None
			if not d.reference_name:
				d.reference_type = None
			if d.reference_type and d.reference_name and (d.reference_type in field_dict.keys()):
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

				# check if party and account match
				if d.reference_type in ("Sales Invoice", "Purchase Invoice"):
					if (against_voucher[0] != d.party or against_voucher[1] != d.account):
						frappe.throw(_("Row {0}: Party / Account does not match with {1} / {2} in {3} {4}")
							.format(d.idx, field_dict.get(d.reference_type)[0], field_dict.get(d.reference_type)[1],
								d.reference_type, d.reference_name))

				# check if party matches for Sales / Purchase Order
				if d.reference_type in ("Sales Order", "Purchase Order"):
					# set totals
					if against_voucher != d.party:
						frappe.throw(_("Row {0}: {1} {2} does not match with {3}") \
							.format(d.idx, d.party_type, d.party, d.reference_type))

		self.validate_orders()
		self.validate_invoices()

	def validate_orders(self):
		"""Validate totals, stopped and docstatus for orders"""
		for reference_name, total in self.reference_totals.iteritems():
			reference_type = self.reference_types[reference_name]
			account = self.reference_accounts[reference_name]

			if reference_type in ("Sales Order", "Purchase Order"):
				order = frappe.db.get_value(reference_type, reference_name,
					["docstatus", "per_billed", "status", "advance_paid",
						"base_grand_total", "grand_total", "currency"], as_dict=1)

				if order.docstatus != 1:
					frappe.throw(_("{0} {1} is not submitted").format(reference_type, reference_name))

				if flt(order.per_billed) >= 100:
					frappe.throw(_("{0} {1} is fully billed").format(reference_type, reference_name))

				if cstr(order.status) == "Stopped":
					frappe.throw(_("{0} {1} is stopped").format(reference_type, reference_name))

				account_currency = get_account_currency(account)
				if account_currency == self.company_currency:
					voucher_total = order.base_grand_total
				else:
					voucher_total = order.grand_total

				if flt(voucher_total) < (flt(order.advance_paid) + total):
					frappe.throw(_("Advance paid against {0} {1} cannot be greater \
						than Grand Total {2}").format(reference_type, reference_name, voucher_total))

	def validate_invoices(self):
		"""Validate totals and docstatus for invoices"""
		for reference_name, total in self.reference_totals.iteritems():
			reference_type = self.reference_types[reference_name]

			if reference_type in ("Sales Invoice", "Purchase Invoice"):
				invoice = frappe.db.get_value(reference_type, reference_name,
					["docstatus", "outstanding_amount"], as_dict=1)

				if invoice.docstatus != 1:
					frappe.throw(_("{0} {1} is not submitted").format(reference_type, reference_name))

				if total and flt(invoice.outstanding_amount) < total:
					frappe.throw(_("Payment against {0} {1} cannot be greater than Outstanding Amount {2}")
						.format(reference_type, reference_name, invoice.outstanding_amount))

	def set_against_account(self):
		accounts_debited, accounts_credited = [], []
		for d in self.get("accounts"):
			if flt(d.debit > 0): accounts_debited.append(d.party or d.account)
			if flt(d.credit) > 0: accounts_credited.append(d.party or d.account)

		for d in self.get("accounts"):
			if flt(d.debit > 0): d.against_account = ", ".join(list(set(accounts_credited)))
			if flt(d.credit > 0): d.against_account = ", ".join(list(set(accounts_debited)))

	def validate_debit_and_credit(self):
		self.total_debit, self.total_credit, self.difference = 0, 0, 0
		for d in self.get("accounts"):
			if d.debit and d.credit:
				frappe.throw(_("You cannot credit and debit same account at the same time"))

			self.total_debit = flt(self.total_debit) + flt(d.debit, d.precision("debit"))
			self.total_credit = flt(self.total_credit) + flt(d.credit, d.precision("credit"))

		self.difference = flt(self.total_debit, self.precision("total_debit")) - \
			flt(self.total_credit, self.precision("total_credit"))

		if self.difference:
			frappe.throw(_("Total Debit must be equal to Total Credit. The difference is {0}")
				.format(self.difference))

	def validate_multi_currency(self):
		alternate_currency = []
		for d in self.get("accounts"):
			account = frappe.db.get_value("Account", d.account, ["account_currency", "account_type"], as_dict=1)
			d.account_currency = account.account_currency or self.company_currency
			d.account_type = account.account_type

			if d.account_currency!=self.company_currency and d.account_currency not in alternate_currency:
				alternate_currency.append(d.account_currency)

		if alternate_currency:
			if not self.multi_currency:
				frappe.throw(_("Please check Multi Currency option to allow accounts with other currency"))

		self.set_exchange_rate()

		for d in self.get("accounts"):
			d.debit = flt(flt(d.debit_in_account_currency)*flt(d.exchange_rate), d.precision("debit"))
			d.credit = flt(flt(d.credit_in_account_currency)*flt(d.exchange_rate), d.precision("credit"))

	def set_exchange_rate(self):
		for d in self.get("accounts"):
			if d.account_currency == self.company_currency:
				d.exchange_rate = 1
			elif not d.exchange_rate or d.account_type=="Bank" or \
				(d.reference_type in ("Sales Invoice", "Purchase Invoice") and d.reference_name):
					d.exchange_rate = get_exchange_rate(d.account, d.account_currency, self.company,
						d.reference_type, d.reference_name, d.debit, d.credit, d.exchange_rate)

			if not d.exchange_rate:
				frappe.throw(_("Row {0}: Exchange Rate is mandatory").format(d.idx))

	def create_remarks(self):
		r = []
		if self.cheque_no:
			if self.cheque_date:
				r.append(_('Reference #{0} dated {1}').format(self.cheque_no, formatdate(self.cheque_date)))
			else:
				msgprint(_("Please enter Reference date"), raise_exception=frappe.MandatoryError)

		for d in self.get('accounts'):
			if d.reference_type=="Sales Invoice" and d.credit:
				r.append(_("{0} against Sales Invoice {1}").format(fmt_money(flt(d.credit), currency = self.company_currency), \
					d.reference_name))

			if d.reference_type=="Sales Order" and d.credit:
				r.append(_("{0} against Sales Order {1}").format(fmt_money(flt(d.credit), currency = self.company_currency), \
					d.reference_name))

			if d.reference_type == "Purchase Invoice" and d.debit:
				bill_no = frappe.db.sql("""select bill_no, bill_date
					from `tabPurchase Invoice` where name=%s""", d.reference_name)
				if bill_no and bill_no[0][0] and bill_no[0][0].lower().strip() \
						not in ['na', 'not applicable', 'none']:
					r.append(_('{0} against Bill {1} dated {2}').format(fmt_money(flt(d.debit), currency=self.company_currency), bill_no[0][0],
						bill_no[0][1] and formatdate(bill_no[0][1].strftime('%Y-%m-%d'))))

			if d.reference_type == "Purchase Order" and d.debit:
				r.append(_("{0} against Purchase Order {1}").format(fmt_money(flt(d.credit), currency = self.company_currency), \
					d.reference_name))

		if self.user_remark:
			r.append(_("Note: {0}").format(self.user_remark))

		if r:
			self.remark = ("\n").join(r) #User Remarks is not mandatory

	def set_print_format_fields(self):
		for d in self.get('accounts'):
			if d.party_type and d.party:
				if not self.pay_to_recd_from:
					self.pay_to_recd_from = frappe.db.get_value(d.party_type, d.party,
						"customer_name" if d.party_type=="Customer" else "supplier_name")

					self.set_total_amount(d.debit or d.credit)
			elif frappe.db.get_value("Account", d.account, "account_type") in ["Bank", "Cash"]:
				self.set_total_amount(d.debit or d.credit)

	def set_total_amount(self, amt):
		self.total_amount = amt
		from frappe.utils import money_in_words
		self.total_amount_in_words = money_in_words(amt, self.company_currency)

	def make_gl_entries(self, cancel=0, adv_adj=0):
		from erpnext.accounts.general_ledger import make_gl_entries

		gl_map = []
		for d in self.get("accounts"):
			if d.debit or d.credit:
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
						"remarks": self.remark,
						"cost_center": d.cost_center
					})
				)

		if gl_map:
			make_gl_entries(gl_map, cancel=cancel, adv_adj=adv_adj)

	def get_balance(self):
		if not self.get('accounts'):
			msgprint(_("'Entries' cannot be empty"), raise_exception=True)
		else:
			flag, self.total_debit, self.total_credit = 0, 0, 0
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

			self.validate_debit_and_credit()

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

		self.validate_debit_and_credit()


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
			if d.reference_type=="Expense Claim":
				amt = frappe.db.sql("""select sum(debit) as amt from `tabJournal Entry Account`
					where reference_type = "Expense Claim" and
					reference_name = %s and docstatus = 1""", d.reference_name ,as_dict=1)[0].amt
				frappe.db.set_value("Expense Claim", d.reference_name , "total_amount_reimbursed", amt)

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
			frappe.throw("Accounts table cannot be blank.")

	def set_account_and_party_balance(self):
		account_balance = {}
		party_balance = {}
		for d in self.get("accounts"):
			if d.account not in account_balance:
				account_balance[d.account] = get_balance_on(account=d.account, date=self.posting_date)

			if (d.party_type, d.party) not in party_balance:
				party_balance[(d.party_type, d.party)] = get_balance_on(party_type=d.party_type,
					party=d.party, date=self.posting_date)

			d.account_balance = account_balance[d.account]
			d.party_balance = party_balance[(d.party_type, d.party)]

@frappe.whitelist()
def get_default_bank_cash_account(company, voucher_type, mode_of_payment=None):
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
	if mode_of_payment:
		account = get_bank_cash_account(mode_of_payment, company)
		if account.get("account"):
			account.update({"balance": get_balance_on(account.get("account"))})
			return account

	if voucher_type=="Bank Entry":
		account = frappe.db.get_value("Company", company, "default_bank_account")
		if not account:
			account = frappe.db.get_value("Account", 
				{"company": company, "account_type": "Bank", "is_group": 0})
	elif voucher_type=="Cash Entry":
		account = frappe.db.get_value("Company", company, "default_cash_account")
		if not account:
			account = frappe.db.get_value("Account", 
				{"company": company, "account_type": "Cash", "is_group": 0})

	if account:
		account_details = frappe.db.get_value("Account", account, 
			["account_currency", "account_type"], as_dict=1)
		return {
			"account": account,
			"balance": get_balance_on(account),
			"account_currency": account_details.account_currency,
			"account_type": account_details.account_type
		}

@frappe.whitelist()
def get_payment_entry_from_sales_invoice(sales_invoice):
	"""Returns new Journal Entry document as dict for given Sales Invoice"""
	from erpnext.accounts.utils import get_balance_on
	si = frappe.get_doc("Sales Invoice", sales_invoice)

	# exchange rate
	exchange_rate = get_exchange_rate(si.debit_to, si.party_account_currency, si.company,
		si.doctype, si.name)

	jv = get_payment_entry(si)
	jv.remark = 'Payment received against Sales Invoice {0}. {1}'.format(si.name, si.remarks)

	# credit customer
	row1 = jv.get("accounts")[0]
	row1.account = si.debit_to
	row1.account_currency = si.party_account_currency
	row1.party_type = "Customer"
	row1.party = si.customer
	row1.balance = get_balance_on(si.debit_to)
	row1.party_balance = get_balance_on(party=si.customer, party_type="Customer")
	row1.credit_in_account_currency = si.outstanding_amount
	row1.reference_type = si.doctype
	row1.reference_name = si.name
	row1.exchange_rate = exchange_rate
	row1.account_type = "Receivable" if si.customer else ""

	# debit bank
	row2 = jv.get("accounts")[1]
	if row2.account_currency == si.party_account_currency:
		row2.debit_in_account_currency = si.outstanding_amount
	else:
		row2.debit_in_account_currency = si.outstanding_amount * exchange_rate

	# set multi currency check
	if row1.account_currency != si.company_currency or row2.account_currency != si.company_currency:
		jv.multi_currency = 1

	return jv.as_dict()

@frappe.whitelist()
def get_payment_entry_from_purchase_invoice(purchase_invoice):
	"""Returns new Journal Entry document as dict for given Purchase Invoice"""
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)

	exchange_rate = get_exchange_rate(pi.credit_to, pi.party_account_currency, pi.company,
		pi.doctype, pi.name)

	jv = get_payment_entry(pi)
	jv.remark = 'Payment against Purchase Invoice {0}. {1}'.format(pi.name, pi.remarks)
	jv.exchange_rate = exchange_rate

	# credit supplier
	row1 = jv.get("accounts")[0]
	row1.account = pi.credit_to
	row1.account_currency = pi.party_account_currency
	row1.party_type = "Supplier"
	row1.party = pi.supplier
	row1.balance = get_balance_on(pi.credit_to)
	row1.party_balance = get_balance_on(party=pi.supplier, party_type="Supplier")
	row1.debit_in_account_currency = pi.outstanding_amount
	row1.reference_type = pi.doctype
	row1.reference_name = pi.name
	row1.exchange_rate = exchange_rate
	row1.account_type = "Payable" if pi.supplier else ""

	# credit bank
	row2 = jv.get("accounts")[1]
	if row2.account_currency == pi.party_account_currency:
		row2.credit_in_account_currency = pi.outstanding_amount
	else:
		row2.credit_in_account_currency = pi.outstanding_amount * exchange_rate

	# set multi currency check
	if row1.account_currency != pi.company_currency or row2.account_currency != pi.company_currency:
		jv.multi_currency = 1

	return jv.as_dict()

@frappe.whitelist()
def get_payment_entry_from_sales_order(sales_order):
	"""Returns new Journal Entry document as dict for given Sales Order"""
	from erpnext.accounts.utils import get_balance_on
	from erpnext.accounts.party import get_party_account

	so = frappe.get_doc("Sales Order", sales_order)

	if flt(so.per_billed, 2) != 0.0:
		frappe.throw(_("Can only make payment against unbilled Sales Order"))

	jv = get_payment_entry(so)
	jv.remark = 'Advance payment received against Sales Order {0}.'.format(so.name)

	party_account = get_party_account("Customer", so.customer, so.company)
	party_account_currency = get_account_currency(party_account)

	exchange_rate = get_exchange_rate(party_account, party_account_currency, so.company)

	if party_account_currency == so.company_currency:
		amount = flt(so.base_grand_total) - flt(so.advance_paid)
	else:
		amount = flt(so.grand_total) - flt(so.advance_paid)

	# credit customer
	row1 = jv.get("accounts")[0]
	row1.account = party_account
	row1.account_currency = party_account_currency
	row1.party_type = "Customer"
	row1.party = so.customer
	row1.balance = get_balance_on(party_account)
	row1.party_balance = get_balance_on(party=so.customer, party_type="Customer")
	row1.credit_in_account_currency = amount
	row1.reference_type = so.doctype
	row1.reference_name = so.name
	row1.is_advance = "Yes"
	row1.exchange_rate = exchange_rate
	row1.account_type = "Receivable"

	# debit bank
	row2 = jv.get("accounts")[1]
	if row2.account_currency == party_account_currency:
		row2.debit_in_account_currency = amount
	else:
		row2.debit_in_account_currency = amount * exchange_rate

	# set multi currency check
	if row1.account_currency != so.company_currency or row2.account_currency != so.company_currency:
		jv.multi_currency = 1

	return jv.as_dict()

@frappe.whitelist()
def get_payment_entry_from_purchase_order(purchase_order):
	"""Returns new Journal Entry document as dict for given Sales Order"""
	from erpnext.accounts.utils import get_balance_on
	from erpnext.accounts.party import get_party_account
	po = frappe.get_doc("Purchase Order", purchase_order)

	if flt(po.per_billed, 2) != 0.0:
		frappe.throw(_("Can only make payment against unbilled Sales Order"))

	jv = get_payment_entry(po)
	jv.remark = 'Advance payment made against Purchase Order {0}.'.format(po.name)

	party_account = get_party_account("Supplier", po.supplier, po.company)
	party_account_currency = get_account_currency(party_account)

	exchange_rate = get_exchange_rate(party_account, party_account_currency, po.company)

	if party_account_currency == po.company_currency:
		amount = flt(po.base_grand_total) - flt(po.advance_paid)
	else:
		amount = flt(po.grand_total) - flt(po.advance_paid)

	# credit customer
	row1 = jv.get("accounts")[0]
	row1.account = party_account
	row1.party_type = "Supplier"
	row1.party = po.supplier
	row1.balance = get_balance_on(party_account)
	row1.party_balance = get_balance_on(party=po.supplier, party_type="Supplier")
	row1.debit_in_account_currency = amount
	row1.reference_type = po.doctype
	row1.reference_name = po.name
	row1.is_advance = "Yes"
	row1.exchange_rate = exchange_rate
	row1.account_type = "Payable"

	# debit bank
	row2 = jv.get("accounts")[1]
	if row2.account_currency == party_account_currency:
		row2.credit_in_account_currency = amount
	else:
		row2.credit_in_account_currency = amount * exchange_rate

	# set multi currency check
	if row1.account_currency != po.company_currency or row2.account_currency != po.company_currency:
		jv.multi_currency = 1

	return jv.as_dict()

def get_payment_entry(doc):
	bank_account = get_default_bank_cash_account(doc.company, "Bank Entry")

	jv = frappe.new_doc('Journal Entry')
	jv.voucher_type = 'Bank Entry'
	jv.company = doc.company
	jv.fiscal_year = doc.fiscal_year

	jv.append("accounts")
	d2 = jv.append("accounts")

	if bank_account:
		d2.account = bank_account["account"]
		d2.balance = bank_account["balance"]
		d2.account_currency = bank_account["account_currency"]
		d2.account_type = bank_account["account_type"]
		d2.exchange_rate = get_exchange_rate(bank_account["account"],
			bank_account["account_currency"], doc.company)

	return jv

@frappe.whitelist()
def get_opening_accounts(company):
	"""get all balance sheet accounts for opening entry"""
	accounts = frappe.db.sql_list("""select name from tabAccount
		where is_group=0 and report_type='Balance Sheet' and company=%s""", company)

	return [{"account": a, "balance": get_balance_on(a)} for a in accounts]


def get_against_jv(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select jv.name, jv.posting_date, jv.user_remark
		from `tabJournal Entry` jv, `tabJournal Entry Account` jv_detail
		where jv_detail.parent = jv.name and jv_detail.account = %s and ifnull(jv_detail.party, '') = %s
		and ifnull(jv_detail.reference_type, '') = ''
		and jv.docstatus = 1 and jv.{0} like %s order by jv.name desc limit %s, %s""".format(searchfield),
		(filters.get("account"), cstr(filters.get("party")), "%{0}%".format(txt), start, page_len))

@frappe.whitelist()
def get_outstanding(args):
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)
	args = eval(args)
	company_currency = get_company_currency(args.get("company"))

	if args.get("doctype") == "Journal Entry":
		condition = " and party=%(party)s" if args.get("party") else ""

		against_jv_amount = frappe.db.sql("""
			select sum(ifnull(debit_in_account_currency, 0)) - sum(ifnull(credit_in_account_currency, 0))
			from `tabJournal Entry Account` where parent=%(docname)s and account=%(account)s {0}
			and ifnull(reference_type, '')=''""".format(condition), args)

		against_jv_amount = flt(against_jv_amount[0][0]) if against_jv_amount else 0
		amount_field = "credit_in_account_currency" if against_jv_amount > 0 else "debit_in_account_currency"
		return {
			amount_field: abs(against_jv_amount)
		}
	elif args.get("doctype") in ("Sales Invoice", "Purchase Invoice"):
		invoice = frappe.db.get_value(args["doctype"], args["docname"],
			["outstanding_amount", "conversion_rate"], as_dict=1)

		exchange_rate = invoice.conversion_rate if (args.get("account_currency") != company_currency) else 1

		if args["doctype"] == "Sales Invoice":
			amount_field = "credit_in_account_currency" \
				if flt(invoice.outstanding_amount) > 0 else "debit_in_account_currency"
		else:
			amount_field = "debit_in_account_currency" \
				if flt(invoice.outstanding_amount) > 0 else "credit_in_account_currency"

		return {
			amount_field: abs(flt(invoice.outstanding_amount)),
			"exchange_rate": exchange_rate
		}

@frappe.whitelist()
def get_party_account_and_balance(company, party_type, party):
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	from erpnext.accounts.party import get_party_account
	account = get_party_account(party_type, party, company)

	account_balance = get_balance_on(account=account)
	party_balance = get_balance_on(party_type=party_type, party=party)

	return {
		"account": account,
		"balance": account_balance,
		"party_balance": party_balance
	}

@frappe.whitelist()
def get_account_balance_and_party_type(account, date, company, debit=None, credit=None, exchange_rate=None):
	"""Returns dict of account balance and party type to be set in Journal Entry on selection of account."""
	if not frappe.has_permission("Account"):
		frappe.msgprint(_("No Permission"), raise_exception=1)

	company_currency = get_company_currency(company)
	account_details = frappe.db.get_value("Account", account, ["account_type", "account_currency"], as_dict=1)

	if account_details.account_type == "Receivable":
		party_type = "Customer"
	elif account_details.account_type == "Payable":
		party_type = "Supplier"
	else:
		party_type = ""

	grid_values = {
		"balance": get_balance_on(account, date),
		"party_type": party_type,
		"account_type": account_details.account_type,
		"account_currency": account_details.account_currency or company_currency,
		"exchange_rate": get_exchange_rate(account, account_details.account_currency,
			company, debit=debit, credit=credit, exchange_rate=exchange_rate)
	}
	return grid_values

@frappe.whitelist()
def get_exchange_rate(account, account_currency=None, company=None,
		reference_type=None, reference_name=None, debit=None, credit=None, exchange_rate=None):
	from erpnext.setup.utils import get_exchange_rate
	account_details = frappe.db.get_value("Account", account, 
		["account_type", "root_type", "account_currency", "company"], as_dict=1)
	
	if not company:
		company = account_details.company
		
	if not account_currency:
		account_currency = account_details.account_currency
		
	company_currency = get_company_currency(company)

	if account_currency != company_currency:
		if reference_type in ("Sales Invoice", "Purchase Invoice") and reference_name:
			exchange_rate = frappe.db.get_value(reference_type, reference_name, "conversion_rate")

		elif account_details and account_details.account_type == "Bank" and \
			((account_details.root_type == "Asset" and flt(credit) > 0) or
				(account_details.root_type == "Liability" and debit)):
			exchange_rate = get_average_exchange_rate(account)

		if not exchange_rate and account_currency:
			exchange_rate = get_exchange_rate(account_currency, company_currency)

	else:
		exchange_rate = 1

	# don't return None or 0 as it is multipled with a value and that value could be lost
	return exchange_rate or 1

def get_average_exchange_rate(account):
	exchange_rate = 0
	bank_balance_in_account_currency = get_balance_on(account)
	if bank_balance_in_account_currency:
		bank_balance_in_company_currency = get_balance_on(account, in_account_currency=False)
		exchange_rate = bank_balance_in_company_currency / bank_balance_in_account_currency

	return exchange_rate
