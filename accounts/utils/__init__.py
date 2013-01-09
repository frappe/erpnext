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
from webnotes.utils import nowdate

class FiscalYearError(webnotes.ValidationError): pass

def get_fiscal_year(date, verbose=1):
	from webnotes.utils import formatdate
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
	
	return fy[0]

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