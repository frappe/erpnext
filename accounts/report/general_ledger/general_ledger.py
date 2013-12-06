# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt

def execute(filters=None):
	columns = get_columns()
	if filters.get("group_by"):
		data = get_grouped_gle(filters)
	else:
		data = get_gl_entries(filters)

	return columns, data
	
def get_columns():
	return ["Posting Date:Date:100", "Account:Link/Account:200", "Debit:Currency:100", 
		"Credit:Currency:100", "Voucher Type::120", "Voucher No::160", "Remarks::200"]
		
def get_gl_entries(filters):
	return webnotes.conn.sql("""select 
			posting_date, account, debit, credit, voucher_type, voucher_no, cost_center, remarks 
		from `tabGL Entry`
		where company=%(company)s 
			and posting_date between %(from_date)s and %(to_date)s
			{conditions}
		order by posting_date, account"""\
		.format(conditions=get_conditions(filters)), filters)
			
def get_conditions(filters):
	return " and account=%(account)s" if filters.get("account") else ""
	
def get_grouped_gle(filters):
	gle_map = {}
	gle = get_gl_entries(filters)
	for d in gle:
		gle_map.setdefault(d[1 if filters["group_by"]=="Account" else 5], []).append(d)
		
	data = []
	for entries in gle_map.values():
		total_debit = total_credit = 0.0
		for entry in entries:
			data.append(entry)
			total_debit += flt(entry[2])
			total_credit += flt(entry[3])
			
		data.append(["", "Total", total_debit, total_credit, "", "", ""])
	return data