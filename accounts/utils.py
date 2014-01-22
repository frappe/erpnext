# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import webnotes
from webnotes.utils import nowdate, cstr, flt, now, getdate, add_months
from webnotes.model.doc import addchild
from webnotes import msgprint, _
from webnotes.utils import formatdate
from utilities import build_filter_conditions


class FiscalYearError(webnotes.ValidationError): pass
class BudgetError(webnotes.ValidationError): pass


def get_fiscal_year(date=None, fiscal_year=None, label="Date", verbose=1):
	return get_fiscal_years(date, fiscal_year, label, verbose)[0]
	
def get_fiscal_years(date=None, fiscal_year=None, label="Date", verbose=1):
	# if year start date is 2012-04-01, year end date should be 2013-03-31 (hence subdate)
	cond = ""
	if fiscal_year:
		cond = "name = '%s'" % fiscal_year
	else:
		cond = "'%s' >= year_start_date and '%s' <= year_end_date" % \
			(date, date)
	fy = webnotes.conn.sql("""select name, year_start_date, year_end_date
		from `tabFiscal Year` where %s order by year_start_date desc""" % cond)
	
	if not fy:
		error_msg = """%s %s not in any Fiscal Year""" % (label, formatdate(date))
		error_msg = """{msg}: {date}""".format(msg=_("Fiscal Year does not exist for date"), 
			date=formatdate(date))
		if verbose: webnotes.msgprint(error_msg)
		raise FiscalYearError, error_msg
	
	return fy
	
def validate_fiscal_year(date, fiscal_year, label="Date"):
	years = [f[0] for f in get_fiscal_years(date, label=label)]
	if fiscal_year not in years:
		webnotes.msgprint(("%(label)s '%(posting_date)s': " + _("not within Fiscal Year") + \
			": '%(fiscal_year)s'") % {
				"label": label,
				"posting_date": formatdate(date),
				"fiscal_year": fiscal_year
			}, raise_exception=1)

@webnotes.whitelist()
def get_balance_on(account=None, date=None):
	if not account and webnotes.form_dict.get("account"):
		account = webnotes.form_dict.get("account")
		date = webnotes.form_dict.get("date")
	
	cond = []
	if date:
		cond.append("posting_date <= '%s'" % date)
	else:
		# get balance of all entries that exist
		date = nowdate()
		
	try:
		year_start_date = get_fiscal_year(date, verbose=0)[1]
	except FiscalYearError, e:
		if getdate(date) > getdate(nowdate()):
			# if fiscal year not found and the date is greater than today
			# get fiscal year for today's date and its corresponding year start date
			year_start_date = get_fiscal_year(nowdate(), verbose=1)[1]
		else:
			# this indicates that it is a date older than any existing fiscal year.
			# hence, assuming balance as 0.0
			return 0.0
		
	acc = webnotes.conn.get_value('Account', account, \
		['lft', 'rgt', 'debit_or_credit', 'is_pl_account', 'group_or_ledger'], as_dict=1)
	
	# for pl accounts, get balance within a fiscal year
	if acc.is_pl_account == 'Yes':
		cond.append("posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" \
			% year_start_date)
	
	# different filter for group and ledger - improved performance
	if acc.group_or_ledger=="Group":
		cond.append("""exists (
			select * from `tabAccount` ac where ac.name = gle.account
			and ac.lft >= %s and ac.rgt <= %s
		)""" % (acc.lft, acc.rgt))
	else:
		cond.append("""gle.account = "%s" """ % (account, ))
	
	bal = webnotes.conn.sql("""
		SELECT sum(ifnull(debit, 0)) - sum(ifnull(credit, 0)) 
		FROM `tabGL Entry` gle
		WHERE %s""" % " and ".join(cond))[0][0]

	# if credit account, it should calculate credit - debit
	if bal and acc.debit_or_credit == 'Credit':
		bal = -bal

	# if bal is None, return 0
	return flt(bal)

@webnotes.whitelist()
def add_ac(args=None):
	if not args:
		args = webnotes.local.form_dict
		args.pop("cmd")
		
	ac = webnotes.bean(args)
	ac.doc.doctype = "Account"
	ac.doc.old_parent = ""
	ac.doc.freeze_account = "No"
	ac.insert()
	return ac.doc.name

@webnotes.whitelist()
def add_cc(args=None):
	if not args:
		args = webnotes.local.form_dict
		args.pop("cmd")
		
	cc = webnotes.bean(args)
	cc.doc.doctype = "Cost Center"
	cc.doc.old_parent = ""
	cc.insert()
	return cc.doc.name

def reconcile_against_document(args):
	"""
		Cancel JV, Update aginst document, split if required and resubmit jv
	"""
	for d in args:
		check_if_jv_modified(d)

		against_fld = {
			'Journal Voucher' : 'against_jv',
			'Sales Invoice' : 'against_invoice',
			'Purchase Invoice' : 'against_voucher'
		}
		
		d['against_fld'] = against_fld[d['against_voucher_type']]

		# cancel JV
		jv_obj = webnotes.get_obj('Journal Voucher', d['voucher_no'], with_children=1)
		jv_obj.make_gl_entries(cancel=1, adv_adj=1)
		
		# update ref in JV Detail
		update_against_doc(d, jv_obj)

		# re-submit JV
		jv_obj = webnotes.get_obj('Journal Voucher', d['voucher_no'], with_children =1)
		jv_obj.make_gl_entries(cancel = 0, adv_adj =1)


def check_if_jv_modified(args):
	"""
		check if there is already a voucher reference
		check if amount is same
		check if jv is submitted
	"""
	ret = webnotes.conn.sql("""
		select t2.%(dr_or_cr)s from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2 
		where t1.name = t2.parent and t2.account = '%(account)s' 
		and ifnull(t2.against_voucher, '')='' 
		and ifnull(t2.against_invoice, '')='' and ifnull(t2.against_jv, '')=''
		and t1.name = '%(voucher_no)s' and t2.name = '%(voucher_detail_no)s'
		and t1.docstatus=1 and t2.%(dr_or_cr)s = %(unadjusted_amt)s""" % args)
	
	if not ret:
		msgprint(_("""Payment Entry has been modified after you pulled it. 
			Please pull it again."""), raise_exception=1)

def update_against_doc(d, jv_obj):
	"""
		Updates against document, if partial amount splits into rows
	"""

	webnotes.conn.sql("""
		update `tabJournal Voucher Detail` t1, `tabJournal Voucher` t2	
		set t1.%(dr_or_cr)s = '%(allocated_amt)s', 
		t1.%(against_fld)s = '%(against_voucher)s', t2.modified = now() 
		where t1.name = '%(voucher_detail_no)s' and t1.parent = t2.name""" % d)
	
	if d['allocated_amt'] < d['unadjusted_amt']:
		jvd = webnotes.conn.sql("""select cost_center, balance, against_account, is_advance 
			from `tabJournal Voucher Detail` where name = %s""", d['voucher_detail_no'])
		# new entry with balance amount
		ch = addchild(jv_obj.doc, 'entries', 'Journal Voucher Detail')
		ch.account = d['account']
		ch.cost_center = cstr(jvd[0][0])
		ch.balance = cstr(jvd[0][1])
		ch.fields[d['dr_or_cr']] = flt(d['unadjusted_amt']) - flt(d['allocated_amt'])
		ch.fields[d['dr_or_cr']== 'debit' and 'credit' or 'debit'] = 0
		ch.against_account = cstr(jvd[0][2])
		ch.is_advance = cstr(jvd[0][3])
		ch.docstatus = 1
		ch.save(1)
		
def get_account_list(doctype, txt, searchfield, start, page_len, filters):
	if not filters.get("group_or_ledger"):
		filters["group_or_ledger"] = "Ledger"

	conditions, filter_values = build_filter_conditions(filters)
		
	return webnotes.conn.sql("""select name, parent_account from `tabAccount` 
		where docstatus < 2 %s and %s like %s order by name limit %s, %s""" % 
		(conditions, searchfield, "%s", "%s", "%s"), 
		tuple(filter_values + ["%%%s%%" % txt, start, page_len]))
		
def get_cost_center_list(doctype, txt, searchfield, start, page_len, filters):
	if not filters.get("group_or_ledger"):
		filters["group_or_ledger"] = "Ledger"

	conditions, filter_values = build_filter_conditions(filters)
	
	return webnotes.conn.sql("""select name, parent_cost_center from `tabCost Center` 
		where docstatus < 2 %s and %s like %s order by name limit %s, %s""" % 
		(conditions, searchfield, "%s", "%s", "%s"), 
		tuple(filter_values + ["%%%s%%" % txt, start, page_len]))
		
def remove_against_link_from_jv(ref_type, ref_no, against_field):
	linked_jv = webnotes.conn.sql_list("""select parent from `tabJournal Voucher Detail` 
		where `%s`=%s and docstatus < 2""" % (against_field, "%s"), (ref_no))
		
	if linked_jv:	
		webnotes.conn.sql("""update `tabJournal Voucher Detail` set `%s`=null,
			modified=%s, modified_by=%s
			where `%s`=%s and docstatus < 2""" % (against_field, "%s", "%s", against_field, "%s"), 
			(now(), webnotes.session.user, ref_no))
	
		webnotes.conn.sql("""update `tabGL Entry`
			set against_voucher_type=null, against_voucher=null,
			modified=%s, modified_by=%s
			where against_voucher_type=%s and against_voucher=%s
			and voucher_no != ifnull(against_voucher, '')""",
			(now(), webnotes.session.user, ref_type, ref_no))
			
		webnotes.msgprint("{msg} {linked_jv}".format(msg = _("""Following linked Journal Vouchers \
			made against this transaction has been unlinked. You can link them again with other \
			transactions via Payment Reconciliation Tool."""), linked_jv="\n".join(linked_jv)))
		

@webnotes.whitelist()
def get_company_default(company, fieldname):
	value = webnotes.conn.get_value("Company", company, fieldname)
	
	if not value:
		msgprint(_("Please mention default value for '") + 
			_(webnotes.get_doctype("company").get_label(fieldname) + 
			_("' in Company: ") + company), raise_exception=True)
			
	return value

def fix_total_debit_credit():
	vouchers = webnotes.conn.sql("""select voucher_type, voucher_no, 
		sum(debit) - sum(credit) as diff 
		from `tabGL Entry` 
		group by voucher_type, voucher_no
		having sum(ifnull(debit, 0)) != sum(ifnull(credit, 0))""", as_dict=1)
		
	for d in vouchers:
		if abs(d.diff) > 0:
			dr_or_cr = d.voucher_type == "Sales Invoice" and "credit" or "debit"
			
			webnotes.conn.sql("""update `tabGL Entry` set %s = %s + %s
				where voucher_type = %s and voucher_no = %s and %s > 0 limit 1""" %
				(dr_or_cr, dr_or_cr, '%s', '%s', '%s', dr_or_cr), 
				(d.diff, d.voucher_type, d.voucher_no))
	
def get_stock_and_account_difference(account_list=None, posting_date=None):
	from stock.utils import get_stock_balance_on
	
	if not posting_date: posting_date = nowdate()
	
	difference = {}
	
	account_warehouse = dict(webnotes.conn.sql("""select name, master_name from tabAccount 
		where account_type = 'Warehouse' and ifnull(master_name, '') != '' 
		and name in (%s)""" % ', '.join(['%s']*len(account_list)), account_list))
			
	for account, warehouse in account_warehouse.items():
		account_balance = get_balance_on(account, posting_date)
		stock_value = get_stock_balance_on(warehouse, posting_date)
		if abs(flt(stock_value) - flt(account_balance)) > 0.005:
			difference.setdefault(account, flt(stock_value) - flt(account_balance))

	return difference

def validate_expense_against_budget(args):
	args = webnotes._dict(args)
	if webnotes.conn.get_value("Account", {"name": args.account, "is_pl_account": "Yes", 
		"debit_or_credit": "Debit"}):
			budget = webnotes.conn.sql("""
				select bd.budget_allocated, cc.distribution_id 
				from `tabCost Center` cc, `tabBudget Detail` bd
				where cc.name=bd.parent and cc.name=%s and account=%s and bd.fiscal_year=%s
			""", (args.cost_center, args.account, args.fiscal_year), as_dict=True)
			
			if budget and budget[0].budget_allocated:
				yearly_action, monthly_action = webnotes.conn.get_value("Company", args.company, 
					["yearly_bgt_flag", "monthly_bgt_flag"])
				action_for = action = ""

				if monthly_action in ["Stop", "Warn"]:
					budget_amount = get_allocated_budget(budget[0].distribution_id, 
						args.posting_date, args.fiscal_year, budget[0].budget_allocated)
					
					args["month_end_date"] = webnotes.conn.sql("select LAST_DAY(%s)", 
						args.posting_date)[0][0]
					action_for, action = "Monthly", monthly_action
					
				elif yearly_action in ["Stop", "Warn"]:
					budget_amount = budget[0].budget_allocated
					action_for, action = "Monthly", yearly_action

				if action_for:
					actual_expense = get_actual_expense(args)
					if actual_expense > budget_amount:
						webnotes.msgprint(action_for + _(" budget ") + cstr(budget_amount) + 
							_(" for account ") + args.account + _(" against cost center ") + 
							args.cost_center + _(" will exceed by ") + 
							cstr(actual_expense - budget_amount) + _(" after this transaction.")
							, raise_exception=BudgetError if action=="Stop" else False)
					
def get_allocated_budget(distribution_id, posting_date, fiscal_year, yearly_budget):
	if distribution_id:
		distribution = {}
		for d in webnotes.conn.sql("""select bdd.month, bdd.percentage_allocation 
			from `tabBudget Distribution Detail` bdd, `tabBudget Distribution` bd
			where bdd.parent=bd.name and bd.fiscal_year=%s""", fiscal_year, as_dict=1):
				distribution.setdefault(d.month, d.percentage_allocation)

	dt = webnotes.conn.get_value("Fiscal Year", fiscal_year, "year_start_date")
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
		
	return webnotes.conn.sql("""
		select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))
		from `tabGL Entry`
		where account='%(account)s' and cost_center='%(cost_center)s' 
		and fiscal_year='%(fiscal_year)s' and company='%(company)s' %(condition)s
	""" % (args))[0][0]
	
def rename_account_for(dt, olddn, newdn, merge):
	old_account = get_account_for(dt, olddn)
	if old_account:
		new_account = None
		if not merge:
			if old_account == olddn:
				new_account = webnotes.rename_doc("Account", olddn, newdn)
		else:
			existing_new_account = get_account_for(dt, newdn)
			new_account = webnotes.rename_doc("Account", old_account, 
				existing_new_account or newdn, merge=True if existing_new_account else False)

		if new_account:
			webnotes.conn.set_value("Account", new_account, "master_name", newdn)
			
def get_account_for(account_for_doctype, account_for):
	if account_for_doctype in ["Customer", "Supplier"]:
		account_for_field = "master_type"
	elif account_for_doctype == "Warehouse":
		account_for_field = "account_type"
		
	return webnotes.conn.get_value("Account", {account_for_field: account_for_doctype, 
		"master_name": account_for})
		
def get_currency_precision(currency=None):
	if not currency:
		currency = webnotes.conn.get_value("Company", 
			webnotes.conn.get_default("company"), "default_currency")
	currency_format = webnotes.conn.get_value("Currency", currency, "number_format")
	
	from webnotes.utils import get_number_format_info
	return get_number_format_info(currency_format)[2]