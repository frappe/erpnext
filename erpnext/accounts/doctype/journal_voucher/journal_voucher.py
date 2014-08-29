# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cint, cstr, flt, fmt_money, formatdate, getdate
from frappe import msgprint, _
from erpnext.setup.utils import get_company_currency

from erpnext.controllers.accounts_controller import AccountsController

class JournalVoucher(AccountsController):
	def __init__(self, arg1, arg2=None):
		super(JournalVoucher, self).__init__(arg1, arg2)
		self.master_type = {}
		self.credit_days_for = {}
		self.credit_days_global = -1
		self.is_approving_authority = -1

	def validate(self):
		if not self.is_opening:
			self.is_opening='No'
		self.clearance_date = None

		super(JournalVoucher, self).validate_date_with_fiscal_year()

		self.validate_cheque_info()
		self.validate_entries_for_advance()
		self.validate_debit_and_credit()
		self.validate_against_jv()
		self.validate_against_sales_invoice()
		self.validate_against_purchase_invoice()
		self.set_against_account()
		self.create_remarks()
		self.set_aging_date()
		self.set_print_format_fields()

	def on_submit(self):
		if self.voucher_type in ['Bank Voucher', 'Contra Voucher', 'Journal Entry']:
			self.check_credit_days()
		self.make_gl_entries()
		self.check_credit_limit()

	def on_cancel(self):
		from erpnext.accounts.utils import remove_against_link_from_jv
		remove_against_link_from_jv(self.doctype, self.name, "against_jv")

		self.make_gl_entries(1)

	def validate_cheque_info(self):
		if self.voucher_type in ['Bank Voucher']:
			if not self.cheque_no or not self.cheque_date:
				msgprint(_("Reference No & Reference Date is required for {0}").format(self.voucher_type),
					raise_exception=1)

		if self.cheque_date and not self.cheque_no:
			msgprint(_("Reference No is mandatory if you entered Reference Date"), raise_exception=1)

	def validate_entries_for_advance(self):
		for d in self.get('entries'):
			if not d.is_advance and not d.against_voucher and \
					not d.against_invoice and not d.against_jv:
				master_type = frappe.db.get_value("Account", d.account, "master_type")
				if (master_type == 'Customer' and flt(d.credit) > 0) or \
						(master_type == 'Supplier' and flt(d.debit) > 0):
					msgprint(_("Please check 'Is Advance' against Account {0} if this is an advance entry.").format(d.account))

	def validate_against_jv(self):
		for d in self.get('entries'):
			if d.against_jv:
				if d.against_jv == self.name:
					frappe.throw(_("You can not enter current voucher in 'Against Journal Voucher' column"))

				against_entries = frappe.db.sql("""select * from `tabJournal Voucher Detail`
					where account = %s and docstatus = 1 and parent = %s
					and ifnull(against_jv, '') = ''""", (d.account, d.against_jv), as_dict=True)

				if not against_entries:
					frappe.throw(_("Journal Voucher {0} does not have account {1} or already matched")
						.format(d.against_jv, d.account))
				else:
					dr_or_cr = "debit" if d.credit > 0 else "credit"
					valid = False
					for jvd in against_entries:
						if flt(jvd[dr_or_cr]) > 0:
							valid = True
					if not valid:
						frappe.throw(_("Against Journal Voucher {0} does not have any unmatched {1} entry")
							.format(d.against_jv, dr_or_cr))

	def validate_against_sales_invoice(self):
		for d in self.get("entries"):
			if d.against_invoice:
				if d.debit > 0:
					frappe.throw(_("Row {0}: Debit entry can not be linked with a Sales Invoice")
						.format(d.idx))
				if frappe.db.get_value("Sales Invoice", d.against_invoice, "debit_to") != d.account:
					frappe.throw(_("Row {0}: Account does not match with \
						Sales Invoice Debit To account").format(d.idx, d.account))

	def validate_against_purchase_invoice(self):
		for d in self.get("entries"):
			if d.against_voucher:
				if flt(d.credit) > 0:
					frappe.throw(_("Row {0}: Credit entry can not be linked with a Purchase Invoice")
						.format(d.idx))
				if frappe.db.get_value("Purchase Invoice", d.against_voucher, "credit_to") != d.account:
					frappe.throw(_("Row {0}: Account does not match with \
						Purchase Invoice Credit To account").format(d.idx, d.account))

	def set_against_account(self):
		accounts_debited, accounts_credited = [], []
		for d in self.get("entries"):
			if flt(d.debit > 0): accounts_debited.append(d.account)
			if flt(d.credit) > 0: accounts_credited.append(d.account)

		for d in self.get("entries"):
			if flt(d.debit > 0): d.against_account = ", ".join(list(set(accounts_credited)))
			if flt(d.credit > 0): d.against_account = ", ".join(list(set(accounts_debited)))

	def validate_debit_and_credit(self):
		self.total_debit, self.total_credit, self.difference = 0, 0, 0

		for d in self.get("entries"):
			if d.debit and d.credit:
				frappe.throw(_("You cannot credit and debit same account at the same time"))

			self.total_debit = flt(self.total_debit) + flt(d.debit, self.precision("debit", "entries"))
			self.total_credit = flt(self.total_credit) + flt(d.credit, self.precision("credit", "entries"))

		self.difference = flt(self.total_debit, self.precision("total_debit")) - \
			flt(self.total_credit, self.precision("total_credit"))

		if self.difference:
			frappe.throw(_("Total Debit must be equal to Total Credit. The difference is {0}")
				.format(self.difference))

	def create_remarks(self):
		r = []
		if self.cheque_no:
			if self.cheque_date:
				r.append(_('Reference #{0} dated {1}').format(self.cheque_no, formatdate(self.cheque_date)))
			else:
				msgprint(_("Please enter Reference date"), raise_exception=frappe.MandatoryError)

		for d in self.get('entries'):
			if d.against_invoice and d.credit:
				currency = frappe.db.get_value("Sales Invoice", d.against_invoice, "currency")
				r.append(_("{0} {1} against Invoice {2}").format(currency, fmt_money(flt(d.credit)), d.against_invoice))

			if d.against_voucher and d.debit:
				bill_no = frappe.db.sql("""select bill_no, bill_date, currency
					from `tabPurchase Invoice` where name=%s""", d.against_voucher)
				if bill_no and bill_no[0][0] and bill_no[0][0].lower().strip() \
						not in ['na', 'not applicable', 'none']:
					r.append(_('{0} {1} against Bill {2} dated {3}').format(bill_no[0][2],
						fmt_money(flt(d.debit)), bill_no[0][0],
						bill_no[0][1] and formatdate(bill_no[0][1].strftime('%Y-%m-%d'))))

		if self.user_remark:
			r.append(_("Note: {0}").format(self.user_remark))

		if r:
			self.remark = ("\n").join(r)
		else:
			frappe.msgprint(_("User Remarks is mandatory"), raise_exception=frappe.MandatoryError)

	def set_aging_date(self):
		if self.is_opening != 'Yes':
			self.aging_date = self.posting_date
		else:
			# check account type whether supplier or customer
			exists = False
			for d in self.get('entries'):
				account_type = frappe.db.get_value("Account", d.account, "account_type")
				if account_type in ["Supplier", "Customer"]:
					exists = True
					break

			# If customer/supplier account, aging date is mandatory
			if exists and not self.aging_date:
				msgprint(_("Aging Date is mandatory for opening entry"), raise_exception=1)
			else:
				self.aging_date = self.posting_date

	def set_print_format_fields(self):
		for d in self.get('entries'):
			result = frappe.db.get_value("Account", d.account,
				["account_type", "master_type"])

			if not result:
				continue

			account_type, master_type = result

			if master_type in ['Supplier', 'Customer']:
				if not self.pay_to_recd_from:
					self.pay_to_recd_from = frappe.db.get_value(master_type,
						' - '.join(d.account.split(' - ')[:-1]),
						master_type == 'Customer' and 'customer_name' or 'supplier_name')

			if account_type in ['Bank', 'Cash']:
				company_currency = get_company_currency(self.company)
				amt = flt(d.debit) and d.debit or d.credit
				self.total_amount = fmt_money(amt, currency=company_currency)
				from frappe.utils import money_in_words
				self.total_amount_in_words = money_in_words(amt, company_currency)

	def check_credit_days(self):
		date_diff = 0
		if self.cheque_date:
			date_diff = (getdate(self.cheque_date)-getdate(self.posting_date)).days

		if date_diff <= 0: return

		# Get List of Customer Account
		acc_list = filter(lambda d: frappe.db.get_value("Account", d.account,
		 	"master_type")=='Customer', self.get('entries'))

		for d in acc_list:
			credit_days = self.get_credit_days_for(d.account)
			# Check credit days
			if credit_days > 0 and not self.get_authorized_user() and cint(date_diff) > credit_days:
				msgprint(_("Maximum allowed credit is {0} days after posting date").format(credit_days),
					raise_exception=1)

	def get_credit_days_for(self, ac):
		if not self.credit_days_for.has_key(ac):
			self.credit_days_for[ac] = cint(frappe.db.get_value("Account", ac, "credit_days"))

		if not self.credit_days_for[ac]:
			if self.credit_days_global==-1:
				self.credit_days_global = cint(frappe.db.get_value("Company",
					self.company, "credit_days"))

			return self.credit_days_global
		else:
			return self.credit_days_for[ac]

	def get_authorized_user(self):
		if self.is_approving_authority==-1:
			self.is_approving_authority = 0

			# Fetch credit controller role
			approving_authority = frappe.db.get_value("Accounts Settings", None,
				"credit_controller")

			# Check logged-in user is authorized
			if approving_authority in frappe.user.get_roles():
				self.is_approving_authority = 1

		return self.is_approving_authority

	def make_gl_entries(self, cancel=0, adv_adj=0):
		from erpnext.accounts.general_ledger import make_gl_entries

		gl_map = []
		for d in self.get("entries"):
			if d.debit or d.credit:
				gl_map.append(
					self.get_gl_dict({
						"account": d.account,
						"against": d.against_account,
						"debit": flt(d.debit, self.precision("debit", "entries")),
						"credit": flt(d.credit, self.precision("credit", "entries")),
						"against_voucher_type": ((d.against_voucher and "Purchase Invoice")
							or (d.against_invoice and "Sales Invoice")
							or (d.against_jv and "Journal Voucher")),
						"against_voucher": d.against_voucher or d.against_invoice or d.against_jv,
						"remarks": self.remark,
						"cost_center": d.cost_center
					})
				)
		if gl_map:
			make_gl_entries(gl_map, cancel=cancel, adv_adj=adv_adj)

	def check_credit_limit(self):
		for d in self.get("entries"):
			master_type, master_name = frappe.db.get_value("Account", d.account,
				["master_type", "master_name"])
			if master_type == "Customer" and master_name:
				super(JournalVoucher, self).check_credit_limit(d.account)

	def get_balance(self):
		if not self.get('entries'):
			msgprint(_("'Entries' cannot be empty"), raise_exception=True)
		else:
			flag, self.total_debit, self.total_credit = 0, 0, 0
			diff = flt(self.difference, self.precision("difference"))

			# If any row without amount, set the diff on that row
			for d in self.get('entries'):
				if not d.credit and not d.debit and diff != 0:
					if diff>0:
						d.credit = diff
					elif diff<0:
						d.debit = diff
					flag = 1

			# Set the diff in a new row
			if flag == 0 and diff != 0:
				jd = self.append('entries', {})
				if diff>0:
					jd.credit = abs(diff)
				elif diff<0:
					jd.debit = abs(diff)

			self.validate_debit_and_credit()

	def get_outstanding_invoices(self):
		self.set('entries', [])
		total = 0
		for d in self.get_values():
			total += flt(d.outstanding_amount, self.precision("credit", "entries"))
			jd1 = self.append('entries', {})
			jd1.account = d.account

			if self.write_off_based_on == 'Accounts Receivable':
				jd1.credit = flt(d.outstanding_amount, self.precision("credit", "entries"))
				jd1.against_invoice = cstr(d.name)
			elif self.write_off_based_on == 'Accounts Payable':
				jd1.debit = flt(d.outstanding_amount, self.precision("debit", "entries"))
				jd1.against_voucher = cstr(d.name)

		jd2 = self.append('entries', {})
		if self.write_off_based_on == 'Accounts Receivable':
			jd2.debit = total
		elif self.write_off_based_on == 'Accounts Payable':
			jd2.credit = total

		self.validate_debit_and_credit()


	def get_values(self):
		cond = " and outstanding_amount <= {0}".format(self.write_off_amount) \
			if flt(self.write_off_amount) > 0 else ""

		if self.write_off_based_on == 'Accounts Receivable':
			return frappe.db.sql("""select name, debit_to as account, outstanding_amount
				from `tabSales Invoice` where docstatus = 1 and company = %s
				and outstanding_amount > 0 %s""" % ('%s', cond), self.company, as_dict=True)
		elif self.write_off_based_on == 'Accounts Payable':
			return frappe.db.sql("""select name, credit_to as account, outstanding_amount
				from `tabPurchase Invoice` where docstatus = 1 and company = %s
				and outstanding_amount > 0 %s""" % ('%s', cond), self.company, as_dict=True)

@frappe.whitelist()
def get_default_bank_cash_account(company, voucher_type):
	from erpnext.accounts.utils import get_balance_on
	account = frappe.db.get_value("Company", company,
		voucher_type=="Bank Voucher" and "default_bank_account" or "default_cash_account")
	if account:
		return {
			"account": account,
			"balance": get_balance_on(account)
		}

@frappe.whitelist()
def get_payment_entry_from_sales_invoice(sales_invoice):
	from erpnext.accounts.utils import get_balance_on
	si = frappe.get_doc("Sales Invoice", sales_invoice)
	jv = get_payment_entry(si)
	jv.remark = 'Payment received against Sales Invoice {0}. {1}'.format(si.name, si.remarks)

	# credit customer
	jv.get("entries")[0].account = si.debit_to
	jv.get("entries")[0].balance = get_balance_on(si.debit_to)
	jv.get("entries")[0].credit = si.outstanding_amount
	jv.get("entries")[0].against_invoice = si.name

	# debit bank
	jv.get("entries")[1].debit = si.outstanding_amount

	return jv.as_dict()

@frappe.whitelist()
def get_payment_entry_from_purchase_invoice(purchase_invoice):
	from erpnext.accounts.utils import get_balance_on
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	jv = get_payment_entry(pi)
	jv.remark = 'Payment against Purchase Invoice {0}. {1}'.format(pi.name, pi.remarks)

	# credit supplier
	jv.get("entries")[0].account = pi.credit_to
	jv.get("entries")[0].balance = get_balance_on(pi.credit_to)
	jv.get("entries")[0].debit = pi.outstanding_amount
	jv.get("entries")[0].against_voucher = pi.name

	# credit bank
	jv.get("entries")[1].credit = pi.outstanding_amount

	return jv.as_dict()

def get_payment_entry(doc):
	bank_account = get_default_bank_cash_account(doc.company, "Bank Voucher")

	jv = frappe.new_doc('Journal Voucher')
	jv.voucher_type = 'Bank Voucher'

	jv.company = doc.company
	jv.fiscal_year = doc.fiscal_year

	jv.append("entries")
	d2 = jv.append("entries")

	if bank_account:
		d2.account = bank_account["account"]
		d2.balance = bank_account["balance"]

	return jv

@frappe.whitelist()
def get_opening_accounts(company):
	"""get all balance sheet accounts for opening entry"""
	from erpnext.accounts.utils import get_balance_on
	accounts = frappe.db.sql_list("""select name from tabAccount
		where group_or_ledger='Ledger' and report_type='Balance Sheet' and company=%s""", company)

	return [{"account": a, "balance": get_balance_on(a)} for a in accounts]

def get_against_purchase_invoice(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select name, credit_to, outstanding_amount, bill_no, bill_date
		from `tabPurchase Invoice` where credit_to = %s and docstatus = 1
		and outstanding_amount > 0 and %s like %s order by name desc limit %s, %s""" %
		("%s", searchfield, "%s", "%s", "%s"),
		(filters["account"], "%%%s%%" % txt, start, page_len))

def get_against_sales_invoice(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select name, debit_to, outstanding_amount
		from `tabSales Invoice` where debit_to = %s and docstatus = 1
		and outstanding_amount > 0 and `%s` like %s order by name desc limit %s, %s""" %
		("%s", searchfield, "%s", "%s", "%s"),
		(filters["account"], "%%%s%%" % txt, start, page_len))

def get_against_jv(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select jv.name, jv.posting_date, jv.user_remark
		from `tabJournal Voucher` jv, `tabJournal Voucher Detail` jv_detail
		where jv_detail.parent = jv.name and jv_detail.account = %s and jv.docstatus = 1
		and jv.%s like %s order by jv.name desc limit %s, %s""" %
		("%s", searchfield, "%s", "%s", "%s"),
		(filters["account"], "%%%s%%" % txt, start, page_len))

@frappe.whitelist()
def get_outstanding(args):
	args = eval(args)
	if args.get("doctype") == "Journal Voucher" and args.get("account"):
		against_jv_amount = frappe.db.sql("""
			select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))
			from `tabJournal Voucher Detail` where parent=%s and account=%s
			and ifnull(against_invoice, '')='' and ifnull(against_voucher, '')=''
			and ifnull(against_jv, '')=''""", (args['docname'], args['account']))

		against_jv_amount = flt(against_jv_amount[0][0]) if against_jv_amount else 0
		if against_jv_amount > 0:
			return {"credit": against_jv_amount}
		else:
			return {"debit": -1* against_jv_amount}

	elif args.get("doctype") == "Sales Invoice":
		return {
			"credit": flt(frappe.db.get_value("Sales Invoice", args["docname"],
				"outstanding_amount"))
		}
	elif args.get("doctype") == "Purchase Invoice":
		return {
			"debit": flt(frappe.db.get_value("Purchase Invoice", args["docname"],
				"outstanding_amount"))
		}
