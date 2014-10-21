# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, flt, fmt_money, formatdate, getdate, money_in_words
from frappe import msgprint, _, scrub
from erpnext.setup.utils import get_company_currency
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.utils import get_balance_on


class JournalVoucher(AccountsController):
	def __init__(self, arg1, arg2=None):
		super(JournalVoucher, self).__init__(arg1, arg2)

	def get_feed(self):
		return self.voucher_type

	def validate(self):
		if not self.is_opening:
			self.is_opening='No'
		self.clearance_date = None

		super(JournalVoucher, self).validate_date_with_fiscal_year()
		self.validate_party()
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
		self.validate_against_sales_order()
		self.validate_against_purchase_order()
		self.check_credit_days()

	def on_submit(self):
		self.check_credit_limit()
		self.make_gl_entries()
		self.update_advance_paid()

	def update_advance_paid(self):
		advance_paid = frappe._dict()
		for d in self.get("entries"):
			if d.is_advance:
				if d.against_sales_order:
					advance_paid.setdefault("Sales Order", []).append(d.against_sales_order)
				elif d.against_purchase_order:
					advance_paid.setdefault("Purchase Order", []).append(d.against_purchase_order)

		for voucher_type, order_list in advance_paid.items():
			for voucher_no in list(set(order_list)):
				frappe.get_doc(voucher_type, voucher_no).set_total_advance_paid()

	def on_cancel(self):
		from erpnext.accounts.utils import remove_against_link_from_jv
		remove_against_link_from_jv(self.doctype, self.name, "against_jv")

		self.make_gl_entries(1)
		self.update_advance_paid()

	def validate_party(self):
		for d in self.get("entries"):
			account_type = frappe.db.get_value("Account", d.account, "account_type")
			if account_type in ["Receivable", "Payable"] and not (d.party_type and d.party):
				frappe.throw(_("Row{0}: Party Type and Party is required for Receivable / Payable account {1}").format(d.idx, d.account))


	def check_credit_limit(self):
		customers = list(set([d.party for d in self.get("entries") if d.party_type=="Customer"]))
		if customers:
			from erpnext.selling.doctype.customer.customer import check_credit_limit
			for customer in customers:
				check_credit_limit(customer, self.company)

	def check_credit_days(self):
		from erpnext.accounts.party import get_credit_days
		posting_date = self.posting_date
		if self.cheque_date:
			for d in self.get("entries"):
				if d.party_type and d.party and d.get("credit" if d.party_type=="Customer" else "debit") > 0:
					if d.against_invoice:
						posting_date = frappe.db.get_value("Sales Invoice", d.against_invoice, "posting_date")
					elif d.against_voucher:
						posting_date = frappe.db.get_value("Purchase Invoice", d.against_voucher, "posting_date")

					credit_days = get_credit_days(d.party_type, d.party, self.company)
					if credit_days:
						date_diff = (getdate(self.cheque_date) - getdate(posting_date)).days
						if  date_diff > flt(credit_days):
							msgprint(_("Note: Reference Date exceeds allowed credit days by {0} days for {1} {2}")
								.format(date_diff, d.party_type, d.party))

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

				if (d.party_type == 'Customer' and flt(d.credit) > 0) or \
						(d.party_type == 'Supplier' and flt(d.debit) > 0):
					msgprint(_("Row {0}: Please check 'Is Advance' against Account {1} if this is an advance entry.").format(d.row, d.account))

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
		payment_against_voucher = self.validate_account_in_against_voucher("against_invoice", "Sales Invoice")
		self.validate_against_invoice_fields("Sales Invoice", payment_against_voucher)

	def validate_against_purchase_invoice(self):
		payment_against_voucher = self.validate_account_in_against_voucher("against_voucher", "Purchase Invoice")
		self.validate_against_invoice_fields("Purchase Invoice", payment_against_voucher)

	def validate_against_sales_order(self):
		payment_against_voucher = self.validate_account_in_against_voucher("against_sales_order", "Sales Order")
		self.validate_against_order_fields("Sales Order", payment_against_voucher)

	def validate_against_purchase_order(self):
		payment_against_voucher = self.validate_account_in_against_voucher("against_purchase_order", "Purchase Order")
		self.validate_against_order_fields("Purchase Order", payment_against_voucher)

	def validate_account_in_against_voucher(self, against_field, doctype):
		payment_against_voucher = frappe._dict()
		field_dict = {'Sales Invoice': ["Customer", "Debit To"],
			'Purchase Invoice': ["Supplier", "Credit To"],
			'Sales Order': ["Customer"],
			'Purchase Order': ["Supplier"]
			}

		for d in self.get("entries"):
			if d.get(against_field):
				dr_or_cr = "credit" if against_field in ["against_invoice", "against_sales_order"] \
					else "debit"
				if against_field in ["against_invoice", "against_sales_order"] and flt(d.debit) > 0:
					frappe.throw(_("Row {0}: Debit entry can not be linked with a {1}").format(d.idx, doctype))

				if against_field in ["against_voucher", "against_purchase_order"] and flt(d.credit) > 0:
					frappe.throw(_("Row {0}: Credit entry can not be linked with a {1}").format(d.idx, doctype))

				against_voucher = frappe.db.get_value(doctype, d.get(against_field),
					[scrub(dt) for dt in field_dict.get(doctype)])

				if against_field in ["against_invoice", "against_voucher"]:
					if (against_voucher[0] !=d.party or against_voucher[1] != d.account):
						frappe.throw(_("Row {0}: Party / Account does not match with \
							Customer / Debit To in {1}").format(d.idx, doctype))
					else:
						payment_against_voucher.setdefault(d.get(against_field), []).append(flt(d.get(dr_or_cr)))

				if against_field in ["against_sales_order", "against_purchase_order"]:
					if against_voucher != d.party:
						frappe.throw(_("Row {0}: {1} {2} does not match with {3}") \
							.format(d.idx, d.party_type, d.party, doctype))
					elif d.is_advance == "Yes":
						payment_against_voucher.setdefault(d.get(against_field), []).append(flt(d.get(dr_or_cr)))

		return payment_against_voucher

	def validate_against_invoice_fields(self, doctype, payment_against_voucher):
		for voucher_no, payment_list in payment_against_voucher.items():
			voucher_properties = frappe.db.get_value(doctype, voucher_no,
				["docstatus", "outstanding_amount"])

			if voucher_properties[0] != 1:
				frappe.throw(_("{0} {1} is not submitted").format(doctype, voucher_no))

			if flt(voucher_properties[1]) < flt(sum(payment_list)):
				frappe.throw(_("Payment against {0} {1} cannot be greater \
					than Outstanding Amount {2}").format(doctype, voucher_no, voucher_properties[1]))

	def validate_against_order_fields(self, doctype, payment_against_voucher):
		for voucher_no, payment_list in payment_against_voucher.items():
			voucher_properties = frappe.db.get_value(doctype, voucher_no,
				["docstatus", "per_billed", "advance_paid", "grand_total"])

			if voucher_properties[0] != 1:
				frappe.throw(_("{0} {1} is not submitted").format(doctype, voucher_no))

			if flt(voucher_properties[1]) >= 100:
				frappe.throw(_("{0} {1} is fully billed").format(doctype, voucher_no))

			if flt(voucher_properties[3]) < flt(voucher_properties[2]) + flt(sum(payment_list)):
				frappe.throw(_("Advance paid against {0} {1} cannot be greater \
					than Grand Total {2}").format(doctype, voucher_no, voucher_properties[3]))

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

				r.append(_("{0} against Sales Invoice {1}").format(fmt_money(flt(d.credit), currency = currency), \
					d.against_invoice))

			if d.against_sales_order and d.credit:
				currency = frappe.db.get_value("Sales Order", d.against_sales_order, "currency")
				r.append(_("{0} against Sales Order {1}").format(fmt_money(flt(d.credit), currency = currency), \
					d.against_sales_order))

			if d.against_voucher and d.debit:
				bill_no = frappe.db.sql("""select bill_no, bill_date, currency
					from `tabPurchase Invoice` where name=%s""", d.against_voucher)
				if bill_no and bill_no[0][0] and bill_no[0][0].lower().strip() \
						not in ['na', 'not applicable', 'none']:
					r.append(_('{0} against Bill {1} dated {2}').format(fmt_money(flt(d.debit), currency=bill_no[0][2]), bill_no[0][0],
						bill_no[0][1] and formatdate(bill_no[0][1].strftime('%Y-%m-%d'))))

			if d.against_purchase_order and d.debit:
				currency = frappe.db.get_value("Purchase Order", d.against_purchase_order, "currency")
				r.append(_("{0} against Purchase Order {1}").format(fmt_money(flt(d.credit), currency = currency), \
					d.against_purchase_order))

		if self.user_remark:
			r.append(_("Note: {0}").format(self.user_remark))

		if r:
			self.remark = ("\n").join(r) #User Remarks is not mandatory


	def set_aging_date(self):
		if self.is_opening != 'Yes':
			self.aging_date = self.posting_date
		else:
			party_list = [d.party for d in self.get("entries") if d.party_type and d.party]

			if len(party_list) and not self.aging_date:
				frappe.throw(_("Aging Date is mandatory for opening entry"))
			else:
				self.aging_date = self.posting_date

	def set_print_format_fields(self):
		currency = get_company_currency(self.company)
		for d in self.get('entries'):
			if d.party_type and d.party:
				if not self.pay_to_recd_from:
					self.pay_to_recd_from = frappe.db.get_value(d.party_type, d.party,
						"customer_name" if d.party_type=="Customer" else "supplier_name")
			elif frappe.db.get_value("Account", d.account, "account_type") in ["Bank", "Cash"]:
				self.total_amount = fmt_money(d.debit or d.credit, currency=currency)
				self.total_amount_in_words = money_in_words(self.total_amount, currency)

	def make_gl_entries(self, cancel=0, adv_adj=0):
		from erpnext.accounts.general_ledger import make_gl_entries

		gl_map = []
		for d in self.get("entries"):
			if d.debit or d.credit:
				gl_map.append(
					self.get_gl_dict({
						"account": d.account,
						"party_type": d.party_type,
						"party": d.party,
						"against": d.against_account,
						"debit": flt(d.debit, self.precision("debit", "entries")),
						"credit": flt(d.credit, self.precision("credit", "entries")),
						"against_voucher_type": (("Purchase Invoice" if d.against_voucher else None)
							or ("Sales Invoice" if d.against_invoice else None)
							or ("Journal Voucher" if d.against_jv else None)
							or ("Sales Order" if d.against_sales_order else None)
							or ("Purchase Order" if d.against_purchase_order else None)),
						"against_voucher": d.against_voucher or d.against_invoice or d.against_jv
							or d.against_sales_order or d.against_purchase_order,
						"remarks": self.remark,
						"cost_center": d.cost_center
					})
				)

		if gl_map:
			make_gl_entries(gl_map, cancel=cancel, adv_adj=adv_adj)

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
			jd1.party = d.party

			if self.write_off_based_on == 'Accounts Receivable':
				jd1.party_type = "Customer"
				jd1.credit = flt(d.outstanding_amount, self.precision("credit", "entries"))
				jd1.against_invoice = cstr(d.name)
			elif self.write_off_based_on == 'Accounts Payable':
				jd1.party_type = "Supplier"
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
			return frappe.db.sql("""select name, debit_to as account, customer as party, outstanding_amount
				from `tabSales Invoice` where docstatus = 1 and company = %s
				and outstanding_amount > 0 %s""" % ('%s', cond), self.company, as_dict=True)
		elif self.write_off_based_on == 'Accounts Payable':
			return frappe.db.sql("""select name, credit_to as account, supplier as party, outstanding_amount
				from `tabPurchase Invoice` where docstatus = 1 and company = %s
				and outstanding_amount > 0 %s""" % ('%s', cond), self.company, as_dict=True)

@frappe.whitelist()
def get_default_bank_cash_account(company, voucher_type):
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
	jv.get("entries")[0].party_type = "Customer"
	jv.get("entries")[0].party = si.customer
	jv.get("entries")[0].balance = get_balance_on(si.debit_to)
	jv.get("entries")[0].party_balance = get_balance_on(party=si.customer, party_type="Customer")
	jv.get("entries")[0].credit = si.outstanding_amount
	jv.get("entries")[0].against_invoice = si.name

	# debit bank
	jv.get("entries")[1].debit = si.outstanding_amount

	return jv.as_dict()

@frappe.whitelist()
def get_payment_entry_from_purchase_invoice(purchase_invoice):
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	jv = get_payment_entry(pi)
	jv.remark = 'Payment against Purchase Invoice {0}. {1}'.format(pi.name, pi.remarks)

	# credit supplier
	jv.get("entries")[0].account = pi.credit_to
	jv.get("entries")[0].party_type = "Supplier"
	jv.get("entries")[0].party = pi.supplier
	jv.get("entries")[0].balance = get_balance_on(pi.credit_to)
	jv.get("entries")[0].party_balance = get_balance_on(party=pi.supplier, party_type="Supplier")
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
	accounts = frappe.db.sql_list("""select name from tabAccount
		where group_or_ledger='Ledger' and report_type='Balance Sheet' and company=%s""", company)

	return [{"account": a, "balance": get_balance_on(a)} for a in accounts]


def get_against_jv(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""select jv.name, jv.posting_date, jv.user_remark
		from `tabJournal Voucher` jv, `tabJournal Voucher Detail` jv_detail
		where jv_detail.parent = jv.name and jv_detail.account = %s and jv_detail.party = %s
		and jv.docstatus = 1 and jv.%s like %s order by jv.name desc limit %s, %s""" %
		("%s", searchfield, "%s", "%s", "%s"),
		(filters["account"], filters["party"], "%%%s%%" % txt, start, page_len))

@frappe.whitelist()
def get_outstanding(args):
	args = eval(args)
	if args.get("doctype") == "Journal Voucher" and args.get("party"):
		against_jv_amount = frappe.db.sql("""
			select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))
			from `tabJournal Voucher Detail` where parent=%s and party=%s
			and ifnull(against_invoice, '')='' and ifnull(against_voucher, '')=''
			and ifnull(against_jv, '')=''""", (args['docname'], args['party']))

		against_jv_amount = flt(against_jv_amount[0][0]) if against_jv_amount else 0
		if against_jv_amount > 0:
			return {"credit": against_jv_amount}
		else:
			return {"debit": -1* against_jv_amount}

	elif args.get("doctype") == "Sales Invoice":
		return {
			"credit": flt(frappe.db.get_value("Sales Invoice", args["docname"], "outstanding_amount"))
		}
	elif args.get("doctype") == "Purchase Invoice":
		return {
			"debit": flt(frappe.db.get_value("Purchase Invoice", args["docname"], "outstanding_amount"))
		}

@frappe.whitelist()
def get_party_account_and_balance(company, party_type, party):
	from erpnext.accounts.party import get_party_account
	account = get_party_account(company, party, party_type)

	account_balance = get_balance_on(account=account)
	party_balance = get_balance_on(party_type=party_type, party=party)

	return {
		"account": account,
		"balance": account_balance,
		"party_balance": party_balance
	}
