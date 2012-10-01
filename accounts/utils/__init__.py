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

def get_fiscal_year(date):
	from webnotes.utils import formatdate
	fy = webnotes.conn.sql("""select name, year_start_date, 
		adddate(year_start_date, interval 1 year) 
		from `tabFiscal Year`
		where %s between year_start_date and adddate(year_start_date, 
		interval 1 year)""", date)
	
	if not fy:
		webnotes.msgprint("""%s not in any Fiscal Year""" % formatdate(date), raise_exception=1)
	
	return fy[0]

@webnotes.whitelist()
def get_balance_on(account=None, date=None):
	if not account and webnotes.form_dict.get("account"):
		account = webnotes.form_dict.get("account")
		date = webnotes.form_dict.get("date")
		
	cond = []
	if date:
		cond.append("posting_date <= '%s'" % date)
	
	acc = webnotes.conn.get_value('Account', account, \
		['lft', 'rgt', 'debit_or_credit', 'is_pl_account', 'group_or_ledger'], as_dict=1)
	
	# for pl accounts, get balance within a fiscal year
	if acc.is_pl_account == 'Yes':
		cond.append("posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" % \
			get_fiscal_year(date or nowdate())[1])
	
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