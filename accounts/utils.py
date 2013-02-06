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
from webnotes.utils import nowdate, cstr, flt
from webnotes.model.doc import addchild
from webnotes import msgprint, _
from webnotes.utils import formatdate

class FiscalYearError(webnotes.ValidationError): pass

def get_fiscal_year(date, verbose=1):
	return get_fiscal_years(date, verbose=1)[0]
	
def get_fiscal_years(date, verbose=1):
	# if year start date is 2012-04-01, year end date should be 2013-03-31 (hence subdate)
	fy = webnotes.conn.sql("""select name, year_start_date, 
		subdate(adddate(year_start_date, interval 1 year), interval 1 day) 
			as year_end_date
		from `tabFiscal Year`
		where %s >= year_start_date and %s < adddate(year_start_date, interval 1 year)
		order by year_start_date desc""", (date, date))
	
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
	
	ac = webnotes.model_wrapper(args)
	ac.doc.doctype = "Account"
	ac.doc.old_parent = ""
	ac.doc.freeze_account = "No"
	ac.ignore_permissions = 1
	ac.insert()
	return ac.doc.name

@webnotes.whitelist()
def add_cc(args=None):
	if not args:
		args = webnotes.form_dict
		args.pop("cmd")
		
	cc = webnotes.model_wrapper(args)
	cc.doc.doctype = "Cost Center"
	cc.doc.old_parent = ""
	cc.ignore_permissions = 1
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