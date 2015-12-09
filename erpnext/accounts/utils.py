# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils import nowdate, cstr, flt, now, getdate, add_months
from frappe import throw, _
from frappe.utils import formatdate
import frappe.desk.reportview

# imported to enable erpnext.accounts.utils.get_account_currency
from erpnext.accounts.doctype.account.account import get_account_currency

class FiscalYearError(frappe.ValidationError): pass
class BudgetError(frappe.ValidationError): pass

@frappe.whitelist()
def get_fiscal_year(date=None, fiscal_year=None, label="Date", verbose=1, company=None):
	return get_fiscal_years(date, fiscal_year, label, verbose, company)[0]

def get_fiscal_years(transaction_date=None, fiscal_year=None, label="Date", verbose=1, company=None):
	# if year start date is 2012-04-01, year end date should be 2013-03-31 (hence subdate)
	cond = " disabled = 0"
	if fiscal_year:
		cond += " and fy.name = %(fiscal_year)s"
	else:
		cond += " and %(transaction_date)s >= fy.year_start_date and %(transaction_date)s <= fy.year_end_date"

	if company:
		cond += """ and (not exists(select name from `tabFiscal Year Company` fyc where fyc.parent = fy.name)
			or exists(select company from `tabFiscal Year Company` fyc where fyc.parent = fy.name and fyc.company=%(company)s ))"""

	fy = frappe.db.sql("""select fy.name, fy.year_start_date, fy.year_end_date from `tabFiscal Year` fy
		where %s order by fy.year_start_date desc""" % cond, {
			"fiscal_year": fiscal_year,
			"transaction_date": transaction_date,
			"company": company
		})

	if not fy:
		error_msg = _("""{0} {1} not in any active Fiscal Year. For more details check {2}.""").format(label, formatdate(transaction_date), "https://erpnext.com/kb/accounts/fiscal-year-error")
		if verbose==1: frappe.msgprint(error_msg)
		raise FiscalYearError, error_msg
	return fy

def validate_fiscal_year(date, fiscal_year, label=_("Date"), doc=None):
	years = [f[0] for f in get_fiscal_years(date, label=label)]
	if fiscal_year not in years:
		if doc:
			doc.fiscal_year = years[0]
		else:
			throw(_("{0} '{1}' not in Fiscal Year {2}").format(label, formatdate(date), fiscal_year))

@frappe.whitelist()
def get_balance_on(account=None, date=None, party_type=None, party=None, in_account_currency=True):
	if not account and frappe.form_dict.get("account"):
		account = frappe.form_dict.get("account")
	if not date and frappe.form_dict.get("date"):
		date = frappe.form_dict.get("date")
	if not party_type and frappe.form_dict.get("party_type"):
		party_type = frappe.form_dict.get("party_type")
	if not party and frappe.form_dict.get("party"):
		party = frappe.form_dict.get("party")

	cond = []
	if date:
		cond.append("posting_date <= '%s'" % frappe.db.escape(cstr(date)))
	else:
		# get balance of all entries that exist
		date = nowdate()

	try:
		year_start_date = get_fiscal_year(date, verbose=0)[1]
	except FiscalYearError:
		if getdate(date) > getdate(nowdate()):
			# if fiscal year not found and the date is greater than today
			# get fiscal year for today's date and its corresponding year start date
			year_start_date = get_fiscal_year(nowdate(), verbose=1)[1]
		else:
			# this indicates that it is a date older than any existing fiscal year.
			# hence, assuming balance as 0.0
			return 0.0

	if account:
		acc = frappe.get_doc("Account", account)

		if not frappe.flags.ignore_account_permission:
			acc.check_permission("read")

		# for pl accounts, get balance within a fiscal year
		if acc.report_type == 'Profit and Loss':
			cond.append("posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" \
				% year_start_date)

		# different filter for group and ledger - improved performance
		if acc.is_group:
			cond.append("""exists (
				select name from `tabAccount` ac where ac.name = gle.account
				and ac.lft >= %s and ac.rgt <= %s
			)""" % (acc.lft, acc.rgt))

			# If group and currency same as company,
			# always return balance based on debit and credit in company currency
			if acc.account_currency == frappe.db.get_value("Company", acc.company, "default_currency"):
				in_account_currency = False
		else:
			cond.append("""gle.account = "%s" """ % (frappe.db.escape(account), ))

	if party_type and party:
		cond.append("""gle.party_type = "%s" and gle.party = "%s" """ %
			(frappe.db.escape(party_type), frappe.db.escape(party)))

	if account or (party_type and party):
		if in_account_currency:
			select_field = "sum(debit_in_account_currency) - sum(credit_in_account_currency)"
		else:
			select_field = "sum(debit) - sum(credit)"
		bal = frappe.db.sql("""
			SELECT {0}
			FROM `tabGL Entry` gle
			WHERE {1}""".format(select_field, " and ".join(cond)))[0][0]

		# if bal is None, return 0
		return flt(bal)

@frappe.whitelist()
def add_ac(args=None):
	if not args:
		args = frappe.local.form_dict
		args.pop("cmd")

	ac = frappe.new_doc("Account")
	ac.update(args)
	ac.old_parent = ""
	ac.freeze_account = "No"
	if ac.get("is_root"):
		ac.flags.ignore_mandatory = True
	ac.insert()

	return ac.name

@frappe.whitelist()
def add_cc(args=None):
	if not args:
		args = frappe.local.form_dict
		args.pop("cmd")

	cc = frappe.new_doc("Cost Center")
	cc.update(args)
	cc.old_parent = ""
	cc.insert()
	return cc.name

def reconcile_against_document(args):
	"""
		Cancel JV, Update aginst document, split if required and resubmit jv
	"""
	for d in args:
		check_if_jv_modified(d)
		validate_allocated_amount(d)

		# cancel JV
		jv_obj = frappe.get_doc('Journal Entry', d['voucher_no'])

		jv_obj.make_gl_entries(cancel=1, adv_adj=1)

		# update ref in JV Detail
		update_against_doc(d, jv_obj)

		# re-submit JV
		jv_obj = frappe.get_doc('Journal Entry', d['voucher_no'])
		jv_obj.make_gl_entries(cancel = 0, adv_adj =1)


def check_if_jv_modified(args):
	"""
		check if there is already a voucher reference
		check if amount is same
		check if jv is submitted
	"""
	ret = frappe.db.sql("""
		select t2.{dr_or_cr} from `tabJournal Entry` t1, `tabJournal Entry Account` t2
		where t1.name = t2.parent and t2.account = %(account)s
		and t2.party_type = %(party_type)s and t2.party = %(party)s
		and (t2.reference_type is null or t2.reference_type in ("", "Sales Order", "Purchase Order"))
		and t1.name = %(voucher_no)s and t2.name = %(voucher_detail_no)s
		and t1.docstatus=1 """.format(dr_or_cr = args.get("dr_or_cr")), args)

	if not ret:
		throw(_("""Payment Entry has been modified after you pulled it. Please pull it again."""))

def validate_allocated_amount(args):
	if args.get("allocated_amt") < 0:
		throw(_("Allocated amount can not be negative"))
	elif args.get("allocated_amt") > args.get("unadjusted_amt"):
		throw(_("Allocated amount can not greater than unadusted amount"))

def update_against_doc(d, jv_obj):
	"""
		Updates against document, if partial amount splits into rows
	"""
	jv_detail = jv_obj.get("accounts", {"name": d["voucher_detail_no"]})[0]
	jv_detail.set(d["dr_or_cr"], d["allocated_amt"])
	jv_detail.set('debit' if d['dr_or_cr']=='debit_in_account_currency' else 'credit',
		d["allocated_amt"]*flt(jv_detail.exchange_rate))

	original_reference_type = jv_detail.reference_type
	original_reference_name = jv_detail.reference_name

	jv_detail.set("reference_type", d["against_voucher_type"])
	jv_detail.set("reference_name", d["against_voucher"])

	if d['allocated_amt'] < d['unadjusted_amt']:
		jvd = frappe.db.sql("""
			select cost_center, balance, against_account, is_advance,
				account_type, exchange_rate, account_currency
			from `tabJournal Entry Account` where name = %s
		""", d['voucher_detail_no'], as_dict=True)

		amount_in_account_currency = flt(d['unadjusted_amt']) - flt(d['allocated_amt'])
		amount_in_company_currency = amount_in_account_currency * flt(jvd[0]['exchange_rate'])

		# new entry with balance amount
		ch = jv_obj.append("accounts")
		ch.account = d['account']
		ch.account_type = jvd[0]['account_type']
		ch.account_currency = jvd[0]['account_currency']
		ch.exchange_rate = jvd[0]['exchange_rate']
		ch.party_type = d["party_type"]
		ch.party = d["party"]
		ch.cost_center = cstr(jvd[0]["cost_center"])
		ch.balance = flt(jvd[0]["balance"])

		ch.set(d['dr_or_cr'], amount_in_account_currency)
		ch.set('debit' if d['dr_or_cr']=='debit_in_account_currency' else 'credit', amount_in_company_currency)

		ch.set('credit_in_account_currency' if d['dr_or_cr']== 'debit_in_account_currency'
			else 'debit_in_account_currency', 0)
		ch.set('credit' if d['dr_or_cr']== 'debit_in_account_currency' else 'debit', 0)

		ch.against_account = cstr(jvd[0]["against_account"])
		ch.reference_type = original_reference_type
		ch.reference_name = original_reference_name
		ch.is_advance = cstr(jvd[0]["is_advance"])
		ch.docstatus = 1

	# will work as update after submit
	jv_obj.flags.ignore_validate_update_after_submit = True
	jv_obj.save()

def remove_against_link_from_jv(ref_type, ref_no):
	linked_jv = frappe.db.sql_list("""select parent from `tabJournal Entry Account`
		where reference_type=%s and reference_name=%s and docstatus < 2""", (ref_type, ref_no))

	if linked_jv:
		frappe.db.sql("""update `tabJournal Entry Account`
			set reference_type=null, reference_name = null,
			modified=%s, modified_by=%s
			where reference_type=%s and reference_name=%s
			and docstatus < 2""", (now(), frappe.session.user, ref_type, ref_no))

		frappe.db.sql("""update `tabGL Entry`
			set against_voucher_type=null, against_voucher=null,
			modified=%s, modified_by=%s
			where against_voucher_type=%s and against_voucher=%s
			and voucher_no != ifnull(against_voucher, '')""",
			(now(), frappe.session.user, ref_type, ref_no))

		frappe.msgprint(_("Journal Entries {0} are un-linked".format("\n".join(linked_jv))))


@frappe.whitelist()
def get_company_default(company, fieldname):
	value = frappe.db.get_value("Company", company, fieldname)

	if not value:
		throw(_("Please set default value {0} in Company {1}").format(frappe.get_meta("Company").get_label(fieldname), company))

	return value

def fix_total_debit_credit():
	vouchers = frappe.db.sql("""select voucher_type, voucher_no,
		sum(debit) - sum(credit) as diff
		from `tabGL Entry`
		group by voucher_type, voucher_no
		having sum(debit) != sum(credit)""", as_dict=1)

	for d in vouchers:
		if abs(d.diff) > 0:
			dr_or_cr = d.voucher_type == "Sales Invoice" and "credit" or "debit"

			frappe.db.sql("""update `tabGL Entry` set %s = %s + %s
				where voucher_type = %s and voucher_no = %s and %s > 0 limit 1""" %
				(dr_or_cr, dr_or_cr, '%s', '%s', '%s', dr_or_cr),
				(d.diff, d.voucher_type, d.voucher_no))

def get_stock_and_account_difference(account_list=None, posting_date=None):
	from erpnext.stock.utils import get_stock_value_on

	if not posting_date: posting_date = nowdate()

	difference = {}

	account_warehouse = dict(frappe.db.sql("""select name, warehouse from tabAccount
		where account_type = 'Warehouse' and (warehouse is not null and warehouse != '')
		and name in (%s)""" % ', '.join(['%s']*len(account_list)), account_list))

	for account, warehouse in account_warehouse.items():
		account_balance = get_balance_on(account, posting_date, in_account_currency=False)
		stock_value = get_stock_value_on(warehouse, posting_date)
		if abs(flt(stock_value) - flt(account_balance)) > 0.005:
			difference.setdefault(account, flt(stock_value) - flt(account_balance))

	return difference

def validate_expense_against_budget(args):
	args = frappe._dict(args)
	if frappe.db.get_value("Account", {"name": args.account, "root_type": "Expense"}):
			budget = frappe.db.sql("""
				select bd.budget_allocated, cc.distribution_id
				from `tabCost Center` cc, `tabBudget Detail` bd
				where cc.name=bd.parent and cc.name=%s and account=%s and bd.fiscal_year=%s
			""", (args.cost_center, args.account, args.fiscal_year), as_dict=True)

			if budget and budget[0].budget_allocated:
				yearly_action, monthly_action = frappe.db.get_value("Company", args.company,
					["yearly_bgt_flag", "monthly_bgt_flag"])
				action_for = action = ""

				if monthly_action in ["Stop", "Warn"]:
					budget_amount = get_allocated_budget(budget[0].distribution_id,
						args.posting_date, args.fiscal_year, budget[0].budget_allocated)

					args["month_end_date"] = frappe.db.sql("select LAST_DAY(%s)",
						args.posting_date)[0][0]
					action_for, action = _("Monthly"), monthly_action

				elif yearly_action in ["Stop", "Warn"]:
					budget_amount = budget[0].budget_allocated
					action_for, action = _("Annual"), yearly_action

				if action_for:
					actual_expense = get_actual_expense(args)
					if actual_expense > budget_amount:
						frappe.msgprint(_("{0} budget for Account {1} against Cost Center {2} will exceed by {3}").format(
							_(action_for), args.account, args.cost_center, cstr(actual_expense - budget_amount)))
						if action=="Stop":
							raise BudgetError

def get_allocated_budget(distribution_id, posting_date, fiscal_year, yearly_budget):
	if distribution_id:
		distribution = {}
		for d in frappe.db.sql("""select mdp.month, mdp.percentage_allocation
			from `tabMonthly Distribution Percentage` mdp, `tabMonthly Distribution` md
			where mdp.parent=md.name and md.fiscal_year=%s""", fiscal_year, as_dict=1):
				distribution.setdefault(d.month, d.percentage_allocation)

	dt = frappe.db.get_value("Fiscal Year", fiscal_year, "year_start_date")
	budget_percentage = 0.0

	while(dt <= getdate(posting_date)):
		if distribution_id:
			budget_percentage += distribution.get(getdate(dt).strftime("%B"), 0)
		else:
			budget_percentage += 100.0/12

		dt = add_months(dt, 1)

	return yearly_budget * budget_percentage / 100

def get_actual_expense(args):
	args["condition"] = " and posting_date<='%s'" % args.month_end_date \
		if args.get("month_end_date") else ""

	return flt(frappe.db.sql("""
		select sum(debit) - sum(credit)
		from `tabGL Entry`
		where account='%(account)s' and cost_center='%(cost_center)s'
		and fiscal_year='%(fiscal_year)s' and company='%(company)s' %(condition)s
	""" % (args))[0][0])

def get_currency_precision(currency=None):
	if not currency:
		currency = frappe.db.get_value("Company",
			frappe.db.get_default("company"), "default_currency", cache=True)
	currency_format = frappe.db.get_value("Currency", currency, "number_format", cache=True)

	from frappe.utils import get_number_format_info
	return get_number_format_info(currency_format)[2]

def get_stock_rbnb_difference(posting_date, company):
	stock_items = frappe.db.sql_list("""select distinct item_code
		from `tabStock Ledger Entry` where company=%s""", company)

	pr_valuation_amount = frappe.db.sql("""
		select sum(pr_item.valuation_rate * pr_item.qty * pr_item.conversion_factor)
		from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
	    where pr.name = pr_item.parent and pr.docstatus=1 and pr.company=%s
		and pr.posting_date <= %s and pr_item.item_code in (%s)""" %
	    ('%s', '%s', ', '.join(['%s']*len(stock_items))), tuple([company, posting_date] + stock_items))[0][0]

	pi_valuation_amount = frappe.db.sql("""
		select sum(pi_item.valuation_rate * pi_item.qty * pi_item.conversion_factor)
		from `tabPurchase Invoice Item` pi_item, `tabPurchase Invoice` pi
	    where pi.name = pi_item.parent and pi.docstatus=1 and pi.company=%s
		and pi.posting_date <= %s and pi_item.item_code in (%s)""" %
	    ('%s', '%s', ', '.join(['%s']*len(stock_items))), tuple([company, posting_date] + stock_items))[0][0]

	# Balance should be
	stock_rbnb = flt(pr_valuation_amount, 2) - flt(pi_valuation_amount, 2)

	# Balance as per system
	stock_rbnb_account = "Stock Received But Not Billed - " + frappe.db.get_value("Company", company, "abbr")
	sys_bal = get_balance_on(stock_rbnb_account, posting_date, in_account_currency=False)

	# Amount should be credited
	return flt(stock_rbnb) + flt(sys_bal)

def get_outstanding_invoices(party_type, party, account, condition=None):
	outstanding_invoices = []
	precision = frappe.get_precision("Sales Invoice", "outstanding_amount")

	if party_type=="Customer":
		dr_or_cr = "debit_in_account_currency - credit_in_account_currency"
		payment_dr_or_cr = "payment_gl_entry.credit_in_account_currency - payment_gl_entry.debit_in_account_currency"
	else:
		dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
		payment_dr_or_cr = "payment_gl_entry.debit_in_account_currency - payment_gl_entry.credit_in_account_currency"

	invoice_list = frappe.db.sql("""select
			voucher_no,	voucher_type, posting_date,
			ifnull(sum({dr_or_cr}), 0) as invoice_amount,
			(
				select
					ifnull(sum({payment_dr_or_cr}), 0)
				from `tabGL Entry` payment_gl_entry
				where
					payment_gl_entry.against_voucher_type = invoice_gl_entry.voucher_type
					and payment_gl_entry.against_voucher = invoice_gl_entry.voucher_no
					and payment_gl_entry.party_type = invoice_gl_entry.party_type
					and payment_gl_entry.party = invoice_gl_entry.party
					and payment_gl_entry.account = invoice_gl_entry.account
					and {payment_dr_or_cr} > 0
			) as payment_amount
		from
			`tabGL Entry` invoice_gl_entry
		where
			party_type = %(party_type)s
			and party = %(party)s
			and account = %(account)s
			and {dr_or_cr} > 0
			{condition}
			and ((voucher_type = 'Journal Entry'
					and (against_voucher = ''
						or against_voucher is null))
				or (voucher_type != 'Journal Entry'))
		group by voucher_type, voucher_no
		having (invoice_amount - payment_amount) > 0.005""".format(
			dr_or_cr = dr_or_cr,
			payment_dr_or_cr = payment_dr_or_cr,
			condition = condition or ""
		), {
			"party_type": party_type,
			"party": party,
			"account": account,
		}, as_dict=True)

	for d in invoice_list:
		outstanding_invoices.append({
			'voucher_no': d.voucher_no,
			'voucher_type': d.voucher_type,
			'posting_date': d.posting_date,
			'invoice_amount': flt(d.invoice_amount),
			'payment_amount': flt(d.payment_amount),
			'outstanding_amount': flt(d.invoice_amount - d.payment_amount, precision)
		})

	return outstanding_invoices
