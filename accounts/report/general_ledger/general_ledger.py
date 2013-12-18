# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt
from webnotes import _

def execute(filters=None):
	validate_filters(filters)
	columns = get_columns()
	
	if filters.get("group_by"):
		data = get_grouped_gle(filters)
	else:
		data = get_gl_entries(filters)
		if data:
			data.append(get_total_row(data))

	return columns, data
	
def validate_filters(filters):
	if filters.get("account") and filters.get("group_by") == "Group by Account":
		webnotes.throw(_("Can not filter based on Account, if grouped by Account"))
		
	if filters.get("voucher_no") and filters.get("group_by") == "Group by Voucher":
		webnotes.throw(_("Can not filter based on Voucher No, if grouped by Voucher"))
	
def get_columns():
	return ["Posting Date:Date:100", "Account:Link/Account:200", "Debit:Currency:100", 
		"Credit:Currency:100", "Voucher Type::120", "Voucher No::160", 
		"Cost Center:Link/Cost Center:100", "Remarks::200"]
		
def get_gl_entries(filters):
	return webnotes.conn.sql("""select 
			posting_date, account, debit, credit, voucher_type, voucher_no, cost_center, remarks 
		from `tabGL Entry`
		where company=%(company)s 
			and posting_date between %(from_date)s and %(to_date)s
			{conditions}
		order by posting_date, account"""\
		.format(conditions=get_conditions(filters)), filters, as_list=1)
			
def get_conditions(filters):
	conditions = []
	if filters.get("account"):
		conditions.append("account=%(account)s")
	if filters.get("voucher_no"):
		conditions.append("voucher_no=%(voucher_no)s")
	
	return "and {}".format(" and ".join(conditions)) if conditions else ""
		
def get_grouped_gle(filters):
	gle_map = {}
	gle = get_gl_entries(filters)
	for d in gle:
		gle_map.setdefault(d[1 if filters["group_by"]=="Group by Account" else 5], []).append(d)
		
	data = []
	for entries in gle_map.values():
		subtotal_debit = subtotal_credit = 0.0
		for entry in entries:
			data.append(entry)
			subtotal_debit += flt(entry[2])
			subtotal_credit += flt(entry[3])
		
		data.append(["", "Total", subtotal_debit, subtotal_credit, "", "", ""])
	
	if data:
		data.append(get_total_row(gle))
	return data
	
def get_total_row(gle):
	total_debit = total_credit = 0.0
	for d in gle:
		total_debit += flt(d[2])
		total_credit += flt(d[3])
		
	return ["", "Total Debit/Credit", total_debit, total_credit, "", "", ""]