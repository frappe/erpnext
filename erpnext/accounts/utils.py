# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils import nowdate, cstr, flt, now, getdate, add_months
from frappe import throw, _
from frappe.utils import formatdate
import frappe.desk.reportview

class FiscalYearError(frappe.ValidationError): pass
class BudgetError(frappe.ValidationError): pass

@frappe.whitelist()
def get_fiscal_year(date=None, fiscal_year=None, label="Date", verbose=1, company=None):
	return get_fiscal_years(date, fiscal_year, label, verbose, company)[0]

def get_fiscal_years(transaction_date=None, fiscal_year=None, label="Date", verbose=1, company=None):
	# if year start date is 2012-04-01, year end date should be 2013-03-31 (hence subdate)
	cond = ""
	if fiscal_year:
		cond = "fy.name = %(fiscal_year)s"
	else:
		cond = "%(transaction_date)s >= fy.year_start_date and %(transaction_date)s <= fy.year_end_date"

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
		error_msg = _("""{0} {1} not in any Fiscal Year. For more details check {2}.""").format(label, formatdate(transaction_date), "https://erpnext.com/kb/accounts/fiscal-year-error")
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
def get_balance_on(account=None, date=None, party_type=None, party=None):
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
		cond.append("posting_date <= '%s'" % date)
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
		acc.check_permission("read")

		# for pl accounts, get balance within a fiscal year
		if acc.report_type == 'Profit and Loss':
			cond.append("posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" \
				% year_start_date)

		# different filter for group and ledger - improved performance
		if acc.group_or_ledger=="Group":
			cond.append("""exists (
				select * from `tabAccount` ac where ac.name = gle.account
				and ac.lft >= %s and ac.rgt <= %s
			)""" % (acc.lft, acc.rgt))
		else:
			cond.append("""gle.account = "%s" """ % (account.replace('"', '\\"'), ))

	if party_type and party:
		cond.append("""gle.party_type = "%s" and gle.party = "%s" """ %
			(party_type.replace('"', '\\"'), party.replace('"', '\\"')))

	bal = frappe.db.sql("""
		SELECT sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))
		FROM `tabGL Entry` gle
		WHERE %s""" % " and ".join(cond))[0][0]

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
		against_fld = {
			'Journal Entry' : 'against_jv',
			'Sales Invoice' : 'against_invoice',
			'Purchase Invoice' : 'against_voucher'
		}

		d['against_fld'] = against_fld[d['against_voucher_type']]

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
		and ifnull(t2.against_voucher, '')=''
		and ifnull(t2.against_invoice, '')='' and ifnull(t2.against_jv, '')=''
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
	jv_detail.set(d["against_fld"], d["against_voucher"])

	if d['allocated_amt'] < d['unadjusted_amt']:
		jvd = frappe.db.sql("""select cost_center, balance, against_account, is_advance
			from `tabJournal Entry Account` where name = %s""", d['voucher_detail_no'])
		# new entry with balance amount
		ch = jv_obj.append("accounts")
		ch.account = d['account']
		ch.party_type = d["party_type"]
		ch.party = d["party"]
		ch.cost_center = cstr(jvd[0][0])
		ch.balance = flt(jvd[0][1])
		ch.set(d['dr_or_cr'], flt(d['unadjusted_amt']) - flt(d['allocated_amt']))
		ch.set(d['dr_or_cr']== 'debit' and 'credit' or 'debit', 0)
		ch.against_account = cstr(jvd[0][2])
		ch.is_advance = cstr(jvd[0][3])
		ch.docstatus = 1

	# will work as update after submit
	jv_obj.flags.ignore_validate_update_after_submit = True
	jv_obj.save()

def remove_against_link_from_jv(ref_type, ref_no, against_field):
	linked_jv = frappe.db.sql_list("""select parent from `tabJournal Entry Account`
		where `%s`=%s and docstatus < 2""" % (against_field, "%s"), (ref_no))

	if linked_jv:
		frappe.db.sql("""update `tabJournal Entry Account` set `%s`=null,
			modified=%s, modified_by=%s
			where `%s`=%s and docstatus < 2""" % (against_field, "%s", "%s", against_field, "%s"),
			(now(), frappe.session.user, ref_no))

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
		having sum(ifnull(debit, 0)) != sum(ifnull(credit, 0))""", as_dict=1)

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
		where account_type = 'Warehouse' and ifnull(warehouse, '') != ''
		and name in (%s)""" % ', '.join(['%s']*len(account_list)), account_list))

	for account, warehouse in account_warehouse.items():
		account_balance = get_balance_on(account, posting_date)
		stock_value = get_stock_value_on(warehouse, posting_date)
		if abs(flt(stock_value) - flt(account_balance)) > 0.005:
			difference.setdefault(account, flt(stock_value) - flt(account_balance))

	return difference

def validate_expense_against_budget(args):
	args = frappe._dict(args)
	if frappe.db.get_value("Account", {"name": args.account, "report_type": "Profit and Loss"}):
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
		select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))
		from `tabGL Entry`
		where account='%(account)s' and cost_center='%(cost_center)s'
		and fiscal_year='%(fiscal_year)s' and company='%(company)s' %(condition)s
	""" % (args))[0][0])

def get_currency_precision(currency=None):
	if not currency:
		currency = frappe.db.get_value("Company",
			frappe.db.get_default("company"), "default_currency")
	currency_format = frappe.db.get_value("Currency", currency, "number_format")

	from frappe.utils import get_number_format_info
	return get_number_format_info(currency_format)[2]

def get_stock_rbnb_difference(posting_date, company):
	stock_items = frappe.db.sql_list("""select distinct item_code
		from `tabStock Ledger Entry` where company=%s""", company)

	pr_valuation_amount = frappe.db.sql("""
		select sum(ifnull(pr_item.valuation_rate, 0) * ifnull(pr_item.qty, 0) * ifnull(pr_item.conversion_factor, 0))
		from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
	    where pr.name = pr_item.parent and pr.docstatus=1 and pr.company=%s
		and pr.posting_date <= %s and pr_item.item_code in (%s)""" %
	    ('%s', '%s', ', '.join(['%s']*len(stock_items))), tuple([company, posting_date] + stock_items))[0][0]

	pi_valuation_amount = frappe.db.sql("""
		select sum(ifnull(pi_item.valuation_rate, 0) * ifnull(pi_item.qty, 0) * ifnull(pi_item.conversion_factor, 0))
		from `tabPurchase Invoice Item` pi_item, `tabPurchase Invoice` pi
	    where pi.name = pi_item.parent and pi.docstatus=1 and pi.company=%s
		and pi.posting_date <= %s and pi_item.item_code in (%s)""" %
	    ('%s', '%s', ', '.join(['%s']*len(stock_items))), tuple([company, posting_date] + stock_items))[0][0]

	# Balance should be
	stock_rbnb = flt(pr_valuation_amount, 2) - flt(pi_valuation_amount, 2)

	# Balance as per system
	stock_rbnb_account = "Stock Received But Not Billed - " + frappe.db.get_value("Company", company, "abbr")
	sys_bal = get_balance_on(stock_rbnb_account, posting_date)

	# Amount should be credited
	return flt(stock_rbnb) + flt(sys_bal)

def get_outstanding_invoices(amount_query, account, party_type, party):
	all_outstanding_vouchers = []
	outstanding_voucher_list = frappe.db.sql("""
		select
			voucher_no, voucher_type, posting_date,
			ifnull(sum({amount_query}), 0) as invoice_amount
		from
			`tabGL Entry`
		where
			account = %s and party_type=%s and party=%s and {amount_query} > 0
		group by voucher_type, voucher_no
		""".format(amount_query = amount_query), (account, party_type, party), as_dict = True)

	for d in outstanding_voucher_list:
		payment_amount = frappe.db.sql("""
			select ifnull(sum(ifnull({amount_query}, 0)), 0)
			from
				`tabGL Entry`
			where
				account = %s and party_type=%s and party=%s and {amount_query} < 0
				and against_voucher_type = %s and ifnull(against_voucher, '') = %s
			""".format(**{
			"amount_query": amount_query
			}), (account, party_type, party, d.voucher_type, d.voucher_no))

		payment_amount = -1*payment_amount[0][0] if payment_amount else 0

		if d.invoice_amount > payment_amount:

			all_outstanding_vouchers.append({
				'voucher_no': d.voucher_no,
				'voucher_type': d.voucher_type,
				'posting_date': d.posting_date,
				'invoice_amount': flt(d.invoice_amount),
				'outstanding_amount': d.invoice_amount - payment_amount
				})

	return all_outstanding_vouchers

@frappe.whitelist()
def get_letter_head(company):
	return frappe.db.get_value("Company",company,"default_letter_head")

