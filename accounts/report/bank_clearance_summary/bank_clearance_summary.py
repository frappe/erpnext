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
from webnotes import _, msgprint

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns()
	data = get_entries(filters)
	
	return columns, data
	
def get_columns():
	return ["Journal Voucher:Link/Journal Voucher:140", "Account:Link/Account:140", 
		"Posting Date:Date:100", "Clearance Date:Date:110", "Against Account:Link/Account:200", 
		"Debit:Currency:120", "Credit:Currency:120"
	]

def get_conditions(filters):
	conditions = ""
	if not filters.get("account"):
		msgprint(_("Please select Bank Account"), raise_exception=1)
	else:
		conditions += " and jvd.account = %(account)s"
		
	if filters.get("from_date"): conditions += " and jv.posting_date>=%(from_date)s"
	if filters.get("to_date"): conditions += " and jv.posting_date<=%(to_date)s"
	
	return conditions
	
def get_entries(filters):
	conditions = get_conditions(filters)
	entries =  webnotes.conn.sql("""select jv.name, jvd.account, jv.posting_date, 
		jv.clearance_date, jvd.against_account, jvd.debit, jvd.credit
		from `tabJournal Voucher Detail` jvd, `tabJournal Voucher` jv 
		where jvd.parent = jv.name and jv.docstatus=1 %s
		order by jv.name DESC""" % conditions, filters, as_list=1)
	return entries