# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt, add_days
from webnotes import _
from accounts.utils import get_balance_on

def execute(filters=None):
	validate_filters(filters)
	columns = get_columns()
	data = []
	if filters.get("group_by"):
		data += get_grouped_gle(filters)
	else:
		data += get_gl_entries(filters)
		if data:
			data.append(get_total_row(data))

	if filters.get("account"):
		data = [get_opening_balance_row(filters)] + data + [get_closing_balance_row(filters)]

	return columns, data
	
def validate_filters(filters):
	if filters.get("account") and filters.get("group_by") == "Group by Account":
		webnotes.throw(_("Can not filter based on Account, if grouped by Account"))
		
	if filters.get("voucher_no") and filters.get("group_by") == "Group by Voucher":
		webnotes.throw(_("Can not filter based on Voucher No, if grouped by Voucher"))
	
def get_columns():
	return ["Posting Date:Date:100", "Account:Link/Account:200", "Debit:Float:100", 
		"Credit:Float:100", "Voucher Type::120", "Voucher No::160", "Link::20", 
		"Cost Center:Link/Cost Center:100", "Remarks::200"]
		
def get_opening_balance_row(filters):
	opening_balance = get_balance_on(filters["account"], add_days(filters["from_date"], -1))
	return ["", "Opening Balance", opening_balance, 0.0, "", "", ""]
	
def get_closing_balance_row(filters):
	closing_balance = get_balance_on(filters["account"], filters["to_date"])
	return ["", "Closing Balance", closing_balance, 0.0, "", "", ""]
		
def get_gl_entries(filters):
	gl_entries = webnotes.conn.sql("""select 
			posting_date, account, debit, credit, voucher_type, voucher_no, cost_center, remarks 
		from `tabGL Entry`
		where company=%(company)s 
			and posting_date between %(from_date)s and %(to_date)s
			{conditions}
		order by posting_date, account"""\
		.format(conditions=get_conditions(filters)), filters, as_list=1)
		
	for d in gl_entries:
		icon = """<a href="%s"><i class="icon icon-share" style="cursor: pointer;"></i></a>""" \
			% ("/".join(["#Form", d[4], d[5]]),)
		d.insert(6, icon)
		
	return gl_entries
			
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