# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import webnotes
from webnotes.utils import nowdate, cstr, flt, now
from webnotes.model.doc import addchild
from webnotes import msgprint, _
from webnotes.utils import formatdate
from utilities import build_filter_conditions


class FiscalYearError(webnotes.ValidationError): pass

def get_fiscal_year(date=None, fiscal_year=None, verbose=1):
	return get_fiscal_years(date, fiscal_year, verbose=1)[0]
	
def get_fiscal_years(date=None, fiscal_year=None, verbose=1):
	# if year start date is 2012-04-01, year end date should be 2013-03-31 (hence subdate)
	cond = ""
	if fiscal_year:
		cond = "name = '%s'" % fiscal_year
	else:
		cond = "'%s' >= year_start_date and '%s' < adddate(year_start_date, interval 1 year)" % \
			(date, date)
	fy = webnotes.conn.sql("""select name, year_start_date, 
		subdate(adddate(year_start_date, interval 1 year), interval 1 day) 
			as year_end_date
		from `tabFiscal Year`
		where %s
		order by year_start_date desc""" % cond)
	
	if not fy:
		error_msg = """%s not in any Fiscal Year""" % formatdate(date)
		if verbose: webnotes.msgprint(error_msg)
		raise FiscalYearError, error_msg
	
	return fy
	
def validate_fiscal_year(date, fiscal_year, label="Date"):
	years = [f[0] for f in get_fiscal_years(date)]
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
		from webnotes.utils import getdate
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
	
	# join conditional conditions
	cond = " and ".join(cond)
	if cond:
		cond += " and "
	
	bal = webnotes.conn.sql("""
		SELECT sum(ifnull(debit, 0)) - sum(ifnull(credit, 0)) 
		FROM `tabGL Entry` gle
		WHERE %s ifnull(is_cancelled, 'No') = 'No' """ % (cond, ))[0][0]

	# if credit account, it should calculate credit - debit
	if bal and acc.debit_or_credit == 'Credit':
		bal = -bal

	# if bal is None, return 0
	return bal or 0

@webnotes.whitelist()
def add_ac(args=None):
	if not args:
		args = webnotes.form_dict
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
		args = webnotes.form_dict
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
	webnotes.conn.sql("""update `tabJournal Voucher Detail` set `%s`=null,
		modified=%s, modified_by=%s
		where `%s`=%s and docstatus < 2""" % (against_field, "%s", "%s", against_field, "%s"), 
		(now(), webnotes.session.user, ref_no))
	
	webnotes.conn.sql("""update `tabGL Entry`
		set against_voucher_type=null, against_voucher=null,
		modified=%s, modified_by=%s
		where against_voucher_type=%s and against_voucher=%s
		and voucher_no != ifnull(against_voucher, "")
		and ifnull(is_cancelled, "No")="No" """,
		(now(), webnotes.session.user, ref_type, ref_no))

@webnotes.whitelist()
def get_company_default(company, fieldname):
	value = webnotes.conn.get_value("Company", company, fieldname)
	
	if not value:
		msgprint(_("Please mention default value for '") + 
			_(webnotes.get_doctype("company").get_label(fieldname) + 
			_("' in Company: ") + company), raise_exception=True)
			
	return value
		
def create_stock_in_hand_jv(reverse=False):
	from webnotes.utils import nowdate
	today = nowdate()
	fiscal_year = get_fiscal_year(today)[0]
	jv_list = []
	
	for company in webnotes.conn.sql_list("select name from `tabCompany`"):
		stock_rbnb_value = get_stock_rbnb_value(company)
		stock_rbnb_value = reverse and -1*stock_rbnb_value or stock_rbnb_value
		if stock_rbnb_value:
			jv = webnotes.bean([
				{
					"doctype": "Journal Voucher",
					"naming_series": "JV-AUTO-",
					"company": company,
					"posting_date": today,
					"fiscal_year": fiscal_year,
					"voucher_type": "Journal Entry",
					"user_remark": (_("Auto Inventory Accounting") + ": " +
						(_("Disabled") if reverse else _("Enabled")) + ". " +
						_("Journal Entry for inventory that is received but not yet invoiced"))
				},
				{
					"doctype": "Journal Voucher Detail",
					"parentfield": "entries",
					"account": get_company_default(company, "stock_received_but_not_billed"),
						(stock_rbnb_value > 0 and "credit" or "debit"): abs(stock_rbnb_value)
				},
				{
					"doctype": "Journal Voucher Detail",
					"parentfield": "entries",
					"account": get_company_default(company, "stock_adjustment_account"),
						(stock_rbnb_value > 0 and "debit" or "credit"): abs(stock_rbnb_value),
					"cost_center": get_company_default(company, "stock_adjustment_cost_center")
				},
			])
			jv.insert()
			
			jv_list.append(jv.doc.name)
	
	if jv_list:
		msgprint(_("Following Journal Vouchers have been created automatically") + \
			":\n%s" % ("\n".join([("<a href=\"#Form/Journal Voucher/%s\">%s</a>" % (jv, jv)) for jv in jv_list]),))
		
		msgprint(_("""These adjustment vouchers book the difference between \
			the total value of received items and the total value of invoiced items, \
			as a required step to use Auto Inventory Accounting.
			This is an approximation to get you started.
			You will need to submit these vouchers after checking if the values are correct.
			For more details, read: \
			<a href="http://erpnext.com/auto-inventory-accounting" target="_blank">\
			Auto Inventory Accounting</a>"""))
			
	webnotes.msgprint("""Please refresh the system to get effect of Auto Inventory Accounting""")
			
		
def get_stock_rbnb_value(company):
	total_received_amount = webnotes.conn.sql("""select sum(valuation_rate*qty*conversion_factor) 
		from `tabPurchase Receipt Item` pr_item where docstatus=1 
		and exists(select name from `tabItem` where name = pr_item.item_code 
			and is_stock_item='Yes')
		and exists(select name from `tabPurchase Receipt` 
			where name = pr_item.parent and company = %s)""", company)
		
	total_billed_amount = webnotes.conn.sql("""select sum(valuation_rate*qty*conversion_factor) 
		from `tabPurchase Invoice Item` pi_item where docstatus=1 
		and exists(select name from `tabItem` where name = pi_item.item_code 
			and is_stock_item='Yes')
		and exists(select name from `tabPurchase Invoice` 
			where name = pi_item.parent and company = %s)""", company)
	return flt(total_received_amount[0][0]) - flt(total_billed_amount[0][0])


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
				(d.diff, d.voucher_type, d.voucher_no), debug=1)