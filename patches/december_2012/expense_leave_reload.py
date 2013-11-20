# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	# new roles
	roles = [r[0] for r in webnotes.conn.sql("""select name from tabRole""")]
	if not "Leave Approver" in roles:
		webnotes.bean([{"doctype":"Role", "role_name":"Leave Approver", 
			"__islocal":1, "module":"HR"}]).save()
	if not "Expense Approver" in roles:
		webnotes.bean([{"doctype":"Role", "role_name":"Expense Approver", 
			"__islocal":1, "module":"HR"}]).save()

	# reload
	webnotes.clear_perms("Leave Application")
	webnotes.reload_doc("hr", "doctype", "leave_application")

	webnotes.clear_perms("Expense Claim")
	webnotes.reload_doc("hr", "doctype", "expense_claim")
	
	# remove extra space in Approved Expense Vouchers
	webnotes.conn.sql("""update `tabExpense Claim` set approval_status='Approved'
		where approval_status='Approved '""")

	webnotes.conn.commit()
	for t in ['__CacheItem', '__SessionCache', 'tabSupport Ticket Response']:
		webnotes.conn.sql("drop table if exists `%s`" % t)